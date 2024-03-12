#spotify controller

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from functools import wraps
from spotipy.exceptions import SpotifyException

def handle_spotify_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 404 and 'NO_ACTIVE_DEVICE' in str(e):
                return "No active Spotify device found. Please ensure your Spotify is open and active on a device."
            else:
                return f"Spotify error occurred: {e}"
    return wrapper


class SpotifyController:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                            client_secret=client_secret,
                                                            redirect_uri=redirect_uri,
                                                            scope="user-read-playback-state,user-modify-playback-state"))
    
    @handle_spotify_exceptions
    def play_song(self, song_name):
        results = self.sp.search(q=song_name, limit=1)
        if results['tracks']['items']:
            track_id = results['tracks']['items'][0]['id']
            self.sp.start_playback(uris=[f'spotify:track:{track_id}'])
        else:
            print("Song not found")
            
    @handle_spotify_exceptions
    def play_artist_radio(self, artist_name):
        results = self.sp.search(q=artist_name, type='artist', limit=1)
        if results['artists']['items']:
            artist_id = results['artists']['items'][0]['id']
            self.sp.start_playback(context_uri=f'spotify:artist:{artist_id}')
        else:
            print("Artist not found")

    @handle_spotify_exceptions
    def play_album(self, album_name):
        results = self.sp.search(q=album_name, type='album', limit=1)
        if results['albums']['items']:
            album_id = results['albums']['items'][0]['id']
            self.sp.start_playback(context_uri=f'spotify:album:{album_id}')
        else:
            print("Album not found")

    @handle_spotify_exceptions
    def play_artist(self, artist_name):
        results = self.sp.search(q='artist:' + artist_name, type='artist', limit=1)
        if results['artists']['items']:
            artist_id = results['artists']['items'][0]['id']
            self.sp.start_playback(context_uri=f'spotify:artist:{artist_id}')
        else:
            print("Artist not found")
            
    @handle_spotify_exceptions
    def like_current_song(self):
        current_track = self.sp.current_playback()
        if current_track and current_track['item']:
            track_id = current_track['item']['id']
            self.sp.current_user_saved_tracks_add([track_id])
            print("Song liked successfully.")
        else:
            print("No song is currently playing.")
