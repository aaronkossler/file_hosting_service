import os
import time
import json
import socket
import difflib
import base64
import maskpass
import threading
from watchdog.observers import Observer
from components.abstract_message_listener import MessageListener
from components.event_handler import EventHandler
from components.server_message_notifier import ServerMessageNotifier

import sys
sys.path.append('../')
from resources.message_sending import send_message

# Import server configuration
# Load configuration from the JSON file
with open('client_config.json', 'r') as config_file:
    config = json.load(config_file)

# Use the loaded configuration
SERVER_HOST = config["server_host"]
SERVER_PORT = config["server_port"]
CLIENT_DIR = config["client_dir"]

# Class responsible for the Client instance
class Client(MessageListener):
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.message_handler = ServerMessageNotifier(self.client_socket)
        self.event_handler = EventHandler(self.client_socket, CLIENT_DIR)
        self.logged_in = False

    # Handle server messages
    def notify_server_message(self, message):
        if message["action"] == "shutdown":
            self.shutdown()
        elif message["action"] == "login":
            self.handle_login_message(message)

    # Connect to server
    def connect(self):
        try:
            self.client_socket.connect((SERVER_HOST, SERVER_PORT))
            print(f"Connected to {SERVER_HOST}:{SERVER_PORT}")  
        except ConnectionError as e:
            print(f"Error connecting to server: {e}")
            sys.exit(0)

    # Login logic
    def login(self):
        while not self.logged_in:
            username = input("Enter username: ")
            password = maskpass.askpass(prompt="Password: ", mask="*")

            message = {
                "action": "login",
                "username": username,
                "password": password
            }
            send_message(self.client_socket, message)

            # Wait for Server to answer for 10 seconds
            timeout = 10
            timeout_start = time.time()
            while time.time() < timeout_start + timeout and not self.logged_in:
                time.sleep(1)

            if not self.logged_in:
                print("Server is not responding. Please try again.")

    def handle_login_message(self, message):
        print(message["text"])
        if message["result"] == "successful":
            self.logged_in = True

    # Start observing to events
    def start(self):
        observer = Observer()
        observer.schedule(self.event_handler, path=CLIENT_DIR, recursive=True)
        observer.start()

        # start listening for messages
        self.message_handler.add_listener(self)
        self.message_handler.start_listening(observer)

        observer.join()

    # Run client
    def run(self):
        # Connect to the server
        self.connect()

        # Start listening to events and server messages in a separate thread
        listen_thread = threading.Thread(target=self.start)
        listen_thread.start()

        # Login
        self.login()

        listen_thread.join()

    # Close client on server disconnect
    def shutdown(self):
        print("Server is shutting down. Closing client...")
        self.message_handler.stop_listening()
        self.client_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    # Create and start Client instance
    client = Client()
    client.run()
