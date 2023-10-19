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
    messages = []

    # Receive data until the custom delimiter is found
    while True:
        chunk = client_socket.recv(1024)
        if not chunk:
            break
        data += chunk

    # Split the received data by the delimiter
    parts = data.split(b'\n')

    # Process and decode each individual message
    decoded_messages = [message.decode() for message in parts]

    return decoded_messages

