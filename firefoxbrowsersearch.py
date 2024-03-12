import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service as FirefoxService

class FirefoxBrowserSearch:
    def __init__(self, settings_path):
        self.settings_path = settings_path
        self.driver = None
        self.ensure_settings_file()
        self.load_settings()
        
    def ensure_settings_file(self):
        # Check if the file exists
        try:
            open(self.settings_path, 'r').close()
        except FileNotFoundError:
            # If the file does not exist, create it with default settings
            default_settings = {
                'firefox_executable_path': '',  # Example default path or leave empty
                'geckodriver_path': '',  # Example default path or leave empty
            }
            with open(self.settings_path, 'w') as settings_file:
                json.dump(default_settings, settings_file, indent=4)
            print(f"Created default settings.json at {self.settings_path}")
            
    def load_settings(self):
        with open(self.settings_path, 'r') as settings_file:
            settings = json.load(settings_file)
        self.firefox_executable_path = settings.get('firefox_executable_path', None)
        self.geckodriver_path = settings.get('geckodriver_path', None)  # Make sure this line is added

    
    def start_browser(self):
        firefox_options = webdriver.FirefoxOptions()
        if self.firefox_executable_path:
            firefox_options.binary_location = self.firefox_executable_path

        # Now self.geckodriver_path is correctly defined
        geckodriver_service = FirefoxService(executable_path=self.geckodriver_path)
        self.driver = webdriver.Firefox(service=geckodriver_service, options=firefox_options)
        print("Firefox WebDriver started successfully.")

    def search(self, query, engine='google'):
        # Start the browser only if it's not already started
        if self.driver is None:
            self.start_browser()

        search_url = "https://www.bing.com" if engine.lower() == 'bing' else "https://www.google.com"
        self.driver.get(search_url)

        try:
            wait = WebDriverWait(self.driver, 10)
            search_box = wait.until(EC.element_to_be_clickable((By.NAME, "q")))
            search_box.clear()
            search_box.send_keys(query)
            search_box.submit()
            print(f"Search for '{query}' on {engine} completed.")
        except Exception as e:
            print(f"Error during search: {e}")

    def close_browser(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
