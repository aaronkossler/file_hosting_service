import os
import time
import json
import socket
import difflib
import base64
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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

class SyncHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return

        if event.src_path in recently_changed_files:
            recently_changed_files.remove(event.src_path)
            return

        """ # NOT WORKINGidea to use difflib to only save changes
        # however, a storage of the original data would need to be done beforehand
        relative_path = os.path.relpath(event.src_path, CLIENT_DIR)
        original_file_path = event.src_path + ".orig"
    
        # Calculate differences between the original and modified files
        with open(original_file_path, 'r', encoding='utf-8') as orig_file:
            orig_content = orig_file.readlines()

        with open(event.src_path, 'rb') as mod_file:
            mod_content = mod_file.readlines()

        d = difflib.Differ()
        diff = list(d.compare(orig_content, mod_content))
        diff_str = '\n'.join(diff)

        # Include the differences in the synchronization message
        message = {
            "action": "update",
            "path": relative_path,
            "event_type": "modified",
            "data": diff_str  # Include the differences
        }

        # Update the original file with the modified content
        with open(original_file_path, 'w', encoding='utf-8') as orig_file:
            orig_file.writelines(mod_content)

        send_message_to_server(message)"""

        # Current workaround to just completely overwrite the file when it is modified
        relative_path = os.path.relpath(event.src_path, CLIENT_DIR)

        # Read the content of the modified file
        modified_content = self.read_bytes(event.src_path)

        # Encode the modified content as Base64 and send it to the server
        data_base64 = base64.b64encode(modified_content).decode('utf-8')

        message = {
            "action": "update",
            "path": relative_path,
            "event_type": "modified",
            "data": data_base64
        }
        recently_changed_files.append(event.src_path)
        send_message_to_server(message)

    def on_deleted(self, event):
        if event.is_directory:
            return
        relative_path = os.path.relpath(event.src_path, CLIENT_DIR)
        message = {
            "action": "update",
            "path": relative_path,
            "event_type": "deleted"
        }
        send_message_to_server(message)

    def on_created(self, event):
        if event.is_directory:
            return
        relative_path = os.path.relpath(event.src_path, CLIENT_DIR)
        
        # Read the content of the created file as bytes
        data_bytes = self.read_bytes(event.src_path)
        
        # Encode the binary data as Base64
        data_base64 = base64.b64encode(data_bytes).decode('utf-8')
        
        message = {
            "action": "update",
            "path": relative_path,
            "event_type": "created",
            "data": data_base64
        }
        recently_changed_files.append(event.src_path)
        send_message_to_server(message)

    def on_moved(self, event):
        if event.is_directory:
            return
        src_relative_path = os.path.relpath(event.src_path, CLIENT_DIR)
        dest_relative_path = os.path.relpath(event.dest_path, CLIENT_DIR)
        message = {
            "action": "update",
            "src_path": src_relative_path,
            "dest_path": dest_relative_path,
            "event_type": "moved"
        }
        send_message_to_server(message)

    def read_bytes(self, file_path):
        with open(file_path, 'rb') as file:
            return file.read()

def send_message_to_server(message):
    print(message)
    # Create a socket connection to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            # Serialize the message to JSON
            message_json = json.dumps(message)
            # Send the message to the server
            client_socket.sendall(message_json.encode())
        except ConnectionError as e:
            print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    event_handler = SyncHandler()
    observer = Observer()
    observer.schedule(event_handler, path=CLIENT_DIR, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
