import argparse
import os
import sys
import socket
import json
import base64
import shutil
import pandas as pd

sys.path.append("../")
from resources.message_sending import send_message, receive_message

# Import server configuration
# Load configuration from the JSON file
with open('server_config.json', 'r') as config_file:
    config = json.load(config_file)

# Use the loaded configuration
SERVER_HOST = config["server_host"]
SERVER_PORT = config["server_port"]
SERVER_DIR = config["server_dir"]

def get_external_ip():
    try:
        # Use a dummy socket to get the external IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error: {e}")
        return None

def parse_command_line_args():
    global SERVER_HOST, SERVER_PORT, SERVER_DIR
    parser = argparse.ArgumentParser(description="Client replicating Dropbox functionality by syncing files and folders in the background")
    
    # Add command-line arguments to overwrite configuration values
    parser.add_argument('--server-port', type=int, help='Server port number')
    parser.add_argument('--debug', action='store_true', help='Decide whether sent messages should be logged for debugging')
    parser.add_argument('--server-dir', help='Server directory path')

    args = parser.parse_args()

    if args.debug:
        os.environ["DEBUG"] = "on"
    else: 
        os.environ["DEBUG"] = "off"

    SERVER_HOST = get_external_ip()
    # Update the configuration based on the command-line arguments
    if args.server_port:
        SERVER_PORT = args.server_port
    if args.server_dir and os.path.exists(args.server_dir):
        SERVER_DIR = args.server_dir
    elif ((args.server_dir and not os.path.exists(args.server_dir)) or
          (not args.server_dir and not os.path.exists(SERVER_DIR))):
        print("The server directory does not exist.")
        sys.exit(0)

class Server:
    def __init__(self, host, port):
        self.logged_in_clients = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((host, port))

    # Main function dedicated to each client
    def handle_clients(self):
        try:
            # Listen for message from client
            while True:
                messages, sender_address = receive_message(self.server_socket)
                if os.environ["DEBUG"] == "on":
                    print(messages, sender_address)
                if not messages:
                    break
                try:
                    for item in messages:
                        # Perform update handling
                        message = json.loads(item)
                        if message["action"] == "update" and sender_address in self.logged_in_clients:
                            self.handle_update(message, sender_address)
                        # Perform login handling
                        elif message["action"] == "login":
                            self.handle_login(message, sender_address)
                        # Remove client on disconnect
                        elif message["action"] == "disconnect":
                            print(f"{sender_address} disconnected")
                            if sender_address in self.logged_in_clients:
                                del self.logged_in_clients[sender_address]
                except json.JSONDecodeError:
                    print("Error decoding JSON message")
        except KeyboardInterrupt:
            message = {
                "action": "shutdown"
            }

            for client in self.logged_in_clients.keys():
                send_message(self.server_socket, message, client)

    # Define what to do on specific client messages
    def handle_update(self, message, client_address):
        if os.environ["DEBUG"] == "on": 
            print(message["event_type"])

        if message["event_type"] == "modified":
            # Handle file modification event with differences maybe to be added (?)

            # For the moment, use the same logic as for file creation
            # Handle file creation event
            server_path = os.path.join(SERVER_DIR, self.logged_in_clients[client_address], message["path"])

            # Decode the Base64-encoded data received from the client
            client_data_base64 = message["data"]
            client_data_bytes = base64.b64decode(client_data_base64)

            # Write the client data to the server file
            with open(server_path, 'wb') as server_file:
                server_file.write(client_data_bytes)

        elif message["event_type"] == "deleted":
            # Handle file deletion event
            server_path = os.path.join(SERVER_DIR, self.logged_in_clients[client_address], message["path"])
            if os.path.exists(server_path):
                if message["structure"] == "dir":
                    shutil.rmtree(server_path)
                else:
                    os.remove(server_path)

        elif message["event_type"] == "created":
            # Handle file creation event
            server_path = os.path.join(SERVER_DIR, self.logged_in_clients[client_address], message["path"])

            if message["structure"] == "dir":
                os.makedirs(server_path)
            else:
                # Decode the Base64-encoded data received from the client
                client_data_base64 = message["data"]
                client_data_bytes = base64.b64decode(client_data_base64)

                # Write the decoded data to the file on the server
                with open(server_path, 'wb') as server_file:
                    server_file.write(client_data_bytes)

        elif message["event_type"] == "moved":
            # Handle file move/rename event
            src_server_path = os.path.join(SERVER_DIR, self.logged_in_clients[client_address], message["src_path"])
            dest_server_path = os.path.join(SERVER_DIR, self.logged_in_clients[client_address], message["dest_path"])
            if os.path.exists(src_server_path):
                if message["structure"] == "dir":
                    try:
                        shutil.move(src_server_path, dest_server_path)
                    except:
                        pass
                else:
                    try:
                        os.rename(src_server_path, dest_server_path)
                    except:
                        pass

        reply = {
            "action": "received",
            "id": message["id"]
        }

        send_message(self.server_socket, reply, client_address)

    # Handle client login
    def handle_login(self, message, client_address):
        if os.environ["DEBUG"] == "on": 
            print(message["action"])

        # Read users "database"
        users = pd.read_csv("users.csv")

        # Read credentials from message
        username = message["username"]
        password = message["password"]

        # Default login response
        login_message = {
            "type": "serverMessage",
            "action": "login"
        }

        # Verify Credentials
        if username in users["username"].unique():
            saved_password = users[users["username"] == username]["password"].item()
            if saved_password == password or pd.isnull(saved_password):
                login_message["result"] = "successful"
                login_message["text"] = "Logged in successfully"
                self.logged_in_clients[client_address] = username
                userpath = os.path.join(SERVER_DIR, username)
                if not os.path.isdir(userpath):
                    os.makedirs(userpath)
                print(f"Login successful by {client_address}")
            else:
                login_message["result"] = "failed"
                login_message["text"] = "Password is wrong"
        else:
            login_message["result"] = "failed"
            login_message["text"] = "Username does not exist"

        send_message(self.server_socket, login_message, client_address)


if __name__ == "__main__":
    # Parse cmd line args
    parse_command_line_args()

    # Boot server
    try:
        server = Server(SERVER_HOST, SERVER_PORT)
        print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")
    except OSError as e:
        print(f"Error binding to {SERVER_HOST}:{SERVER_PORT}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    server.handle_clients()

    print("Server terminated")