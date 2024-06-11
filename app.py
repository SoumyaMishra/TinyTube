from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from googleapiclient.discovery import build
import re
import os
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for session management

CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)

def get_youtube_api_key():
    config = load_config()
    return config.get('YOUTUBE_API_KEY')

def prompt_for_api_key():
    api_key = input("Please provide your YouTube API Key: ")
    config = load_config()
    config['YOUTUBE_API_KEY'] = api_key
    save_config(config)

# Ensure API Key is set
YOUTUBE_API_KEY = get_youtube_api_key()
if not YOUTUBE_API_KEY:
    prompt_for_api_key()
    YOUTUBE_API_KEY = get_youtube_api_key()

FAVORITES_FILE = 'favorites.json'

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_favorites(favorites):
    with open(FAVORITES_FILE, 'w') as file:
        json.dump(favorites, file)

def add_favorite(name, url):
    favorites = load_favorites()
    favorites[name] = url
    save_favorites(favorites)

def delete_favorite(name):
    favorites = load_favorites()
    if name in favorites:
        del favorites[name]
        save_favorites(favorites)

def extract_id(youtube, url):
    """
    Extract ID (video, channel, or playlist) from the provided YouTube URL.
    """
    # Video URL pattern
    video_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})')
    match = video_pattern.search(url)
    if match:
        return {'type': 'video', 'id': match.group(1)}

    # Channel URL pattern (channelId)
    channel_pattern = re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/channel/([a-zA-Z0-9_-]+)')
    match = channel_pattern.search(url)
    if match:
        return {'type': 'channel', 'id': match.group(1)}

    # Channel URL pattern (user)
    user_pattern = re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/user/([a-zA-Z0-9_-]+)')
    match = user_pattern.search(url)
    if match:
        username = match.group(1)
        response = youtube.channels().list(part='id', forUsername=username).execute()
        if 'items' in response and len(response['items']) > 0:
            return {'type': 'channel', 'id': response['items'][0]['id']}

    # Channel URL pattern (handle)
    handle_pattern = re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/@([a-zA-Z0-9_-]+)')
    match = handle_pattern.search(url)
    if match:
        handle = match.group(1)
        response = youtube.search().list(part='snippet', q=handle, type='channel').execute()
        if 'items' in response and len(response['items']) > 0:
            return {'type': 'channel', 'id': response['items'][0]['snippet']['channelId']}

    # Playlist URL pattern
    playlist_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/playlist\?list=|youtube\.com/embed/videoseries\?list=)([a-zA-Z0-9_-]+)')
    match = playlist_pattern.search(url)
    if match:
        return {'type': 'playlist', 'id': match.group(1)}

    return None

def get_videos(youtube, id_info, page_token=None, max_results=20):
    if id_info['type'] == 'video':
        request = youtube.videos().list(
            part="snippet",
            id=id_info['id']
        )
    elif id_info['type'] == 'channel':
        request = youtube.search().list(
            part="snippet",
            channelId=id_info['id'],
            maxResults=max_results,
            pageToken=page_token,
            order="date"
        )
    elif id_info['type'] == 'playlist':
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=id_info['id'],
            maxResults=max_results,
            pageToken=page_token
        )

    response = request.execute()

    videos = []
    next_page_token = response.get('nextPageToken')
    prev_page_token = response.get('prevPageToken', None)  # Store previous page token

    if id_info['type'] == 'video':
        for item in response['items']:
            video_info = {
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'publishedAt': item['snippet']['publishedAt'],
                'videoId': item['id'],
                'thumbnail': item['snippet']['thumbnails']['high']['url']
            }
            videos.append(video_info)
    elif id_info['type'] == 'channel' or id_info['type'] == 'playlist':
        for item in response['items']:
            video_id = item['snippet']['resourceId']['videoId'] if 'resourceId' in item['snippet'] else item['id'].get('videoId')
            if video_id:
                video_info = {
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'publishedAt': item['snippet']['publishedAt'],
                    'videoId': video_id,
                    'thumbnail': item['snippet']['thumbnails']['high']['url']
                }
                videos.append(video_info)

    return videos, next_page_token, prev_page_token

@app.route('/')
def index():
    error = request.args.get('error')
    favorites = load_favorites()
    return render_template('index.html', error=error, favorites=favorites)

@app.route('/search', methods=['POST'])
def search():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    youtube_url = request.form['youtube_url']
    id_info = extract_id(youtube, youtube_url)
    if not id_info:
        return redirect(url_for('index', error="Invalid YouTube URL"))

    videos, next_page_token, _ = get_videos(youtube, id_info)
    
    # Initialize page tokens
    session['page_tokens'] = [None]  # First page has no previous token
    
    return render_template('index.html', videos=videos, next_page_token=next_page_token, prev_page_token=None, id_info=id_info, favorites=load_favorites())

@app.route('/next', methods=['POST'])
def next_page():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    id_info = eval(request.form['id_info'])  # Convert string back to dictionary
    next_page_token = request.form['next_page_token']
    
    videos, new_next_page_token, prev_page_token = get_videos(youtube, id_info, page_token=next_page_token)
    
    # Store the next page token
    page_tokens = session.get('page_tokens', [])
    page_tokens.append(next_page_token)
    session['page_tokens'] = page_tokens
    
    return render_template('index.html', videos=videos, next_page_token=new_next_page_token, prev_page_token=prev_page_token, id_info=id_info, favorites=load_favorites())

@app.route('/prev', methods=['POST'])
def prev_page():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    id_info = eval(request.form['id_info'])  # Convert string back to dictionary
    
    page_tokens = session.get('page_tokens', [])
    prev_page_token = page_tokens.pop() if len(page_tokens) > 1 else None  # Get the last page token
    session['page_tokens'] = page_tokens
    
    videos, next_page_token, new_prev_page_token = get_videos(youtube, id_info, page_token=prev_page_token)
    
    return render_template('index.html', videos=videos, next_page_token=next_page_token, prev_page_token=new_prev_page_token, id_info=id_info, favorites=load_favorites())

@app.route('/add_favorite', methods=['POST'])
def add_favorite_route():
    data = request.get_json()
    name = data.get('name')
    url = data.get('url')
    add_favorite(name, url)
    return jsonify({'status': 'success'})

@app.route('/delete_favorite', methods=['POST'])
def delete_favorite_route():
    data = request.get_json()
    name = data.get('name')
    delete_favorite(name)
    return jsonify({'status': 'success'})

@app.route('/search_favorite', methods=['POST'])
def search_favorite_route():
    url = request.form['url']
    return search()

if __name__ == '__main__':
    app.run(debug=True)
