import sys
import json
import threading

sys.path.append('../')
from resources.message_sending import receive_message

# Class responsible for handling server messages
class ServerMessageNotifier:
    def __init__(self, client_socket):
        self.client_socket = client_socket
        self._listeners = []
        self.sent_messages = {}
        self._stop_listening = threading.Event()

    def add_listener(self, listener):
        self._listeners.append(listener)

    def remove_listener(self, listener):
        self._listeners.remove(listener)

    def notify_listeners(self, server_message, server_address):
        for listener in self._listeners:
            listener.notify_server_message(server_message, server_address)

    def start_listening(self):
        try:
            while not self._stop_listening.is_set():
                messages, server_address = receive_message(self.client_socket)
                if not messages:
                    break
                try:     
                    for item in messages:
                        message = json.loads(item)
                        self.notify_listeners(message, server_address)
                except json.JSONDecodeError:
                    print("Error decoding JSON message")
        except (KeyboardInterrupt, ConnectionResetError):
            quit()

    def stop_listening(self):
        self._stop_listening.set()
