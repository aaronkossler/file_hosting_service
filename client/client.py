import os
import time
import json
import socket
import difflib
import base64
import maskpass
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
sys.path.append('../')
from resources.message_sending import send_message, receive_message

# Import server configuration
# Load configuration from the JSON file
with open('client_config.json', 'r') as config_file:
    config = json.load(config_file)

# Use the loaded configuration
SERVER_HOST = config["server_host"]
SERVER_PORT = config["server_port"]
CLIENT_DIR = config["client_dir"]

# Keep track of recently created/modified files to catch the successive modified event thrown by watchdog
recently_changed_files = []

# Class responsible for detecting events and sending sync messages to server
class EventHandler(FileSystemEventHandler):
    # Set socket in constructor
    def __init__(self, client_socket):
        self.client_socket = client_socket
        super().__init__()

        # Create a MessageHandler instance to receive messages from the server
        self.message_handler = ServerMessageHandler(self.client_socket)

    # MODIFIED logic
    def on_modified(self, event):
        if event.is_directory:
            return

        if event.src_path in recently_changed_files:
            recently_changed_files.remove(event.src_path)
            return

        relative_path = os.path.relpath(event.src_path, CLIENT_DIR)
        modified_content = self.read_bytes(event.src_path)
        data_base64 = base64.b64encode(modified_content).decode('utf-8')

        message = {
            "action": "update",
            "path": relative_path,
            "event_type": "modified",
            "data": data_base64
        }
        recently_changed_files.append(event.src_path)
        send_message(self.client_socket, message)

    # DELETE logic
    def on_deleted(self, event):
        relative_path = os.path.relpath(event.src_path, CLIENT_DIR)

        message = {
            "action": "update",
            "path": relative_path,
            "event_type": "deleted"
        }

        if event.is_directory:
            message["structure"] = "dir"
        else:
            message["structure"] = "file"

        send_message(self.client_socket, message)

    # CREATED logic
    def on_created(self, event):
        relative_path = os.path.relpath(event.src_path, CLIENT_DIR)

        message = {
            "action": "update",
            "path": relative_path,
            "event_type": "created"
        }

        if event.is_directory:
            message["structure"] = "dir"
        else:
            data_bytes = self.read_bytes(event.src_path)
            data_base64 = base64.b64encode(data_bytes).decode('utf-8')

            message["structure"] = "file"
            message["data"] = data_base64

            recently_changed_files.append(event.src_path)

        send_message(self.client_socket, message)

    # MOVED logic
    def on_moved(self, event):
        src_relative_path = os.path.relpath(event.src_path, CLIENT_DIR)
        dest_relative_path = os.path.relpath(event.dest_path, CLIENT_DIR)

        message = {
            "action": "update",
            "src_path": src_relative_path,
            "dest_path": dest_relative_path,
            "event_type": "moved"
        }

        if event.is_directory:
            message["structure"] = "dir"
        else:
            message["structure"] = "file"

        send_message(self.client_socket, message)

    # CLOSED logic
    def on_closed(self, event):
        self.on_modified(event)

    # Helper function to read files
    def read_bytes(self, file_path):
        with open(file_path, 'rb') as file:
            return file.read()

    def listen_to_server_messages(self):
        # Listen for server messages using the MessageHandler
        message = self.message_handler.listen_to_server_messages()
        return message

    # Class responsible for the Login
    def on_login(self):
        while True:
            username = input("Enter username: ")
            password = maskpass.askpass(prompt="Password: ", mask="*")

            message = {
                "action": "login",
                "username": username,
                "password": password
            }
            send_message(client_socket, message)

            # Wait for Server to answer for 10 seconds
            timeout = 10
            timeout_start = time.time()
            server_message = None
            while time.time() < timeout_start + timeout:
                # Listening for server messages
                server_message = self.listen_to_server_messages()
                time.sleep(1)
                if server_message:
                    break

            if server_message:
                # Print error message or login successful
                print(server_message["text"])

                if server_message["result"] == "successful":
                    return True
            else:
                print("Server is not responding. Please try again.")


# Class responsible for handling server messages
class ServerMessageHandler:
    def __init__(self, client_socket):
        self.client_socket = client_socket

    # Listen and receive server messages
    def listen_to_server_messages(self):
        try:
            while True:
                data = receive_message(self.client_socket)
                if not data:
                    break

                message = json.loads(data)

                if message["action"] == "login":
                    return message

                self.handle_server_message(message)

        except json.JSONDecodeError:
            print("Error decoding JSON message")
        except ConnectionResetError:
            print("Server disconnected")

    # Define functions that are used to react to server messages
    def handle_server_message(self, message):
        if message["action"] == "shutdown":
            self.handle_server_shutdown()
        # Other types of server messages can be added here

    # Close client due to server shutdown
    def handle_server_shutdown(self):
        print("Server is shutting down. Closing client...")
        self.client_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    # Create socket and try to connect to the server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        print(f"Connected to {SERVER_HOST}:{SERVER_PORT}")  
    except ConnectionError as e:
        print(f"Error connecting to server: {e}")
        sys.exit(0)

    # Create EventHandler
    event_handler = EventHandler(client_socket)

    # Login
    login = None
    try:
        login = event_handler.on_login()
    except KeyboardInterrupt:
        pass

    if login:
        # Start listening to events
        observer = Observer()
        observer.schedule(event_handler, path=CLIENT_DIR, recursive=True)
        observer.start()

        try:
            while True:
                # Check for server messages periodically
                event_handler.listen_to_server_messages()
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
