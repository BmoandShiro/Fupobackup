Dont forget to setup all the settings and do the scan before use.
https://developer.spotify.com for api setup for your spotify account
asana tokens can be found on their developer portal as well.

To confirm spotify auth copy the URL that pops up even though the page says its an error the URL is the valid token you need to paste in ther terminal
If it says spotify instance isnt active then click play on spotify to actiavte instance
f24 is current macro keybind for listen 
run main file

mozilla drivers
https://github.com/mozilla/geckodriver

firefoxwebdrivergecko is essential for firefox api usage. 
firefox executable path is self explanatory had this feature fully working till github fucked me so i have to see what format this version requires i forget but not hard to figure out
i should add format examples in the settings text boxes

i am aware audio ducking has a few unintended issues if you try to change volume while active. not sure this feature is even worth debugging but very doable 

show microphones shows you the index number for your mic that you need to set however just dawned on me i didnt make a setting for this in the settings so you add the correct mic index to line 76 of desktop_assistant.py until i add this feature

very aware i didnt implement error handling yet so if you get an error itll likely freeze and need to be killed and restarted.
tried to compile to .exe but failed to get it to work yet.

havent ever tested add path but let me know if it works i couldnt find an app the auto scan didnt work for.

i should add a total list of commands here or in a menu in the app
for now heres the mains commands 

 def process_command(self, command):
     command = command.lower().strip()
     if command == "start essentials":
         return self.start_essential_apps()
     elif "create task" in command:
         task_start = command.find("task") + len("task")
         task_name = command[task_start:].strip()
         if task_name:
             return self.create_task('1206227946299762', task_name)
     elif command.startswith("start"):
          program_name = command[5:].strip()
          return self.start_program_with_confirmation(program_name)
     
     # Spotify commands
     elif "play song" in command:
         song_name = command.replace("play song", "").strip()
         play_result = self.spotify_controller.play_song(song_name)
         if isinstance(play_result, str):  # If the return value is a string (error message or confirmation)
             return play_result
         else:
             return f"Playing {song_name} on Spotify"

     elif "play artist radio" in command:
         artist_name = command.replace("play artist radio", "").strip()
         play_result = self.spotify_controller.play_artist_radio(artist_name)
         if isinstance(play_result, str):
             return play_result
         else:
             return f"Playing {artist_name} radio on Spotify"

     elif "play album" in command:
         album_name = command.replace("play album", "").strip()
         play_result = self.spotify_controller.play_album(album_name)
         if isinstance(play_result, str):
             return play_result
         else:
             return f"Playing album {album_name} on Spotify"

     elif "play artist" in command:
         artist_name = command.replace("play artist", "").strip()
         play_result = self.spotify_controller.play_artist(artist_name)
         if isinstance(play_result, str):
             return play_result
         else:
             return f"Playing music by {artist_name} on Spotify"

     elif "like song" in command or "favorite this track" in command:
         like_result = self.spotify_controller.like_current_song()
         if isinstance(like_result, str):
             return like_result
         else:
             return "Liked the current song on Spotify"
         
     elif "search google for" in command:
         # Extract the search query
         search_query = command.replace("search google for", "", 1).strip()
         # Perform the search using Google
         if search_query:
             self.firefox_search.search(search_query, engine='google')
             return f"Searching Google for {search_query}"
 
     elif "search bing for" in command:
         # Extract the search query
         search_query = command.replace("search bing for", "", 1).strip()
         # Perform the search using Bing
         if search_query:
             self.firefox_search.search(search_query, engine='bing')
             return f"Searching Bing for {search_query}"

 
     #normal defaults
     elif "hello" in command:
         return "Hello! How can I help you?"
     elif "how are you" in command:
         return "I'm fine, thank you!"
     else:
         return "I'm not sure how to respond to that."
     
     

 def play_song_on_spotify(self, song_name):
     self.spotify_controller.play_song(song_name)

 
 

 def start_program(self, program_name):
 # Check if the program_name exists in the list of executables
     if program_name in self.executables:
         try:
             # Start the program
             subprocess.Popen(self.executables[program_name], shell=True)
             return f"Started {program_name.capitalize()}."
         except Exception as e:
             return f"Error starting {program_name.capitalize()}: {e}"
     else:
         return f"{program_name.capitalize()} not found in the list of executables."
