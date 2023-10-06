import os
import json
import socket
from threading import Thread
import difflib
import base64
import shutil
import signal
import pandas as pd

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
logged_clients = []

# Main function dedicated to each client
def handle_client(client_socket):
    try:
        active_clients.append(client_socket)
        # Listen for message from client
        while True:
            data = receive_message(client_socket)
            if not data:
                break

            message = json.loads(data)

            # Perform update handling
            if message["action"] == "update" and client_socket in logged_clients:
                handle_update(message)
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
        try:
            logged_clients.remove(client_socket)
        except:
            pass

# Define what to do on specific client messages
def handle_update(message):
    print(message["event_type"])
    if message["event_type"] == "modified":
        # Handle file modification event with differences
        server_path = os.path.join(SERVER_DIR, message["path"])

        """ CURRENTLY NOT WORKING
        # Read the current content of the server file
        with open(server_path, 'r', encoding='utf-8') as server_file:
            server_content = server_file.readlines()
        
        # Decode the Base64-encoded data received from the client
        client_data_base64 = message["data"]
        client_data_bytes = base64.b64decode(client_data_base64)
        
        # Decode the client data as UTF-8 text
        client_data = client_data_bytes.decode('utf-8')
        
        # Apply the differences to the server content
        d = difflib.Differ()
        diff = list(d.compare(server_content, client_data.splitlines(keepends=True)))
        
        # Update the server file with the modified content
        with open(server_path, 'w', encoding='utf-8') as server_file:
            server_file.writelines(diff)"""

        # Temporarily use the same logic as for file creation
        # Handle file creation event
        server_path = os.path.join(SERVER_DIR, message["path"])

        # Decode the Base64-encoded data received from the client
        client_data_base64 = message["data"]
        client_data_bytes = base64.b64decode(client_data_base64)

        # Write the client data to the server file
        with open(server_path, 'wb') as server_file:
            server_file.write(client_data_bytes)

    elif message["event_type"] == "deleted":
        # Handle file deletion event
        server_path = os.path.join(SERVER_DIR, message["path"])
        if os.path.exists(server_path):
            if message["structure"] == "dir":
                shutil.rmtree(server_path)
            else:
                os.remove(server_path)

    elif message["event_type"] == "created":
        # Handle file creation event
        server_path = os.path.join(SERVER_DIR, message["path"])

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
        src_server_path = os.path.join(SERVER_DIR, message["src_path"])
        dest_server_path = os.path.join(SERVER_DIR, message["dest_path"])
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
    print(message["action"])

    # Read users "database"
    users = pd.read_csv("users.csv")

    # Read credentials from message
    username = message["username"]
    password = message["password"]

    # Default message
    login_message = {
        "type": "serverMessage",
        "action": "login"
    }

    # Verify Credentials
    if username in users["username"].unique():
        if users[users["username"] == username]["password"].item() == password:
            login_message["result"] = "successful"
            login_message["text"] = "Logged in successfully"
            logged_clients.append(client_socket)
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

# Add function to forward the Ctrl+C event to
def handle_server_termination(signum, frame):
    print("Server terminated")
    send_shutdown_message_to_clients()
    sys.exit(0)

# Register the signal handler for Ctrl+C
signal.signal(signal.SIGINT, handle_server_termination)

if __name__ == "__main__":
    # Boot server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

    # Accept new clients and hand each one over to its own thread
    try:
        while True:
            client_socket, _ = server_socket.accept()
            print(f"Accepted connection from {client_socket.getpeername()}")
            client_handler = Thread(target=handle_client, args=(client_socket,))
            client_handler.start()
    except KeyboardInterrupt:
        pass

    print("Server terminated")