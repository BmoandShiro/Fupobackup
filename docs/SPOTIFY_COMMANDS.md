# Spotify voice/text commands

## Currently supported (API + desktop app)

| Command (examples) | What it does |
|-------------------|--------------|
| **Play song [name]** / *Play a song Ain't No Rest for the Wicked* | Search and play a track (optional: *... by [artist]*). |
| **Play song [name] from my liked songs** | Play a specific track from your Liked Songs. |
| **Play artist [name]** | Start playing an artist's top tracks (shuffled). |
| **Play artist radio [name]** / *Play radio [name]* | Play artist radio. |
| **Play album [name]** | Play an album. |
| **Play playlist [name]** | Play one of your playlists by name. |
| **Play daylist** | Play your Spotify Daylist. |
| **Pause** | Pause playback. |
| **Resume** / **Play music** | Resume playback. |
| **Skip** / **Next** | Skip to next track. |
| **Previous** / **Back** | Go to previous track. |
| **What's playing** / **Current song** / **Check song** | Say what track is playing. |
| **Like song** / **Favorite song** | Add current track to Liked Songs. |
| **Unlike song** / **Remove song** / **Unfavorite song** | Remove current track from Liked Songs. |
| **Toggle shuffle** / **Switch shuffle** | Turn shuffle on/off. |
| **Toggle repeat** / **Switch repeat** | Cycle repeat off → context → track. |

---

## In SpotifyController but not wired in API (assistant_core)

These exist in `spotify_controller.py` and in the **desktop (Qt) app** but are **not** in the **web/API** command runner yet:

| Intent | Example phrase | Controller method |
|--------|----------------|-------------------|
| Set volume | *Set Spotify volume to 50%* | `set_volume(percent)` |
| Increase volume | *Increase Spotify volume* / *... by 20%* | `increase_volume(amount)` |
| Decrease volume | *Decrease Spotify volume* / *... by 10%* | `decrease_volume(amount)` |
| Create playlist | *Create a playlist called [name]* | `create_playlist(name)` |
| Add to playlist | *Add this song to my [name] playlist* | `add_to_playlist(name, track_uri)` |
| Delete playlist | *Delete playlist [name]* | `delete_playlist(name)` |
| Recommendations | *Recommend songs like [X]* / *Find [genre] music* | `get_recommendations(seed_type, seed_value)` |
| Timed playback | *Play music for 30 minutes then stop* | `stop_after_time(seconds)` |

---

## Recommended additions

### 1. Wire existing controller methods in API (assistant_core)

- **Volume:** set / increase / decrease Spotify volume (phrases above).
- **Playlists:** create playlist, add current song to playlist, delete playlist.
- **Recommendations:** e.g. *Recommend songs like [song/artist]* or *Find [genre] music*.
- **Timed playback:** *Play music for [N] minutes/hours then stop*.

### 2. New controller + commands (if you extend spotify_controller)

| Idea | Example phrase | Notes |
|------|----------------|--------|
| **Play Liked Songs** | *Play my liked songs* | Start playing saved tracks (context_uri for user’s saved tracks). |
| **Discover Weekly** | *Play Discover Weekly* | Play the Discover Weekly playlist (fixed name or ID). |
| **Release Radar** | *Play Release Radar* | Same for Release Radar. |
| **Play genre** | *Play [genre] music* / *Play rock* | Use recommendations with `seed_genres` or search. |
| **Mute** | *Mute Spotify* | Set volume to 0 or pause (and optionally remember previous volume). |
| **Play similar** | *Play something similar* / *More like this* | Recommendations from current track. |
| **Add to queue** | *Add this to queue* / *Add [song] to queue* | Add current or searched track to queue (Spotify Web API: add to queue). |
| **Clear queue** | *Clear queue* | Not in standard Web API; could map to “skip until end” or document as unsupported. |
| **Transfer playback** | *Play on [device name]* | `transfer_playback(device_id)` for multi-device. |
| **Save album** | *Save this album* | Add current album to library. |
| **Play top tracks** | *Play top tracks by [artist]* | Artist’s top tracks (already similar to play_artist). |

### 3. Quick wins (no new backend logic)

- **Aliases:** e.g. *What’s playing* → same as *Current song* (already covered).
- **Shorter phrases:** e.g. *Volume up/down* → map to increase/decrease volume once volume is wired in API.

---

## Where it’s implemented

- **Intent detection (keywords):** `backend/assistant_core.py` → `_simple_intent()`
- **Execution:** `backend/assistant_core.py` → `run_command()` (API), `desktop_assistant.py` → `process_command()` (Qt app)
- **Spotify calls:** `spotify_controller.py` → `SpotifyController` methods

To add a command: extend `_simple_intent()` for the new phrase pattern, then in `run_command()` handle that intent and call the right `SpotifyController` method.
