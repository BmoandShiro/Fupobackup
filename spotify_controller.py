# spotify_controller.py

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from functools import wraps
import logging
import webbrowser  # Added to fix 'name 'webbrowser' is not defined' error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_spotify_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 404 and 'NO_ACTIVE_DEVICE' in str(e):
                return "No active Spotify device found. Please ensure your Spotify is open and active on a device."
            else:
                logger.error(f"Spotify error occurred: {e}")
                return f"Spotify error occurred: {e}"
    return wrapper

class SpotifyController:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.redirect_uri = redirect_uri if redirect_uri else "http://localhost"  # Default to original redirect URI
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                                client_secret=client_secret,
                                                                redirect_uri=self.redirect_uri,
                                                                scope="user-read-playback-state,user-modify-playback-state,user-library-modify,user-library-read,playlist-read-private,playlist-read-collaborative",
                                                                cache_path=".spotify_cache",
                                                                show_dialog=True))
            logger.info("Spotify controller initialized successfully.")
            # Verify authentication
            if self.sp:
                user = self.sp.current_user()
                logger.info(f"Authenticated as: {user['display_name']}")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify controller: {e}")
            self.sp = None
            self.handle_authentication_failure(client_id, client_secret, self.redirect_uri)

    def handle_authentication_failure(self, client_id, client_secret, redirect_uri):
        """Manually handle authentication if automatic flow fails."""
        auth_manager = SpotifyOAuth(client_id=client_id,
                                   client_secret=client_secret,
                                   redirect_uri=redirect_uri,
                                   scope="user-read-playback-state,user-modify-playback-state,user-library-modify,user-library-read,playlist-read-private,playlist-read-collaborative",
                                   cache_path=".spotify_cache",
                                   show_dialog=True)
        
        auth_url = auth_manager.get_authorize_url()
        logger.info(f"Opening browser for Spotify authentication: {auth_url}")
        webbrowser.open(auth_url)
        
        # Wait for user to complete authentication and paste the redirect URL
        redirect_response = input("Enter the URL you were redirected to: ")
        code = auth_manager.parse_response_code(redirect_response)
        if code:
            token_info = auth_manager.get_access_token(code)
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            logger.info("Manual authentication successful.")
        else:
            logger.error("Failed to parse authorization code. Authentication failed.")

    @handle_spotify_exceptions
    def play_song(self, song_name):
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        results = self.sp.search(q=song_name, limit=1, type='track')
        if results['tracks']['items']:
            track_id = results['tracks']['items'][0]['id']
            self.sp.start_playback(uris=[f'spotify:track:{track_id}'])
            self.sp.repeat('off')  # Disable repeat for single songs
            self.sp.shuffle(False)  # Enable shuffle to play related tracks after the song
            return True
        return "Song not found"
    
    @handle_spotify_exceptions
    def play_artist_radio(self, artist_name):
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        results = self.sp.search(q=artist_name, type='artist', limit=1)
        if results['artists']['items']:
            artist_id = results['artists']['items'][0]['id']
            self.sp.start_playback(context_uri=f'spotify:artist:{artist_id}')
            return True
        return "Artist not found"

    @handle_spotify_exceptions
    def play_album(self, album_name):
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        results = self.sp.search(q=album_name, type='album', limit=1)
        if results['albums']['items']:
            album_id = results['albums']['items'][0]['id']
            self.sp.start_playback(context_uri=f'spotify:album:{album_id}')
            self.sp.repeat('context')  # Enable repeat for the album
            self.sp.shuffle(False)  # Disable shuffle for album order
            return True
        return "Album not found"

    @handle_spotify_exceptions
    def play_artist(self, artist_name):
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        results = self.sp.search(q='artist:' + artist_name, type='artist', limit=1)
        if results['artists']['items']:
            artist_id = results['artists']['items'][0]['id']
            self.sp.start_playback(context_uri=f'spotify:artist:{artist_id}')
            self.sp.repeat('context')  # Enable repeat for continuous playback
            self.sp.shuffle(True)  # Enable shuffle for variety
            return True
        return "Artist not found"
    
    @handle_spotify_exceptions
    def play_playlist(self, playlist_name):
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        playlists = self.sp.current_user_playlists()
        for playlist in playlists['items']:
            if playlist_name.lower() in playlist['name'].lower():
                self.sp.start_playback(context_uri=playlist['uri'])
                self.sp.repeat('context')  # Enable repeat for continuous playback
                self.sp.shuffle(True)  # Enable shuffle for variety
                return True
        return "Playlist not found"

    @handle_spotify_exceptions
    def like_current_song(self):
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current_track = self.sp.current_playback()
        if current_track and current_track['item']:
            track_id = current_track['item']['id']
            self.sp.current_user_saved_tracks_add([track_id])
            return "Song liked successfully."
        return "No song is currently playing."

    @handle_spotify_exceptions
    def unlike_current_song(self):
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current_track = self.sp.current_playback()
        if current_track and current_track['item']:
            track_id = current_track['item']['id']
            self.sp.current_user_saved_tracks_delete([track_id])
            return "Song unliked successfully."
        return "No song is currently playing."

    @handle_spotify_exceptions
    def play_daylist(self):
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        playlists = self.sp.current_user_playlists()
        for playlist in playlists['items']:
            if "daylist" in playlist['name'].lower():
                self.sp.start_playback(context_uri=playlist['uri'])
                self.sp.repeat('context')
                self.sp.shuffle(True)
                return "Playing your Daylist on Spotify"
        return "Daylist not found. Please check your Spotify playlists for a Daylist."