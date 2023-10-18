import os
import time
import json
import socket
import maskpass
import threading
import argparse
import signal
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

def parse_command_line_args():
    global SERVER_HOST, SERVER_PORT, CLIENT_DIR
    parser = argparse.ArgumentParser(description="Client replicating Dropbox functionality "
                                                 "by syncing files and folders in the background")
    
    # Add command-line arguments to overwrite configuration values
    parser.add_argument('--server-host', help='Server host address')
    parser.add_argument('--server-port', type=int, help='Server port number')
    parser.add_argument('--debug', action='store_true', help='Decide whether sent messages should be logged for debugging')
    parser.add_argument('--client-dir', help='Client directory path')

    args = parser.parse_args()

    if args.debug:
        os.environ["DEBUG"] = "on"
    else: 
        os.environ["DEBUG"] = "off"

    # Update the configuration based on the command-line arguments
    if args.server_host:
        SERVER_HOST = args.server_host
    if args.server_port:
        SERVER_PORT = args.server_port
    if args.client_dir and os.path.exists(args.client_dir):
        CLIENT_DIR = args.client_dir
    elif not os.path.exists(CLIENT_DIR):
        print("The client directory does not exist.")
        sys.exit(0)

# Class responsible for the Client instance
class Client(MessageListener):
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.message_handler = ServerMessageNotifier(self.client_socket)
        self.event_handler = EventHandler(self.client_socket, CLIENT_DIR)
        self.login_response = False
        self.logged_in = False
        self.disconnected = False

    # Handle server messages
    def notify_server_message(self, message):
        if message["action"] == "shutdown" and self.logged_in:
            self.shutdown("Server is disconnected. Closing client...")
        elif message["action"] == "login" or not self.logged_in:
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

            if not self.disconnected:
                send_message(self.client_socket, message)
            else:
                self.shutdown("Server is disconnected. Aborting login...")

            # Wait for Server to answer for 10 seconds
            timeout = 10
            timeout_start = time.time()
            while time.time() < timeout_start + timeout and not self.logged_in and not self.login_response:
                time.sleep(1)

            if not self.login_response and not self.logged_in:
                print("Server is not responding. Please try again.")
            elif not self.logged_in:
                self.login_response = False

    def handle_login_message(self, message):
        if message["action"] == "login":
            print(message["text"])
            self.login_response = True
            if message["result"] == "successful":
                self.logged_in = True
        elif message["action"] == "shutdown":
            self.disconnected = True

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

        try:
            # Start listening to events and server messages in a separate thread
            listen_thread = threading.Thread(target=self.start)
            listen_thread.daemon = True
            listen_thread.start()

            # Login
            self.login()

            listen_thread.join()
        except KeyboardInterrupt:
            self.shutdown("Closing client...")

    # Close client
    def shutdown(self, message):
        print(message)
        self.message_handler.stop_listening()
        self.client_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    # Parse cmd line args
    parse_command_line_args()
    # Create Client instance
    client = Client()
    # Start Client instance
    client.run()
