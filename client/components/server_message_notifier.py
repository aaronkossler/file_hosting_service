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
        self._stop_listening = threading.Event()

    def add_listener(self, listener):
        self._listeners.append(listener)

    def remove_listener(self, listener):
        self._listeners.remove(listener)

    def notify_listeners(self, server_message):
        for listener in self._listeners:
            listener.notify_server_message(server_message)

    def start_listening(self, observer):
        try:
            while not self._stop_listening.is_set():
                data = receive_message(self.client_socket)
                if not data:
                    break
                try:
                    messages = []
                    for data_item in data:
                        message = json.loads(data_item)
                        messages.append(message)
                        
                    for message in messages:
                        self.notify_listeners(message)
                except json.JSONDecodeError:
                    print("Error decoding JSON message")
        except ConnectionResetError:
            print("Server disconnected")
        except KeyboardInterrupt:
            observer.stop()

    def stop_listening(self):
        self._stop_listening.set()

    def listen_to_server_messages(self):
        # Start listening in a separate thread
        listening_thread = threading.Thread(target=self.start_listening)
        listening_thread.daemon = True 
        listening_thread.start()