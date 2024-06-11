# TinyTube Application

This is a Flask-based web application that allows users to search for YouTube videos, channels, and playlists using a YouTube API key. Users can also manage their favorite searches, which are stored and persisted across sessions.

The Python and HTML code are generated using GPT-4.
## Features

- Search for YouTube videos, channels, and playlists
- Save favorite searches with custom names
- Manage favorites (add/delete)
- Persist favorites across sessions

## Prerequisites

- Python 3.6 or higher
- A valid YouTube Data API v3 key

## Installation

1. **Clone the repository**:
   ```sh
   git clone https://github.com/SoumyaMishra/TinyTube.git
   cd TinyTube

2. **Create and activate a virtual environment**:
   ```sh
   python -m venv venv
   source venv/bin/activate   # On Windows use `venv\Scripts\activate`

3. **Install the dependencies**:
   ```sh
   pip install -r requirements.txt

4. **Configure the YouTube API key**:
 
- When you run the application for the first time, you will be prompted to enter your YouTube API key.
- The key will be stored in a config.json file.

## Running the Application

1. **Run the Flask application**:
   ```sh
   python app.py

2. **Open your web browser and navigate to http://127.0.0.1:5000/**

## Project Structure

TinyTube/
├── app.py
├── config.json
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── aurora.jpg
    └── favicon.ico
