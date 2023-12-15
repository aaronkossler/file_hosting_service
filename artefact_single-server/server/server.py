import os
import json
import socket
from threading import Thread
import base64
import shutil
import signal
import pandas as pd
import argparse

import sys
sys.path.append('../')
from resources.message_sending import send_message, receive_message

# Import server configuration
# Load configuration from the JSON file
with open('server_config.json', 'r') as config_file:
    config = json.load(config_file)

# Use the loaded configuration
SERVER_HOST = config["server_host"]
SERVER_PORT = config["server_port"]
SERVER_DIR = config["server_dir"]

# Define a list to store active client sockets
active_clients = []

# Define a list to store clients, that are logged in
logged_clients = {}

def parse_command_line_args():
    global SERVER_HOST, SERVER_PORT, SERVER_DIR
    parser = argparse.ArgumentParser(description="Client replicating Dropbox functionality by syncing files and folders in the background")
    
    # Add command-line arguments to overwrite configuration values
    parser.add_argument('--server-host', help='Server host address')
    parser.add_argument('--server-port', type=int, help='Server port number')
    parser.add_argument('--debug', action='store_true', help='Decide whether sent messages should be logged for debugging')
    parser.add_argument('--server-dir', help='Server directory path')

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
    if args.server_dir and os.path.exists(args.server_dir):
        SERVER_DIR = args.server_dir
    elif ((args.server_dir and not os.path.exists(args.server_dir)) or
          (not args.server_dir and not os.path.exists(SERVER_DIR))):
        print("The server directory does not exist.")
        sys.exit(0)

# Main function dedicated to each client
def handle_client(client_socket):
    try:
        active_clients.append(client_socket)
        # Listen for message from client
        while True:
            data = receive_message(client_socket)
            if not data:
                break
            try:
                messages = []
                for data_item in data:
                    message = json.loads(data_item)
                    messages.append(message)

                for message in messages:
                    # Perform update handling
                    if message["action"] == "update" and client_socket in logged_clients:
                        handle_update(message, client_socket)
                    # Perform login handling
                    elif message["action"] == "login":
                        handle_login(message, client_socket)
            except json.JSONDecodeError:
                print("Error decoding JSON message")

    except ConnectionResetError:
        print("Client disconnected")
    finally:
        print(f"{client_socket.getpeername()} disconnected")
        client_socket.close()
        active_clients.remove(client_socket)
        if client_socket in logged_clients:
            del logged_clients[client_socket]

# Define what to do on specific client messages
def handle_update(message, client_socket):
    if os.environ["DEBUG"] == "on": 
        print(message["event_type"])
    if message["event_type"] == "modified":
        # Handle file modification event with differences maybe to be added (?)

        # For the moment, use the same logic as for file creation
        # Handle file creation event
        server_path = os.path.join(SERVER_DIR, logged_clients[client_socket], message["path"])

        # Decode the Base64-encoded data received from the client
        client_data_base64 = message["data"]
        client_data_bytes = base64.b64decode(client_data_base64)

        # Write the client data to the server file
        with open(server_path, 'wb') as server_file:
            server_file.write(client_data_bytes)

    elif message["event_type"] == "deleted":
        # Handle file deletion event
        server_path = os.path.join(SERVER_DIR, logged_clients[client_socket], message["path"])
        if os.path.exists(server_path):
            if message["structure"] == "dir":
                shutil.rmtree(server_path)
            else:
                os.remove(server_path)

    elif message["event_type"] == "created":
        # Handle file creation event
        server_path = os.path.join(SERVER_DIR, logged_clients[client_socket], message["path"])

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
        src_server_path = os.path.join(SERVER_DIR, logged_clients[client_socket], message["src_path"])
        dest_server_path = os.path.join(SERVER_DIR, logged_clients[client_socket], message["dest_path"])
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

# Handle client login
def handle_login(message, client_socket):
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
            logged_clients[client_socket] = username
            userpath = os.path.join(SERVER_DIR, username)
            if not os.path.isdir(userpath):
                os.makedirs(userpath)
            print(f"Login successful by {client_socket.getpeername()}")
        else:
            login_message["result"] = "failed"
            login_message["text"] = "Password is wrong"
    else:
        login_message["result"] = "failed"
        login_message["text"] = "Username does not exist"

    send_message(client_socket, login_message)

# If the server is closed, notify clients
def send_shutdown_message_to_clients():
    shutdown_message = {
        "type": "serverMessage",
        "action": "shutdown"
    }

    for client_socket in active_clients:
        send_message(client_socket, shutdown_message)
        client_socket.close()

# Add function to forward the Ctrl+C event to
def handle_server_termination(signum, frame):
    print("Server terminated")
    send_shutdown_message_to_clients()
    sys.exit(0)

# Register the signal handler for Ctrl+C
signal.signal(signal.SIGINT, handle_server_termination)

if __name__ == "__main__":
    # Parse cmd line args
    parse_command_line_args()

    # Boot server
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(5)
        print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")
    except OSError as e:
        print(f"Error binding to {SERVER_HOST}:{SERVER_PORT}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # Accept new clients and hand each one over to its own thread
    try:
        while True:
            client_socket, _ = server_socket.accept()
            print(f"Accepted connection from {client_socket.getpeername()}")
            client_handler = Thread(target=handle_client, args=(client_socket,))
            client_handler.daemon = True
            client_handler.start()
    except KeyboardInterrupt:
        pass

    print("Server terminated")