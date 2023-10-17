import json
import os

# Helper script that defines functions for both sending and receiving messages on client and server side

def send_message(socket, message):
    if os.environ["DEBUG"] == "on":
        print("sending:", message)
    # Serialize the message to JSON
    message_json = dump_message(message)
    # Send the message to the server
    socket.sendall(message_json.encode())

def dump_message(message):
    # Dump message and add delimiter
    return json.dumps(message) + '\n'

# Define function to receive the complete message in 1024 byte blocks
def receive_message(client_socket):
    data = b""

    # Concatenate data as long as there is data flow
    while True:
        chunk = client_socket.recv(1024)
        if not chunk:
            break
        data += chunk
        if b"\n" in chunk:
            break

    # Return decoded data
    return data.decode()