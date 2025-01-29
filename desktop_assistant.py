
import speech_recognition as sr
import pyttsx3
import threading
import spacy
import os
import json
from fuzzywuzzy import process, fuzz
import subprocess
import winreg
import win32com.client
import asana
import pythoncom
import keyboard
from spotify_controller import SpotifyController  # Import SpotifyController here
from audio_ducking import monitor_and_adjust_volume, smooth_adjust_volume
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pythoncom
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QProgressBar, QCheckBox, QStyleFactory, QLineEdit, QDialog, QInputDialog, QMessageBox
from PyQt6.QtGui import QPalette, QColor, QAction
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from firefoxbrowsersearch import FirefoxBrowserSearch
import sys
from weather_api import WeatherAPI



class DesktopAssistant(QWidget):
    # Define the signals at the class level
    confirmationSignal = pyqtSignal(str)
    updateLabelSignal = pyqtSignal(str)  # Add this line


    def initialize_key_listener(self):
        macro_key = self.load_setting("macro_key", "F24")
        macro_key_hold = self.load_setting("macro_key_hold", False)

        if macro_key_hold:
            # Implement logic for hold behavior
            def on_press(event):
                self.listen_and_respond()  # Example action, modify as needed
        
            def on_release(event):
                # Possibly stop listening or other action on release
                pass

            keyboard.on_press_key(macro_key, on_press)
            keyboard.on_release_key(macro_key, on_release)
        else:
            # Original behavior for single press
            keyboard.add_hotkey(macro_key, self.listen_and_respond)
        
    def __init__(self, window):
        super().__init__()  # Initialize the parent QWidget class
        self.window = window
        self.configure_dark_theme()
        
        # Connect the signal to the slot
        self.confirmationSignal.connect(self.confirm_start_program)
        
        # Connect signals to slots havent tested if i need all 4 of these but its working so not touching it
        self.confirmationSignal.connect(self.confirm_start_program)
        self.updateLabelSignal.connect(self.update_label)  # Add this line
        
        # You will need to define a new signal for confirmation
        confirmationSignal = pyqtSignal(str)

        # Connect this signal to a new slot that will handle the confirmation
        self.confirmationSignal.connect(self.confirm_start_program)
        
        # Audio ducking
        self.init_volume_control()  # Initialize volume control at the start
        self.audio_ducking_enabled = False  # Replaces the tk.BooleanVar()
        self.ducking_thread = None
        self.ducking_stop_event = threading.Event()
        
        self.load_settings()
        asana_token = self.load_setting("asana_token", "")
        if asana_token:
            self.client = asana.Client.access_token(asana_token)
        else:
            # Handle case where Asana token is not set
            self.client = None  # Or some other default behavior

        self.executables = self.load_executables()
        self.desktop_shortcuts = self.find_shortcuts(os.path.join(os.environ['USERPROFILE'], 'Desktop'))
        self.create_widgets()
        self.nlp = spacy.load("en_core_web_sm")
        self.mic = sr.Microphone(device_index=1)
        self.initialize_key_listener()
        spotify_client_id = self.load_setting("spotify_client_id", "")
        spotify_client_secret = self.load_setting("spotify_client_secret", "")
        spotify_redirect_uri = self.load_setting("spotify_redirect_uri", "")
        if spotify_client_id and spotify_client_secret and spotify_redirect_uri:
            self.spotify_controller = SpotifyController(spotify_client_id, spotify_client_secret, spotify_redirect_uri)
        else:
            # Handle case where Spotify settings are not set
            self.spotify_controller = None  # Or some other default behavior
        self.create_settings_menu()
        
        # Initialize the browser settings for Firefox
        self.firefox_service = FirefoxService(executable_path=self.load_setting("geckodriver_path", "path_to_geckodriver"))
        self.firefox_options = webdriver.FirefoxOptions()
        self.firefox_options.binary_location = self.load_setting("firefox_path", "path_to_firefox")

        # Now create a method to start Firefox with these settings
        # Initialize FirefoxBrowserSearch but do not start the browser
        self.firefox_search = FirefoxBrowserSearch("settings.json")

        #weather
        self.weather_api = WeatherAPI()

    def start_firefox_browser(self):
        # This method starts the Firefox browser with the specified options and service
        geckodriver_path = self.load_setting("geckodriver_path", "path_to_geckodriver")
        firefox_path = self.load_setting("firefox_path", "path_to_firefox")
    
        self.firefox_service = FirefoxService(executable_path=geckodriver_path)
        self.firefox_options = webdriver.FirefoxOptions()
        self.firefox_options.binary_location = firefox_path

        try:
            self.firefox_browser = webdriver.Firefox(service=self.firefox_service, options=self.firefox_options)
            print("Firefox WebDriver started successfully.")
        except Exception as e:
            print(f"Failed to start Firefox WebDriver: {e}")
            
        


        
        
        

    
        
    def configure_dark_theme(self):
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor("#333"))
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor('white'))

        QApplication.setPalette(dark_palette)

    from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QProgressBar, QCheckBox

    def create_widgets(self):
        self.layout = QVBoxLayout(self.window)

        # Label
        self.label = QLabel("Welcome to your Desktop Assistant!", self.window)
        self.layout.addWidget(self.label)

        # Listen Button
        self.listen_button = QPushButton("Listen", self.window)
        self.listen_button.clicked.connect(self.on_listen)
        self.layout.addWidget(self.listen_button)
        
        # Adding the reset button to the main window as an example
        self.reset_button = QPushButton("Reset Application")
        self.reset_button.clicked.connect(self.reset_application)
        self.layout.addWidget(self.reset_button)


        # Scan Button
        self.scan_button = QPushButton("Scan for Programs", self.window)
        self.scan_button.clicked.connect(self.on_scan)
        self.layout.addWidget(self.scan_button)

        # Microphone Button
        self.mic_button = QPushButton("Show Microphones", self.window)
        self.mic_button.clicked.connect(self.show_mics)
        self.layout.addWidget(self.mic_button)

        # Shortcuts Button
        self.shortcuts_button = QPushButton("Show Shortcuts", self.window)
        self.shortcuts_button.clicked.connect(self.show_shortcuts)
        self.layout.addWidget(self.shortcuts_button)

        # Add Path Button
        self.add_path_button = QPushButton("Add Path...", self.window)
        self.add_path_button.clicked.connect(self.prompt_path_entry)
        self.layout.addWidget(self.add_path_button)

        # Progress Bar
        self.progress = QProgressBar(self.window)
        self.progress.setMaximum(100)
        self.layout.addWidget(self.progress)

        # Progress Label
        self.progress_label = QLabel("0%", self.window)
        self.layout.addWidget(self.progress_label)

        # Audio Ducking Checkbox
        self.ducking_checkbox = QCheckBox("Toggle Audio Ducking", self.window)
        self.ducking_checkbox.stateChanged.connect(self.toggle_audio_ducking)
        self.layout.addWidget(self.ducking_checkbox)

        self.setLayout(self.layout)

    
    def init_volume_control(self):
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.volume = cast(interface, POINTER(IAudioEndpointVolume))
        self.original_volume_level = self.volume.GetMasterVolumeLevelScalar()  # Correctly define the original volume level


    def prompt_path_entry(self):
        path, ok = QInputDialog.getText(self, "Input", "Enter the executable path:")
        if ok and path:
            self.add_path_to_executables(path)

            
    def find_executables(self, directory):
        exclusions = ["update", "uninstall"]  # Exclude any .exe containing these words i dont this is working or maybe just not for shortcuts. instead just verify proper shortcut is on desktop
        executables = {}
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_lower = file.lower()
                if file_lower.endswith(".exe") and not any(excl in file_lower for excl in exclusions):
                    exec_name = os.path.splitext(file)[0].lower()
                    executables[exec_name] = os.path.join(root, file)
        return executables

    def reset_application(self):
        """Restart the application."""
        python = sys.executable
        os.execl(python, python, *sys.argv)
        
    def initialize_reset_macro(self):
        # Assuming 'reset_application' is the method you want to trigger
        reset_macro_key = self.load_setting("reset_macro_key", "F23")  # Defaulting to F23 if no specific setting is saved

        # Clear existing hotkeys to avoid conflicts if needed commented out below
        #keyboard.unhook_all_hotkeys()
    
        # Register the new macro key to trigger 'reset_application'
        keyboard.add_hotkey(reset_macro_key, self.reset_application)
        
        print(f"Reset macro key set to: {reset_macro_key}")



    
    def get_installed_programs(self):
        installed_programs = {}
        try:
            # Use the "wmic" command to list installed programs
            process = subprocess.Popen("wmic product get name,version", stdout=subprocess.PIPE, universal_newlines=True, shell=True)
            output, _ = process.communicate()

            # Split the output into lines and extract program names and versions
            lines = output.split('\n')
            for line in lines:
                if line.strip() and not line.startswith("Name"):
                    parts = line.strip().split()
                    program_name = ' '.join(parts[:-1])  # Combine parts to get the program name
                    installed_programs[program_name.lower()] = ""
        except Exception as e:
            print(f"Error getting installed programs: {e}")
        return installed_programs
            
    
    def show_mics(self):
        mic_list = sr.Microphone.list_microphone_names()
        formatted_mic_list = [f"Microphone with name \"{name}\" found for `Microphone(device_index={index})`"
                              for index, name in enumerate(mic_list)]
        mic_string = "\n".join(formatted_mic_list)
        self.label.setText(mic_string)

    def show_shortcuts(self):
        shortcut_list = "\n".join([f"{name}: {path}" for name, path in self.desktop_shortcuts.items()])
        self.label.setText(shortcut_list)

    def add_path_to_executables(self, path):
        # This method now takes 'path' as an argument
        exec_name = os.path.basename(path)
        self.executables[exec_name.lower()] = path
        self.save_executables(self.executables)
        self.label.config(text=f"Added {exec_name} to the list")

    def on_listen(self):
        threading.Thread(target=self.listen_and_respond).start()

    def listen_and_respond(self):
        pythoncom.CoInitialize()
        try:
            command = self.listen_command()
            response = self.process_command(command)  # 🔍 Can return 1 or 2 values

            # ✅ Ensure response is always a tuple
            if isinstance(response, tuple) and len(response) == 2:
                display_message, spoken_message = response  # Normal case
            else:
                display_message, spoken_message = response, response  # Wrap single responses

            self.speak(spoken_message)  # 🎙️ Speak only the relevant message
            self.updateLabelSignal.emit(display_message)  # 🖥️ Update GUI with the full display message
        finally:
            pythoncom.CoUninitialize()


    # The slot that updates the label
    def update_label(self, text):
        if self.label is not None:
            self.label.setText(text)
            
    def confirm_start_program(self, best_match):
        reply = QMessageBox.question(self, "Confirm", f"Did you mean '{best_match}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # If the user confirms, start the program
            self.start_program(best_match)
        else:
            self.updateLabelSignal.emit("Operation cancelled by user.")

    def update_label(self, text):
        # Ensure GUI updates are made in the main thread
        if self.label is not None:
            self.label.setText(text)  # Update the label's text

    @staticmethod
    def load_executables(filename='executables.json'):
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    @staticmethod
    def save_executables(executables, filename='executables.json'):
        with open(filename, 'w') as file:  # 'w' mode will overwrite the file
            json.dump(executables, file, indent=4)  # Use indent for pretty-printing

    def find_shortcuts(self, directory):
        shortcuts = {}
        for file in os.listdir(directory):
            if file.lower().endswith(".lnk"):
                shortcut_path = os.path.join(directory, file)
                target_path = self.get_shortcut_target(shortcut_path)
                if target_path and target_path.endswith('.exe'):
                    shortcut_name = os.path.splitext(file)[0].lower()
                    shortcuts[shortcut_name] = target_path
                    # Update the executables dictionary if the shortcut name is found
                    if shortcut_name in self.executables:
                        self.executables[shortcut_name] = target_path
        return shortcuts
    
    

    @staticmethod
    def get_shortcut_target(shortcut_path):
        shell = win32com.client.Dispatch("WScript.Shell")
        try:
            shortcut = shell.CreateShortcut(shortcut_path)
            return shortcut.Targetpath
        except Exception as e:
            print(f"Error reading shortcut: {e}")
            return None

    # ... other methods ...

    def speak(self, text):
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

    def listen_command(self):
        r = sr.Recognizer()
        with self.mic as source:
            print("Listening...")
            audio = r.listen(source)

        try:
            command = r.recognize_google(audio).lower()
            print("You said: " + command)
            return command
        except sr.UnknownValueError:
            print("Sorry, I did not understand that.")
        except sr.RequestError:
            print("Could not request results; check your internet connection.")
        return ""

    def create_task(self, project_id, task_name):
        try:
            # Assuming 'client' is your authenticated Asana client
            result = self.client.tasks.create({
                'name': task_name,
                'projects': [project_id]
            })
            print(f"Task created: {result}")
            return f"Task '{task_name}' created successfully."
        except asana.error.AsanaError as e:
            print(f"Error creating task: {e}")
            return f"Error: {e}"
        except Exception as e:
            print(f"General Error: {e}")
            return f"General Error: {e}"
        
    def start_program_with_confirmation(self, spoken_name):
        # Find the best match for the spoken name
        best_match, best_match_score = process.extractOne(spoken_name, self.executables.keys())

        # If the best match score is 100, start the program directly
        if best_match_score == 100:
            return self.start_program(best_match)
        # If the match is not perfect, ask for confirmation
        elif best_match_score >= 84:
            # Emit a signal to show the confirmation dialog in the main thread
            self.confirmationSignal.emit(best_match)
        else:
            return f"Could not find a close match for '{spoken_name}'. Please try again."

    

    # Define the new slot that shows the confirmation dialog
    def confirm_start_program(self, best_match):
        reply = QMessageBox.question(self, "Confirm", f"Did you mean '{best_match}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # If the user confirms, start the program
            self.start_program(best_match)
        else:
            self.updateLabelSignal.emit(f"Operation cancelled by user.")
        
    def start_essential_apps(self):
        essential_apps = ["discord", "signal", "opera gx browser", "lorexcloud"]
        status_messages = []

        for app in essential_apps:
            if app.lower() in self.executables:
                try:
                    subprocess.Popen(self.executables[app.lower()], shell=True)
                    status_messages.append(f"Started {app.capitalize()}.")
                except Exception as e:
                    status_messages.append(f"Error starting {app.capitalize()}: {e}")
            else:
                status_messages.append(f"{app.capitalize()} not found in the list of executables.")
    
        return "\n".join(status_messages)
        

    def process_command(self, command):
        command = command.lower().strip()
        
        #weather
        # Check if the user is asking about the weather 
        # Get Weather in your city
        if "weather" in command:
            detailed_weather_requested = "detailed weather" in command  # Detect detailed request
            location = command.replace("detailed weather", "").replace("weather", "").strip()
        
            if not location:  # If no location provided, use auto-location
                location = "auto"
        
            display_message, spoken_message = self.weather_api.get_weather(location, spoken_request=command, detailed=detailed_weather_requested)

            return display_message, spoken_message




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
        

    def update_progress_bar(self, value):
        # Calculate percentage and ensure it's an integer
        percentage = int(value)  # Convert value to int to avoid TypeError

        # Schedule the UI update to be run in the main thread
        self.progress_bar_set(percentage, f"{percentage}%")

    def progress_bar_set(self, value, text):
        # Ensure GUI updates are made in the main thread
        if self.progress is not None and self.progress_label is not None:
            self.progress.setValue(value)  # Update the progress bar's value
            self.progress_label.setText(text)  # Update the progress label's text

        
    def on_scan(self):
        # Clear the existing executables before scanning
        self.executables.clear()
    
        # Start the scanning process in a new thread
        threading.Thread(target=self.scan_process, daemon=True).start()
        

    def scan_process(self):
        # Initialize COM library for the new thread
        pythoncom.CoInitialize()

        paths_to_scan = [
            os.environ['ProgramFiles'],
            os.environ['ProgramFiles(x86)'],
            os.environ['APPDATA'] + '\\Microsoft\\Windows\\Start Menu\\Programs',
            "D:\\",
            "F:\\",
        ]
        total_paths = len(paths_to_scan)
    
        for index, path in enumerate(paths_to_scan, start=1):
            executables_found = self.find_executables(path)
            self.executables.update(executables_found)
        
            # Update the UI with the progress in a thread-safe manner
            self.update_progress_bar((index / total_paths) * 100)
    
        # Find shortcuts and update executables with correct paths
        self.desktop_shortcuts = self.find_shortcuts(os.path.join(os.environ['USERPROFILE'], 'Desktop'))
        for name, path in self.desktop_shortcuts.items():
            self.executables[name] = path
    
        # Save the updated executables dictionary to a file
        self.save_executables(self.executables)
        print("Saved executables to executables.json.")
        
        # Reset the progress bar and update the label to indicate completion
        self.update_progress_bar(100)
        QTimer.singleShot(0, lambda: self.label.setText("Scan complete!"))
        
        pythoncom.CoUninitialize()
        

       
        
        def listen_and_respond(self):
            try:
                command = self.listen_command()
                if command:
                    response = self.process_command(command)
                    self.speak(response)
                    self.root.after(0, self.update_label, response)
            except Exception as e:
                print(f"Error in listen_and_respond: {e}")
                self.root.after(0, self.update_label, "An error occurred.")


    def create_settings_menu(self):
        # Create a menu item in the main window
        menu_bar = self.window.menuBar()

        settings_menu = menu_bar.addMenu("&Settings")
        
        # QAction for opening settings window
        settings_action = QAction("Configure Settings", self.window)

        settings_action.triggered.connect(self.open_settings_window)
        settings_menu.addAction(settings_action)

    def open_settings_window(self):
        # Open a new dialog for settings
        self.settings_window = QDialog(self.window)
        self.settings_window.setWindowTitle("Settings")
        layout = QVBoxLayout(self.settings_window)

        # Spotify Client ID
        layout.addWidget(QLabel("Spotify Client ID"))
        self.spotify_client_id_entry = QLineEdit()
        self.spotify_client_id_entry.setText(self.load_setting("spotify_client_id", ""))
        layout.addWidget(self.spotify_client_id_entry)

        # Spotify Client Secret
        layout.addWidget(QLabel("Spotify Client Secret"))
        self.spotify_client_secret_entry = QLineEdit()
        self.spotify_client_secret_entry.setText(self.load_setting("spotify_client_secret", ""))
        layout.addWidget(self.spotify_client_secret_entry)

        # Spotify Redirect URI
        layout.addWidget(QLabel("Spotify Redirect URI"))
        self.spotify_redirect_uri_entry = QLineEdit()
        self.spotify_redirect_uri_entry.setText(self.load_setting("spotify_redirect_uri", ""))
        layout.addWidget(self.spotify_redirect_uri_entry)

        # Asana Access Token
        layout.addWidget(QLabel("Asana Access Token"))
        self.asana_token_entry = QLineEdit()
        self.asana_token_entry.setText(self.load_setting("asana_token", ""))
        layout.addWidget(self.asana_token_entry)

        # Firefox Browser Executable
        layout.addWidget(QLabel("Firefox Executable Path"))
        self.firefox_browser_exe_entry = QLineEdit()
        self.firefox_browser_exe_entry.setText(self.load_setting("firefox_path", ""))
        layout.addWidget(self.firefox_browser_exe_entry)

        # Firefox WebDriver (geckodriver) Executable
        layout.addWidget(QLabel("Firefox WebDriver (geckodriver) Path"))
        self.geckodriver_path_entry = QLineEdit()
        self.geckodriver_path_entry.setText(self.load_setting("geckodriver_path", ""))
        layout.addWidget(self.geckodriver_path_entry)
        
        '''# Weather API Key
        layout.addWidget(QLabel("Weather API Key"))
        self.weather_api_key_entry = QLineEdit()
        self.weather_api_key_entry.setText(self.load_setting("weather_api_key", ""))
        layout.addWidget(self.weather_api_key_entry)'''

        #Macro key text box
        layout.addWidget(QLabel("Macro Key (e.g., F24, F12, Ctrl+Shift+M)"))
        self.macro_key_entry = QLineEdit()
        self.macro_key_entry.setText(self.load_setting("macro_key", "F24"))  # Default to F24 if no setting is saved
        layout.addWidget(self.macro_key_entry)
        
        # Add a checkbox for the Macro Key Hold option in the settings window
        self.macro_key_hold_toggle = QCheckBox("Hold Macro Key to Listen")
        self.macro_key_hold_toggle.setChecked(self.load_setting("macro_key_hold", False))  # Default to False if no setting is saved
        layout.addWidget(self.macro_key_hold_toggle)
        
        # Add a section for Reset Macro Key in the settings window
        layout.addWidget(QLabel("Reset Macro Key (e.g., Ctrl+Alt+R)"))
        self.reset_macro_key_entry = QLineEdit()
        # Load the current setting for the reset macro key, with a suitable default if none is set
        self.reset_macro_key_entry.setText(self.load_setting("reset_macro_key", "Ctrl+Alt+R"))
        layout.addWidget(self.reset_macro_key_entry)


        # Save Button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.settings_window.setLayout(layout)
        self.settings_window.exec()  # Use exec() to make the dialog modal

        
        
        


    def save_settings(self):
        # Save the settings to a file
        try:
            settings = {
                "spotify_client_id": self.spotify_client_id_entry.text(),
                "spotify_client_secret": self.spotify_client_secret_entry.text(),
                "spotify_redirect_uri": self.spotify_redirect_uri_entry.text(),
                "asana_token": self.asana_token_entry.text(),
                "firefox_path": self.firefox_browser_exe_entry.text(),
                "weather_api_key": self.weather_api_key_entry.text(),
                "geckodriver_path": self.geckodriver_path_entry.text(),
                "macro_key": self.macro_key_entry.text(),
                "macro_key_hold": self.macro_key_hold_toggle.isChecked(),
                "reset_macro_key": self.reset_macro_key_entry.text()
                
                # Add more settings as needed...
            }
            with open("settings.json", "w") as file:
                json.dump(settings, file)
            # Reload settings in the application
            self.load_settings()
            QMessageBox.information(self, "Success", "Settings saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")


    def load_settings(self):
        # Load the settings from a file
        try:
            with open("settings.json", "r") as file:
                settings = json.load(file)
                # Update application logic with these settings
                # For example, reinitialize SpotifyController and Asana Client with new settings
        except FileNotFoundError:
            # Handle case where settings file doesn't exist
            pass
        self.initialize_reset_macro()  # Ensure this is called after settings are loaded
        

    def load_setting(self, key, default_value):
        # Utility method to load individual setting
        try:
            with open("settings.json", "r") as file:
                settings = json.load(file)
                return settings.get(key, default_value)
        except FileNotFoundError:
            return default_value
        self.initialize_reset_macro()  # Ensure this is called after settings are loaded


    #original_volume_level = volume.GetMasterVolumeLevelScalar()  # Get the current volume level
    #audio ducking
    def start_audio_ducking(self):
        if not self.audio_ducking_enabled:
            self.ducking_stop_event.clear()
            reduce_volume_level = self.original_volume_level / 2  # Use the class attribute
            threshold_db = 15  # This is the level of the microphone at which ducking should start
            self.ducking_thread = threading.Thread(target=monitor_and_adjust_volume,
                                                   args=(self.volume, threshold_db, reduce_volume_level, self.ducking_stop_event))
            self.ducking_thread.start()
            self.audio_ducking_enabled = True
    
    def stop_audio_ducking(self):
        if self.audio_ducking_enabled:
            self.ducking_stop_event.set()
            if self.ducking_thread.is_alive():
                self.ducking_thread.join()
            self.audio_ducking_enabled = False
    
    def toggle_audio_ducking(self):
        # If audio ducking is already enabled, disable it.
        if self.audio_ducking_enabled:
            self.stop_audio_ducking()
        # Otherwise, enable audio ducking.
        else:
            self.start_audio_ducking()
            self.audio_ducking_enabled = True

            
def initialize_asana_client(self):
    asana_token = self.load_setting("asana_token", "")
    if asana_token:
        self.client = asana.Client.access_token(asana_token)
    else:
        # Handle case where Asana token is not set
        pass
    

    
