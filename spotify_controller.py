# spotify_controller.py

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from functools import wraps
import logging
import webbrowser  # Added to fix 'name 'webbrowser' is not defined' error
import time
from threading import Timer

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
        self._volume_before_mute = None  # Restored by unmute()
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
    
    @handle_spotify_exceptions
    def play_liked_song(self, song_name):
        """Play a song by name from the user's liked tracks."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        results = self.sp.current_user_saved_tracks(limit=50)  # Fetch up to 50 liked tracks at a time
        found = False
        while results and not found:
            for item in results['items']:
                track = item['track']
                if song_name.lower() in track['name'].lower():
                    self.sp.start_playback(uris=[f'spotify:track:{track["id"]}'])
                    self.sp.repeat('off')  # Disable repeat for single songs
                    self.sp.shuffle(True)  # Enable shuffle for related tracks
                    return f"Playing {track['name']} by {track['artists'][0]['name']} from your liked songs"
            if results['next']:
                results = self.sp.next(results)  # Paginate to fetch more liked tracks
            else:
                break
        return f"Song '{song_name}' not found in your liked tracks."

    @handle_spotify_exceptions
    def pause_playback(self):
        """Pause the current playback."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        self.sp.pause_playback()
        return "Playback paused."

    @handle_spotify_exceptions
    def resume_playback(self):
        """Resume the current playback."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        self.sp.start_playback()
        return "Playback resumed."

    @handle_spotify_exceptions
    def skip_track(self):
        """Skip to the next track."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        self.sp.next_track()
        return "Skipped to the next track."

    @handle_spotify_exceptions
    def previous_track(self):
        """Go back to the previous track."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        self.sp.previous_track()
        return "Returned to the previous track."

    @handle_spotify_exceptions
    def get_current_song(self):
        """Get the name and artist of the currently playing song."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current_track = self.sp.current_playback()
        if current_track and current_track['item']:
            return f"Currently playing: {current_track['item']['name']} by {current_track['item']['artists'][0]['name']}"
        return "No song is currently playing."

    @handle_spotify_exceptions
    def get_current_track_uri(self):
        """Get the URI of the currently playing track, or None."""
        if not self.sp:
            return None
        current = self.sp.current_playback()
        if current and current.get('item') and current['item'].get('uri'):
            return current['item']['uri']
        return None

    @handle_spotify_exceptions
    def play_liked_songs(self):
        """Start playing the user's Liked Songs library."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        results = self.sp.current_user_saved_tracks(limit=50)
        if not results or not results.get('items'):
            return "No liked songs found."
        uris = [item['track']['uri'] for item in results['items'] if item.get('track') and item['track'].get('uri')]
        if not uris:
            return "No liked songs found."
        self.sp.start_playback(uris=uris)
        self.sp.shuffle(True)
        return "Playing your liked songs."

    @handle_spotify_exceptions
    def _play_named_playlist(self, name_substring):
        """Find a user playlist whose name contains the given string (case-insensitive) and play it."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        playlists = self.sp.current_user_playlists(limit=50)
        for p in playlists.get('items', []):
            if name_substring.lower() in (p.get('name') or '').lower():
                self.sp.start_playback(context_uri=p['uri'])
                return f"Playing {p['name']}."
        return f"Playlist '{name_substring}' not found."

    @handle_spotify_exceptions
    def play_discover_weekly(self):
        return self._play_named_playlist("Discover Weekly")

    @handle_spotify_exceptions
    def play_release_radar(self):
        return self._play_named_playlist("Release Radar")

    @handle_spotify_exceptions
    def mute(self):
        """Set Spotify volume to 0 (mute). Stores current volume for unmute."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current = self.sp.current_playback()
        if current and current.get("device") and "volume_percent" in current["device"]:
            self._volume_before_mute = current["device"]["volume_percent"]
        self.sp.volume(0)
        return "Spotify muted."

    @handle_spotify_exceptions
    def unmute(self):
        """Restore Spotify volume (to value before mute, or 70% if unknown)."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        vol = self._volume_before_mute if self._volume_before_mute is not None else 70
        vol = min(100, max(0, vol))
        self.sp.volume(vol)
        self._volume_before_mute = None
        return f"Spotify unmuted (volume {vol}%)."

    @handle_spotify_exceptions
    def play_similar(self):
        """Play recommendations based on the current track."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current = self.sp.current_playback()
        if not current or not current.get('item') or not current['item'].get('id'):
            return "No track playing. Play something first, then say 'play something similar'."
        track_id = current['item']['id']
        recs = self.sp.recommendations(seed_tracks=[track_id], limit=20)
        uris = [f"spotify:track:{t['id']}" for t in recs['tracks']]
        if not uris:
            return "Could not get recommendations."
        self.sp.start_playback(uris=uris)
        self.sp.shuffle(True)
        return "Playing similar tracks."

    @handle_spotify_exceptions
    def add_to_queue(self, track_uri_or_query):
        """Add a track to the queue. Pass a spotify:track: URI or a search query string."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        if track_uri_or_query.startswith('spotify:track:'):
            uri = track_uri_or_query
        else:
            results = self.sp.search(q=track_uri_or_query, type='track', limit=1)
            if not results['tracks']['items']:
                return f"Track '{track_uri_or_query}' not found."
            uri = f"spotify:track:{results['tracks']['items'][0]['id']}"
        self.sp.add_to_queue(uri)
        return "Added to queue."

    @handle_spotify_exceptions
    def toggle_shuffle(self):
        """Toggle shuffle mode."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current_state = self.sp.shuffle()['shuffle']
        self.sp.shuffle(not current_state)
        return f"Shuffle {'enabled' if not current_state else 'disabled'}."

    @handle_spotify_exceptions
    def toggle_repeat(self):
        """Toggle repeat mode (off -> context -> track)."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current_state = self.sp.repeat()['repeat_state']
        if current_state == 'off':
            new_state = 'context'
        elif current_state == 'context':
            new_state = 'track'
        else:  # 'track'
            new_state = 'off'
        self.sp.repeat(new_state)
        return f"Repeat set to {'context' if new_state == 'context' else 'track' if new_state == 'track' else 'off'}."
    
    @handle_spotify_exceptions
    def create_playlist(self, playlist_name, description="Created via Desktop Assistant"):
        """Create a new playlist with the given name and optional description."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        user_id = self.sp.current_user()['id']
        playlist = self.sp.user_playlist_create(user_id, playlist_name, public=True, description=description)
        return f"Created playlist '{playlist_name}' with ID {playlist['id']}"

    @handle_spotify_exceptions
    def add_to_playlist(self, playlist_name, track_uri):
        """Add a track to an existing playlist by name."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        playlists = self.sp.current_user_playlists()
        playlist_id = None
        for playlist in playlists['items']:
            if playlist_name.lower() in playlist['name'].lower():
                playlist_id = playlist['id']
                break
        if not playlist_id:
            return f"Playlist '{playlist_name}' not found."
        self.sp.playlist_add_items(playlist_id, [track_uri])
        return f"Added track to playlist '{playlist_name}'"

    @handle_spotify_exceptions
    def delete_playlist(self, playlist_name):
        """Delete an existing playlist by name."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        playlists = self.sp.current_user_playlists()
        playlist_id = None
        for playlist in playlists['items']:
            if playlist_name.lower() in playlist['name'].lower():
                playlist_id = playlist['id']
                break
        if not playlist_id:
            return f"Playlist '{playlist_name}' not found."
        self.sp.current_user_unfollow_playlist(playlist_id)
        return f"Deleted playlist '{playlist_name}'"

    def get_current_volume(self):
        """Return current Spotify device volume (0-100) or None if unavailable."""
        if not self.sp:
            return None
        try:
            current = self.sp.current_playback()
            if current and current.get("device") and "volume_percent" in current["device"]:
                return current["device"]["volume_percent"]
        except Exception:
            pass
        return None

    @handle_spotify_exceptions
    def set_volume(self, volume_percent):
        """Set Spotify playback volume (0-100)."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        if not 0 <= volume_percent <= 100:
            return "Volume must be between 0 and 100."
        self.sp.volume(volume_percent)
        return f"Set Spotify volume to {volume_percent}%"

    @handle_spotify_exceptions
    def increase_volume(self, amount=10):
        """Increase Spotify volume by a specified amount (default 10%)."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current_playback = self.sp.current_playback()
        if current_playback and 'device' in current_playback and 'volume_percent' in current_playback['device']:
            current_volume = current_playback['device']['volume_percent']
            new_volume = min(100, current_volume + amount)  # Cap at 100
            self.sp.volume(new_volume)
            return f"Increased Spotify volume to {new_volume}%"
        return "Could not retrieve current volume."

    @handle_spotify_exceptions
    def decrease_volume(self, amount=10):
        """Decrease Spotify volume by a specified amount (default 10%)."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        current_playback = self.sp.current_playback()
        if current_playback and 'device' in current_playback and 'volume_percent' in current_playback['device']:
            current_volume = current_playback['device']['volume_percent']
            new_volume = max(0, current_volume - amount)  # Cap at 0
            self.sp.volume(new_volume)
            return f"Decreased Spotify volume to {new_volume}%"
        return "Could not retrieve current volume."

    @handle_spotify_exceptions
    def get_recommendations(self, seed_type, seed_value, limit=10):
        """Get recommendations based on a song, artist, or genre."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        if seed_type == "song":
            results = self.sp.search(q=seed_value, type='track', limit=1)
            if results['tracks']['items']:
                seed_id = results['tracks']['items'][0]['id']
                recommendations = self.sp.recommendations(seed_tracks=[seed_id], limit=limit)
            else:
                return f"Song '{seed_value}' not found."
        elif seed_type == "artist":
            results = self.sp.search(q=seed_value, type='artist', limit=1)
            if results['artists']['items']:
                seed_id = results['artists']['items'][0]['id']
                recommendations = self.sp.recommendations(seed_artists=[seed_id], limit=limit)
            else:
                return f"Artist '{seed_value}' not found."
        elif seed_type == "genre":
            recommendations = self.sp.recommendations(seed_genres=[seed_value.lower()], limit=limit)
        else:
            return "Invalid seed type. Use 'song', 'artist', or 'genre'."
        
        track_uris = [f'spotify:track:{track["id"]}' for track in recommendations['tracks']]
        self.sp.start_playback(uris=track_uris)
        self.sp.repeat('context')
        self.sp.shuffle(True)
        return f"Playing {limit} recommendations based on {seed_type} '{seed_value}'"

    def stop_after_time(self, seconds):
        """Stop playback after a specified time (in seconds)."""
        if not self.sp:
            return "Spotify not initialized. Check authentication."
        def stop_playback():
            try:
                self.sp.pause_playback()
                logger.info("Playback stopped after timer.")
            except Exception as e:
                logger.error(f"Error stopping playback: {e}")
        timer = Timer(seconds, stop_playback)
        timer.start()
        return f"Playback will stop after {seconds} seconds"