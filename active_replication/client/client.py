import os
import time
import json
import socket
import maskpass
import threading
import argparse
from watchdog.observers import Observer
from components.abstract_message_listener import MessageListener
from components.event_handler import EventHandler
from components.server_message_notifier import ServerMessageNotifier
from components.server_list_manager import ServerListManager

import sys
sys.path.append('../')
from resources.message_sending import send_message

# Import server configuration
# Load configuration from the JSON file
with open('client_config.json', 'r') as config_file:
    config = json.load(config_file)

# Use the loaded configuration
#SERVER_HOST = config["server_host"]
#SERVER_PORT = config["server_port"]
CLIENT_DIR = config["client_dir"]

def parse_command_line_args():
    global SERVERS, CLIENT_DIR
    parser = argparse.ArgumentParser(description="Client replicating Dropbox functionality "
                                                 "by syncing files and folders in the background")
    
    # Add command-line arguments to overwrite configuration values
    parser.add_argument('--server-hosts', nargs='+', help='Server host addresses')
    parser.add_argument('--server-ports', nargs='+', type=int, help='Server port numbers')
    parser.add_argument('--debug', action='store_true', help='Decide whether sent messages should be logged for debugging')
    parser.add_argument('--client-dir', help='Client directory path')

    args = parser.parse_args()

    if args.debug:
        os.environ["DEBUG"] = "on"
    else: 
        os.environ["DEBUG"] = "off"

    # Update the configuration based on the command-line arguments
    if len(args.server_hosts) != 1 and len(args.server_hosts) != len(args.server_ports):
        raise ValueError("Number of server IPs does not match the provided number of ports! In case you want to connect multiple processes running on the same host, enter the single host and all port numbers.")
    else:
        SERVERS = []
        for i, port in enumerate(args.server_ports):
            if len(args.server_hosts) > 1:
                host = args.server_hosts[i]
            else:
                host = args.server_hosts[0]
            SERVERS.append((host, port))

    if args.client_dir and os.path.exists(args.client_dir):
        CLIENT_DIR = args.client_dir
    elif ((args.client_dir and not os.path.exists(args.client_dir)) or
          (not args.client_dir and not os.path.exists(CLIENT_DIR))):
        print("The client directory does not exist.")
        sys.exit(0)

# Class responsible for the Client instance
class Client(MessageListener):
    def __init__(self, client_dir, servers):
        self.client_dir = client_dir
        self.server_list_manager = ServerListManager(servers)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.message_handler = ServerMessageNotifier(self.client_socket)
        self.event_handler = EventHandler(self)
        self.login_response = False
        self.logged_in = False
        self.reply_log = {}

    # Return current list of servers
    def get_servers(self):
        return self.server_list_manager.get_servers()

    # Handle server messages
    def notify_server_message(self, message, server_address):
        if message["action"] == "received":
            self.server_list_manager.register_reply(message["id"], server_address)
        elif message["action"] == "shutdown":
            self.server_list_manager.remove_server(server_address)
        elif message["action"] == "login":
            self.handle_login_message(message)

    # Send a message to the server
    def send_message(self, message):
        self.server_list_manager.check_server_timeouts()
        send_message(self.client_socket, message, self.get_servers())

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

            self.send_message(message)

            # Wait for Server to answer for 10 seconds
            timeout = 10
            timeout_start = time.time()
            while time.time() < timeout_start + timeout and not self.logged_in and not self.login_response:
                time.sleep(1)

            if not self.login_response and not self.logged_in:
                print("None of the servers are responding. Servers are potentially down. Please try again later or check your internet connection.")
            elif not self.logged_in:
                self.login_response = False

    def handle_login_message(self, message):
        if message["action"] == "login" and not self.logged_in:
            print(message["text"])
            self.login_response = True
            if message["result"] == "successful":
                self.logged_in = True
        elif message["action"] == "shutdown":
            self.disconnected = True

    # Start observing to events
    def start(self):
        observer = Observer()
        observer.schedule(self.event_handler, path=self.client_dir, recursive=True)
        observer.start()

        # start listening for messages
        self.message_handler.add_listener(self)
        self.message_handler.listen_to_server_messages()

        observer.join()

    # Run client
    def run(self):
        try:
            # Start listening to events and server messages in a separate thread
            listen_thread = threading.Thread(target=self.start)
            listen_thread.daemon = True
            listen_thread.start()

            # Login
            self.login()

            listen_thread.join()
        except (KeyboardInterrupt, ConnectionResetError):
            self.shutdown("Closing client...")

    # Close client
    def shutdown(self, message):
        print(message)
        self.message_handler.stop_listening()
        self.event_handler.on_shutdown()
        self.client_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    # Parse cmd line args
    parse_command_line_args()
    # Create Client instance
    client = Client(CLIENT_DIR, SERVERS)
    # Start Client instance
    client.run()
