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
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QProgressBar, QCheckBox, QStyleFactory, QLineEdit, QDialog, QInputDialog, QMessageBox, QTabWidget, QTextEdit, QComboBox
from PyQt6.QtGui import QPalette, QColor, QAction
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from firefoxbrowsersearch import FirefoxBrowserSearch
import sys
from weather_api import WeatherAPI
from Weather_dashboard import WeatherDashboard
import pyautogui
from datetime import datetime
import psutil
from system_monitor import SystemMonitor
import pyqtgraph as pg
from transformers import pipeline
import torch
from openai import OpenAI
import requests
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Start system monitoring thread with default 5-second interval
        self.system_monitor = SystemMonitor(interval=5000)  # 5 seconds in milliseconds
        self.system_monitor.stats_updated.connect(self.update_system_stats)
        self.system_monitor.start()
        
        # Connect the signal to the slot
        self.confirmationSignal.connect(self.confirm_start_program)
        self.updateLabelSignal.connect(self.update_label)  # Add this line
        
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

        self.executables = DesktopAssistant.load_executables()  # Use class name for static method
        self.desktop_shortcuts = self.find_shortcuts(os.path.join(os.environ['USERPROFILE'], 'Desktop'))
        self.create_widgets()
        self.nlp_choice = self.load_setting("nlp_choice", "Transformers")  # Default to Transformers
        self.spacy_nlp = spacy.load("en_core_web_sm") if self.nlp_choice == "Spacy" else None
        self.transformers_nlp = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=0 if torch.cuda.is_available() else -1) if self.nlp_choice == "Transformers" else None
        self.mic = sr.Microphone(device_index=1)
        self.initialize_key_listener()
        spotify_client_id = self.load_setting("spotify_client_id", "")
        spotify_client_secret = self.load_setting("spotify_client_secret", "")
        spotify_redirect_uri = self.load_setting("spotify_redirect_uri", "")
        if spotify_client_id and spotify_client_secret and spotify_redirect_uri:
            self.spotify_controller = SpotifyController(spotify_client_id, spotify_client_secret, spotify_redirect_uri)
            print("Spotify controller initialized successfully. Testing authentication...")
            try:
                # Test authentication by getting user info or current playback
                if self.spotify_controller:
                    user = self.spotify_controller.sp.current_user()
                    print(f"Authenticated as: {user['display_name']}")
                    current = self.spotify_controller.sp.current_playback()
                    print(f"Current playback: {current}")
            except Exception as e:
                print(f"Spotify authentication error: {e}")
        else:
            self.spotify_controller = None
            print("Spotify settings not configured. Spotify commands will not work.")
        self.create_settings_menu()
        
        # Initialize the browser settings for Firefox
        self.firefox_service = FirefoxService(executable_path=self.load_setting("geckodriver_path", "path_to_geckodriver"))
        self.firefox_options = webdriver.FirefoxOptions()
        self.firefox_options.binary_location = self.load_setting("firefox_path", "path_to_firefox")

        # Now create a method to start Firefox with these settings
        # Initialize FirefoxBrowserSearch but do not start the browser
        self.firefox_search = FirefoxBrowserSearch("settings.json")

        # Weather
        self.weather_api = WeatherAPI()
        
        # Initialize plot data
        self.cpu_data = []
        self.ram_data = []
        self.disk_data = []
        self.time_data = []

        # Initialize AI clients
        self.ai_choice = self.load_setting("ai_choice", "ChatGPT")
        self.openai_client = OpenAI(api_key=self.load_setting("openai_api_key", "")) if self.load_setting("openai_api_key", "") else None
        self.xai_api_key = self.load_setting("xai_api_key", "")

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

    def create_widgets(self):
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        self.layout.addWidget(self.tabs)

        # Home Tab
        self.home_tab = QWidget()
        self.home_layout = QVBoxLayout(self.home_tab)
        self.tabs.addTab(self.home_tab, "Home")

        self.label = QLabel("Welcome to your Desktop Assistant!", self.home_tab)
        self.home_layout.addWidget(self.label)

        self.listen_button = QPushButton("Listen", self.home_tab)
        self.listen_button.clicked.connect(self.on_listen)
        self.home_layout.addWidget(self.listen_button)

        self.reset_button = QPushButton("Reset Application", self.home_tab)
        self.reset_button.clicked.connect(self.reset_application)
        self.home_layout.addWidget(self.reset_button)

        self.scan_button = QPushButton("Scan for Programs", self.home_tab)
        self.scan_button.clicked.connect(self.on_scan)
        self.home_layout.addWidget(self.scan_button)

        self.mic_button = QPushButton("Show Microphones", self.home_tab)
        self.mic_button.clicked.connect(self.show_mics)
        self.home_layout.addWidget(self.mic_button)

        self.shortcuts_button = QPushButton("Show Shortcuts", self.home_tab)
        self.shortcuts_button.clicked.connect(self.show_shortcuts)
        self.home_layout.addWidget(self.shortcuts_button)

        self.add_path_button = QPushButton("Add Path...", self.home_tab)
        self.add_path_button.clicked.connect(self.prompt_path_entry)
        self.home_layout.addWidget(self.add_path_button)

        self.weather_button = QPushButton("🌦️ Weather", self.home_tab)
        self.weather_button.clicked.connect(self.open_weather_dashboard)
        self.home_layout.addWidget(self.weather_button)

        self.progress = QProgressBar(self.home_tab)
        self.progress.setMaximum(100)
        self.home_layout.addWidget(self.progress)

        self.progress_label = QLabel("0%", self.home_tab)
        self.home_layout.addWidget(self.progress_label)

        self.ducking_checkbox = QCheckBox("Toggle Audio Ducking", self.home_tab)
        self.ducking_checkbox.stateChanged.connect(self.toggle_audio_ducking)
        self.home_layout.addWidget(self.ducking_checkbox)

        # Weather Tab (placeholder, unchanged for now)
        self.weather_tab = QWidget()
        self.weather_tab_layout = QVBoxLayout(self.weather_tab)
        self.tabs.addTab(self.weather_tab, "Weather")

        # System Tab (with charts)
        self.system_tab = QWidget()
        self.system_tab_layout = QVBoxLayout(self.system_tab)
        self.tabs.addTab(self.system_tab, "System")

        self.system_toggle = QCheckBox("Enable System Monitoring", self.system_tab)
        self.system_toggle.stateChanged.connect(self.toggle_system_monitoring)
        self.system_tab_layout.addWidget(self.system_toggle)

        # CPU Chart
        self.cpu_plot = pg.PlotWidget(self.system_tab)
        self.cpu_plot.setLabel('left', 'CPU Usage (%)')
        self.cpu_plot.setLabel('bottom', 'Time')
        self.cpu_curve = self.cpu_plot.plot(pen='b')
        self.system_tab_layout.addWidget(self.cpu_plot)

        # RAM Chart
        self.ram_plot = pg.PlotWidget(self.system_tab)
        self.ram_plot.setLabel('left', 'RAM Usage (%)')
        self.ram_plot.setLabel('bottom', 'Time')
        self.ram_curve = self.ram_plot.plot(pen='m')
        self.system_tab_layout.addWidget(self.ram_plot)

        # Disk Chart
        self.disk_plot = pg.PlotWidget(self.system_tab)
        self.disk_plot.setLabel('left', 'Disk Usage (%)')
        self.disk_plot.setLabel('bottom', 'Time')
        self.disk_curve = self.disk_plot.plot(pen='g')
        self.system_tab_layout.addWidget(self.disk_plot)
        
        # Chat Tab
        self.chat_tab = QWidget()
        self.chat_tab_layout = QVBoxLayout(self.chat_tab)
        self.chat_display = QTextEdit(self.chat_tab)
        self.chat_display.setReadOnly(True)
        self.chat_tab_layout.addWidget(self.chat_display)
        self.tabs.addTab(self.chat_tab, "Chat")

        # Tools Tab (new content for Feature 11)
        self.tools_tab = QWidget()
        self.tools_tab_layout = QVBoxLayout(self.tools_tab)
        self.tabs.addTab(self.tools_tab, "Tools")

        self.screenshot_button = QPushButton("📸 Take Screenshot", self.tools_tab)
        self.screenshot_button.clicked.connect(self.take_screenshot)
        self.tools_tab_layout.addWidget(self.screenshot_button)

        self.tools_label = QLabel("Tools output will appear here.", self.tools_tab)
        self.tools_tab_layout.addWidget(self.tools_label)

        self.setLayout(self.layout)
        
    def toggle_system_monitoring(self, state):
        """Toggle system monitoring on/off and update interval from settings."""
        enabled = state == Qt.CheckState.Checked.value
        self.system_monitor.set_enabled(enabled)
        if not enabled:
            self.cpu_curve.setData([])
            self.ram_curve.setData([])
            self.disk_curve.setData([])
            self.cpu_data.clear()
            self.ram_data.clear()
            self.disk_data.clear()
            self.time_data.clear()

    def update_system_stats(self, cpu_percent, ram_percent, ram_used, ram_total, disk_percent):
        """Update system monitoring stats and charts from thread."""
        if self.system_monitor.enabled:
            current_time = len(self.time_data)
            self.cpu_data.append(cpu_percent)
            self.ram_data.append(ram_percent)
            self.disk_data.append(disk_percent)
            self.time_data.append(current_time)

            # Limit data points for performance
            if len(self.cpu_data) > 100:  # Match SystemMonitor.max_points
                self.cpu_data.pop(0)
                self.ram_data.pop(0)
                self.disk_data.pop(0)
                self.time_data.pop(0)

            self.cpu_curve.setData(self.time_data, self.cpu_data)
            self.ram_curve.setData(self.time_data, self.ram_data)
            self.disk_curve.setData(self.time_data, self.disk_data)
        
    def take_screenshot(self):
        """Capture a screenshot and save it to a directory."""
        save_dir = self.load_setting("screenshot_dir", os.path.join(os.environ['USERPROFILE'], 'Pictures', 'Screenshots'))
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        msg = f"Screenshot saved to {filepath}"
        self.tools_label.setText(msg)  # Update Tools tab label
        self.speak(msg)
        return msg  # For voice command response

    def update_label(self, text):
        if self.label is not None:
            self.label.setText(text)  # Update the label's text
            
    def confirm_start_program(self, best_match):
        reply = QMessageBox.question(self, "Confirm", f"Did you mean '{best_match}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # If the user confirms, start the program
            self.start_program(best_match)
        else:
            self.updateLabelSignal.emit("Operation cancelled by user.")

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
        exclusions = ["update", "uninstall"]  # Exclude any .exe containing these words
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

        # Clear existing hotkeys to avoid conflicts if needed (commented out below)
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
        DesktopAssistant.save_executables(self.executables)  # Use class name for static method
        self.label.setText(f"Added {exec_name} to the list")

    def on_listen(self):
        threading.Thread(target=self.listen_and_respond).start()

    def listen_and_respond(self):
        pythoncom.CoInitialize()
        try:
            command = self.listen_command()
            if command:
                response = self.process_command(command)  # Use NLP for processing
                if isinstance(response, tuple) and len(response) == 2:
                    display_message, spoken_message = response
                else:
                    display_message, spoken_message = response, response
                self.speak(spoken_message)
                self.updateLabelSignal.emit(display_message)
        finally:
            pythoncom.CoUninitialize()

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
            print(f"You said: {command}")
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

    def confirm_start_program(self, best_match):
        reply = QMessageBox.question(self, "Confirm", f"Did you mean '{best_match}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # If the user confirms, start the program
            self.start_program(best_match)
        else:
            self.updateLabelSignal.emit("Operation cancelled by user.")

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
        if not command.strip():
            return "No command provided.", "No command provided."

        # Use selected NLP for intent classification
        if self.nlp_choice == "Spacy" and self.spacy_nlp:
            doc = self.spacy_nlp(command)
            # Simple Spacy-based intent detection (rule-based)
            intent = "unknown"
            if any(token.text.lower() in ["weather", "forecast", "alerts"] for token in doc):
                intent = "weather"
            elif any(token.text.lower() in ["start", "launch", "open"] for token in doc):
                intent = "start_program"
            elif any(token.text.lower() in ["play", "music", "song", "artist", "album"] for token in doc):
                intent = "play_music"
            elif any(token.text.lower() in ["check", "system", "status"] for token in doc):
                intent = "check_system"
            elif any(token.text.lower() in ["screenshot", "capture", "screen"] for token in doc):
                intent = "take_screenshot"
        elif self.nlp_choice == "Transformers" and self.transformers_nlp:
            logger.info(f"Using Transformers for command: {command}")
            candidate_labels = [
                "weather", "start_program", "play_music", "check_system", "take_screenshot",
                "unknown"
            ]
            try:
                result = self.transformers_nlp(command, candidate_labels, multi_label=False)
                intent = result['labels'][0]  # Most likely intent
                logger.info(f"Transformers result: {result}")
            except Exception as e:
                logger.error(f"Transformers error: {e}")
                intent = "unknown"
        else:
            return "NLP not configured. Check settings.", "NLP not configured."

        if intent == "weather":
            detailed_weather = any(keyword in command.lower() for keyword in ["detailed weather", "detailed"])
            forecast = "forecast" in command.lower()
            alerts = "alerts" in command.lower()
            location = re.sub(r"\b(detailed|forecast|alerts|weather)\b", "", command.lower(), flags=re.IGNORECASE).strip()
            # Handle contractions and preserve "weather"
            if "what's" in location or "what is" in location:
                location = re.sub(r"what'?s\s*|what is\s*", "", location).strip()
            if not location or location in ["", "the"]:
                location = "auto"
            logger.info(f"Parsed weather location: {location}, detailed: {detailed_weather}, forecast: {forecast}, alerts: {alerts}")
            try:
                display_msg, spoken_msg = self.weather_api.get_weather(location, spoken_request=command, detailed=detailed_weather)
                if forecast or alerts:
                    lat, lon, loc = self.weather_api.get_coordinates(location) if location != "auto" else self.weather_api.get_current_location()
                    if lat and lon:
                        if forecast:
                            full_display, _ = self.weather_api.get_weather(location)
                            forecast_lines = full_display.split("\n**5-Day Forecast:**\n")[-1].strip().split("\n")
                            forecast_data = []
                            for line in forecast_lines:
                                if line.strip():
                                    match = re.match(r"(\d{4}-\d{2}-\d{2}): High (\d+\.\d+)°F, Low (\d+\.\d+)°F, Precip (\d+\.\d+) mm, Wind (\d+\.\d+) mph (\w+)", line.strip())
                                    if match:
                                        date, high_f, low_f, precip_mm, wind_mph, wind_dir = match.groups()
                                        try:
                                            forecast_data.append({
                                                "date": date,
                                                "high_f": float(high_f),
                                                "low_f": float(low_f),
                                                "precip_mm": float(precip_mm),
                                                "wind_mph": float(wind_mph),
                                                "wind_dir": wind_dir
                                            })
                                        except ValueError as e:
                                            logger.error(f"Error converting forecast values: {e}")
                                            continue
                            if forecast_data:
                                display_msg += "\n**5-Day Forecast:**\n" + "\n".join([
                                    f"{day['date']}: High {day['high_f']}°F, Low {day['low_f']}°F, Precip {day['precip_mm']} mm, Wind {day['wind_mph']} mph {day['wind_dir']}"
                                    for day in forecast_data
                                ])
                                spoken_msg += " Here’s the 5-day forecast: " + ", ".join([
                                    f"On {day['date']}, high {day['high_f']} degrees, low {day['low_f']} degrees"
                                    for day in forecast_data[:2]
                                ])
                        if alerts:
                            alerts_data = self.weather_api.get_weather_alerts(lat, lon)
                            if alerts_data:
                                alert_text = "🔔 **Weather Alerts:**\n" + "\n".join([f"- {a['event']} ({a['severity']}): {a['description']} (Expires: {a['expires']})" for a in alerts_data])
                                display_msg += "\n" + alert_text
                                spoken_msg += " Weather alerts: " + ", ".join([f"{a['event']} until {a['expires']}" for a in alerts_data[:2]])
                return display_msg, spoken_msg
            except Exception as e:
                logger.error(f"Error fetching weather: {e}")
                return f"Error fetching weather: {e}", f"Error fetching weather."

        elif intent == "start_program":
            match = re.search(r"start\s+(.+)", command)
            if match:
                program_name = match.group(1).strip()
                return self.start_program_with_confirmation(program_name)
            return "Program not specified.", "Program not specified."

        elif intent == "play_music":
            match = re.search(r"play\s+(?:a\s+)?(?:song|artist|album|artist radio)\s+(.+)", command, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if self.spotify_controller:
                    play_result = self.spotify_controller.play_song(name)  # Default to song for simplicity
                    logger.info(f"Attempting to play: {name}, Result: {play_result}")
                    if isinstance(play_result, str):  # If the return value is a string (error message or confirmation)
                        return play_result, play_result
                    else:
                        return f"Playing {name} on Spotify", f"Playing {name} on Spotify"
                else:
                    return "Spotify not configured. Check settings.", "Spotify not configured."
            return "Music command unclear.", "Music command unclear."

        elif intent == "check_system":
            if not self.system_monitor.enabled:
                msg = "System monitoring is disabled. Enable it in the System tab."
                self.label.setText(msg)
                return msg, msg
            cpu_percent = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            msg = (
                f"CPU usage is {cpu_percent:.1f}%. "
                f"RAM usage is {ram.percent:.1f}%, {ram.used / 1024**3:.1f} out of {ram.total / 1024**3:.1f} GB. "
                f"Disk usage is {disk.percent:.1f}%, {disk.used / 1024**3:.1f} out of {disk.total / 1024**3:.1f} GB."
            )
            self.label.setText(msg)
            return msg, msg

        elif intent == "take_screenshot":
            msg = self.take_screenshot()
            return msg, "Screenshot captured."

        else:
            return "I'm not sure how to respond to that.", "I'm not sure how to respond."

    def ask_chatgpt(self, query):
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": query}]
            )
            return response.choices[0].message.content, response.choices[0].message.content
        except Exception as e:
            logger.error(f"ChatGPT error: {e}")
            return f"ChatGPT error: {e}", f"ChatGPT error."

    def ask_grok(self, query):
        # Mock until xAI API is stable; replace with real API later
        if not self.xai_api_key:
            return f"Grok API key not set. Mock response: Imagine I’m Grok, giving you a witty answer to {query}", f"Mock Grok response: {query}"
        try:
            # Hypothetical xAI API call (based on beta info)
            response = requests.post(
                "https://api.xai.com/grok3",  # Placeholder URL
                json={"query": query, "mode": "standard"},
                headers={"Authorization": f"Bearer {self.xai_api_key}"}
            )
            return response.json().get("response", "Grok failed to respond."), response.json().get("response", "Grok failed to respond.")
        except Exception as e:
            logger.error(f"Grok error: {e}")
            return f"Grok error: {e}", f"Grok error."

    def start_program(self, program_name):
        # Check if the program_name exists in the list of executables
        if program_name in self.executables:
            try:
                # Start the program
                subprocess.Popen(self.executables[program_name], shell=True)
                return f"Started {program_name.capitalize()}."
            except Exception as e:
                logger.error(f"Error starting {program_name.capitalize()}: {e}")
                return f"Error starting {program_name.capitalize()}: {e}"
        else:
            return f"{program_name.capitalize()} not found in the list of executables."

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
            logger.error(f"Failed to start Firefox WebDriver: {e}")
            print(f"Failed to start Firefox WebDriver: {e}")

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
        DesktopAssistant.save_executables(self.executables)  # Use class name for static method
        print("Saved executables to executables.json.")
        
        # Reset the progress bar and update the label to indicate completion
        self.update_progress_bar(100)
        QTimer.singleShot(0, lambda: self.label.setText("Scan complete!"))
        
        pythoncom.CoUninitialize()

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
        
        # Macro key text box
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

        # NLP Choice Dropdown
        layout.addWidget(QLabel("Preferred NLP"))
        self.nlp_choice_dropdown = QComboBox()
        self.nlp_choice_dropdown.addItems(["Spacy", "Transformers"])
        self.nlp_choice_dropdown.setCurrentText(self.load_setting("nlp_choice", "Transformers"))
        layout.addWidget(self.nlp_choice_dropdown)

        # AI Selection Dropdown
        layout.addWidget(QLabel("Preferred AI"))
        self.ai_choice = QComboBox()
        self.ai_choice.addItems(["ChatGPT", "Grok", "Compare Both"])
        self.ai_choice.setCurrentText(self.load_setting("ai_choice", "ChatGPT"))
        layout.addWidget(self.ai_choice)

        # OpenAI API Key
        layout.addWidget(QLabel("OpenAI API Key"))
        self.openai_key_entry = QLineEdit()
        self.openai_key_entry.setText(self.load_setting("openai_api_key", ""))
        layout.addWidget(self.openai_key_entry)

        # xAI API Key (Grok)
        layout.addWidget(QLabel("xAI API Key (Grok)"))
        self.xai_key_entry = QLineEdit()
        self.xai_key_entry.setText(self.load_setting("xai_api_key", ""))
        layout.addWidget(self.xai_key_entry)

        # Screenshot Directory Setting
        layout.addWidget(QLabel("Screenshot Save Directory"))
        self.screenshot_dir_entry = QLineEdit()
        self.screenshot_dir_entry.setText(self.load_setting("screenshot_dir", os.path.join(os.environ['USERPROFILE'], 'Pictures', 'Screenshots')))
        layout.addWidget(self.screenshot_dir_entry)
        
        # System Monitoring Refresh Interval
        layout.addWidget(QLabel("System Monitoring Refresh Interval (seconds)"))
        self.refresh_interval = QComboBox()
        self.refresh_interval.addItems(["1", "5", "10", "30"])
        current_interval = self.load_setting("system_refresh_interval", 5)  # Default 5 seconds
        self.refresh_interval.setCurrentText(str(current_interval))
        layout.addWidget(self.refresh_interval)

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
                "geckodriver_path": self.geckodriver_path_entry.text(),
                "macro_key": self.macro_key_entry.text(),
                "macro_key_hold": self.macro_key_hold_toggle.isChecked(),
                "reset_macro_key": self.reset_macro_key_entry.text(),
                "nlp_choice": self.nlp_choice_dropdown.currentText(),
                "ai_choice": self.ai_choice.currentText(),
                "openai_api_key": self.openai_key_entry.text(),
                "xai_api_key": self.xai_key_entry.text(),
                "screenshot_dir": self.screenshot_dir_entry.text(),
                "system_refresh_interval": int(self.refresh_interval.currentText()) * 1000  # Convert to milliseconds
            }
            with open("settings.json", "w") as file:
                json.dump(settings, file, indent=4)
            # Reload settings in the application
            self.load_settings()
            self.system_monitor.set_interval(settings["system_refresh_interval"])
            # Reinitialize NLP based on new choice
            self.nlp_choice = settings["nlp_choice"]
            self.spacy_nlp = spacy.load("en_core_web_sm") if self.nlp_choice == "Spacy" else None
            self.transformers_nlp = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=0 if torch.cuda.is_available() else -1) if self.nlp_choice == "Transformers" else None
            QMessageBox.information(self, "Success", "Settings saved successfully.")
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid refresh interval: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")    

    def open_weather_dashboard(self):
        """Opens the Weather Dashboard window."""
        self.weather_dashboard = WeatherDashboard()
        self.weather_dashboard.show()
        
    def closeEvent(self, event):
        """Clean up threads on window close."""
        self.system_monitor.stop()
        super().closeEvent(event)

    def load_executables(filename='executables.json'):
        """Static method to load executables from a JSON file."""
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_executables(executables, filename='executables.json'):
        """Static method to save executables to a JSON file."""
        with open(filename, 'w') as file:  # 'w' mode will overwrite the file
            json.dump(executables, file, indent=4)  # Use indent for pretty-printing

    def load_setting(self, key, default_value):
        """Load a single setting from settings.json."""
        try:
            with open("settings.json", "r") as file:
                settings = json.load(file)
                return settings.get(key, default_value)
        except FileNotFoundError:
            return default_value

    def save_setting(self, key, value):
        """Save a single setting to settings.json."""
        settings = self.load_setting(key, {})
        settings[key] = value
        with open("settings.json", "w") as file:
            json.dump(settings, file, indent=4)

    def load_settings(self):
        """Load settings from settings.json, ensuring system_monitor exists."""
        try:
            with open("settings.json", "r") as file:
                settings = json.load(file)
                # Update application logic with these settings
                for key, value in settings.items():
                    if key == "system_refresh_interval" and hasattr(self, "system_monitor"):
                        try:
                            self.system_monitor.set_interval(int(value))
                        except (ValueError, TypeError):
                            self.system_monitor.set_interval(5000)  # Default to 5 seconds if invalid
                    elif key == "nlp_choice":
                        self.nlp_choice = value
                        self.spacy_nlp = spacy.load("en_core_web_sm") if value == "Spacy" else None
                        self.transformers_nlp = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=0 if torch.cuda.is_available() else -1) if value == "Transformers" else None
                    elif key == "ai_choice":
                        self.ai_choice = value
                    # ... (other settings logic as needed)
        except FileNotFoundError:
            pass
        # Ensure reset macro key is initialized
        self.initialize_reset_macro()

    def start_program(self, program_name):
        # Check if the program_name exists in the list of executables
        if program_name in self.executables:
            try:
                # Start the program
                subprocess.Popen(self.executables[program_name], shell=True)
                return f"Started {program_name.capitalize()}."
            except Exception as e:
                logger.error(f"Error starting {program_name.capitalize()}: {e}")
                return f"Error starting {program_name.capitalize()}: {e}"
        else:
            return f"{program_name.capitalize()} not found in the list of executables."

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

    def start_essential_apps(self):
        essential_apps = ["discord", "signal", "opera gx browser", "lorexcloud"]
        status_messages = []

        for app in essential_apps:
            if app.lower() in self.executables:
                try:
                    subprocess.Popen(self.executables[app.lower()], shell=True)
                    status_messages.append(f"Started {app.capitalize()}.")
                except Exception as e:
                    logger.error(f"Error starting {app.capitalize()}: {e}")
                    status_messages.append(f"Error starting {app.capitalize()}: {e}")
            else:
                status_messages.append(f"{app.capitalize()} not found in the list of executables.")
    
        return "\n".join(status_messages)

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
            logger.error(f"Failed to start Firefox WebDriver: {e}")
            print(f"Failed to start Firefox WebDriver: {e}")

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
        DesktopAssistant.save_executables(self.executables)  # Use class name for static method
        print("Saved executables to executables.json.")
        
        # Reset the progress bar and update the label to indicate completion
        self.update_progress_bar(100)
        QTimer.singleShot(0, lambda: self.label.setText("Scan complete!"))
        
        pythoncom.CoUninitialize()

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
    
    def get_shortcut_target(self, shortcut_path):
        shell = win32com.client.Dispatch("WScript.Shell")
        try:
            shortcut = shell.CreateShortcut(shortcut_path)
            return shortcut.Targetpath
        except Exception as e:
            logger.error(f"Error reading shortcut: {e}")
            print(f"Error reading shortcut: {e}")
            return None

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Desktop Assistant")
    window.setGeometry(100, 100, 800, 600)
    desktop_assistant = DesktopAssistant(window)
    layout = QVBoxLayout()
    central_widget = QWidget()
    central_widget.setLayout(layout)
    window.setCentralWidget(central_widget)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()