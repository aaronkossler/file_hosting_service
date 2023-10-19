import os
import base64
from watchdog.events import FileSystemEventHandler

import sys
sys.path.append('../')
from resources.message_sending import send_message

# Class responsible for detecting events and sending sync messages to server
class EventHandler(FileSystemEventHandler):
    # Set socket in constructor
    def __init__(self, client_socket, client_dir):
        self.client_socket = client_socket
        self.CLIENT_DIR = client_dir
        # Keep track of recently created/modified files to catch the successive modified event thrown by watchdog
        self.recently_changed_files = []
        super().__init__()

    # MODIFIED logic
    def on_modified(self, event):
        if event.is_directory:
            return

        if event.src_path in self.recently_changed_files:
            self.recently_changed_files.remove(event.src_path)
            return

        relative_path = os.path.relpath(event.src_path, self.CLIENT_DIR)
        modified_content = self.read_bytes(event.src_path)
        data_base64 = base64.b64encode(modified_content).decode('utf-8')

        message = {
            "action": "update",
            "path": relative_path,
            "event_type": "modified",
            "data": data_base64
        }
        self.recently_changed_files.append(event.src_path)
        send_message(self.client_socket, message)

    # DELETE logic
    def on_deleted(self, event):
        relative_path = os.path.relpath(event.src_path, self.CLIENT_DIR)

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
        relative_path = os.path.relpath(event.src_path, self.CLIENT_DIR)

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

            self.recently_changed_files.append(event.src_path)

        send_message(self.client_socket, message)

    # MOVED logic
    def on_moved(self, event):
        src_relative_path = os.path.relpath(event.src_path, self.CLIENT_DIR)
        dest_relative_path = os.path.relpath(event.dest_path, self.CLIENT_DIR)

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
