import os
import json
import socket
from threading import Thread
import difflib
import base64

# Import server configuration
# Load configuration from the JSON file
with open('server_config.json', 'r') as config_file:
    config = json.load(config_file)

# Use the loaded configuration
SERVER_HOST = config["server_host"]
SERVER_PORT = config["server_port"]
SERVER_DIR = config["server_dir"]

# Define function to receive the complete message from the client in 1024 byte blocks
def receive_client_message(client_socket):
    data = b""
    
    # Concatenate data as long as there is data flow
    while True:
        chunk = client_socket.recv(1024)
        if not chunk:
            break
        data += chunk

    # Return decoded data
    return data.decode()

def handle_client(client_socket):
    try:
        while True:
            data = receive_client_message(client_socket)
            if not data:
                break

            # Load data as json
            message = json.loads(data)

            # Perform update handling
            if message["action"] == "update":
                print(message["event_type"])
                handle_update(message)

    except json.JSONDecodeError:
        print("Error decoding JSON message")
    finally:
        client_socket.close()

def handle_update(message):
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
            os.remove(server_path)

    elif message["event_type"] == "created":
        # Handle file creation event
        server_path = os.path.join(SERVER_DIR, message["path"])
        
        # Decode the Base64-encoded data received from the client
        client_data_base64 = message["data"]
        client_data_bytes = base64.b64decode(client_data_base64)
        
        # Write the client data to the server file
        with open(server_path, 'wb') as server_file:
            server_file.write(client_data_bytes)

    elif message["event_type"] == "moved":
        # Handle file move/rename event
        src_server_path = os.path.join(SERVER_DIR, message["src_path"])
        dest_server_path = os.path.join(SERVER_DIR, message["dest_path"])
        if os.path.exists(src_server_path):
            os.rename(src_server_path, dest_server_path)

if __name__ == "__main__":
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

    while True:
        client_socket, _ = server_socket.accept()
        print(f"Accepted connection from {client_socket.getpeername()}")
        client_handler = Thread(target=handle_client, args=(client_socket,))
        client_handler.start()
