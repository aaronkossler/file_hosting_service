import json
import os

# Helper script that defines functions for both sending and receiving messages on client and server side

def send_message(socket, message, receiver_address):
    if os.environ["DEBUG"] == "on":
        print("sending:", message)
    # Serialize the message to JSON
    message_json = dump_message(message)
    
    # Send the message to the server
    for chunk in split_into_chunks(message_json, 65536):
        if type(receiver_address) == list:
            for receiver in receiver_address:
                socket.sendto(chunk.encode(), receiver)
        else:
            socket.sendto(chunk.encode(), receiver_address)

def dump_message(message):
    # Dump message and add delimiter
    return json.dumps(message) + '\n'

def split_into_chunks(data, chunk_size):
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

# Define function to receive the complete message
def receive_message(socket):
    data, sender_address = socket.recvfrom(65536)

    # Process and decode each individual message
    decoded_messages = [message.decode() for message in data.split(b'\n') if message]

    return decoded_messages, sender_address
