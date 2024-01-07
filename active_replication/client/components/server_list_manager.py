from datetime import datetime
import os

# Class for keeping the server list up to date with active replication
class ServerListManager:
    def __init__(self, servers, client):
        self.client = client
        self.servers = servers
        self.reply_log = {}
        self.server_timeout = 5 # in seconds

    def get_servers(self):
        return self.servers
    
    # Register when a message was sent
    def register_send_event(self, timestamp, message_id):
        self.reply_log[message_id] = {
            "timestamp": timestamp,
            "pending_servers": self.servers.copy()
        }
        if os.environ["DEBUG"] == "on":
            print(self.reply_log)

    # Check if any servers did not reply to the message within the specified timeout window
    def check_server_timeouts(self):
        for _, msg_data in self.reply_log.items():
            diff = datetime.now() - msg_data["timestamp"]
            if diff.total_seconds() >= self.server_timeout:
                for server in msg_data["pending_servers"]:
                    print("Server {} timed out and has been removed from the server list.".format(server))
                    if server in self.servers: self.remove_server(server)

    # Add logic to remove server and shutdown, if no servers are left
    def remove_server(self, removed_server):
        self.servers.remove(removed_server)
        if len(self.servers) == 0:
            self.client.shutdown("All servers disconnected. Closing client...")
        else:
            print("Server {} disconnected. Still enough backups available.".format(removed_server))

    # Register 
    def register_reply(self, msg_id, server_address):
        self.check_server_timeouts()
        if server_address in self.reply_log[msg_id]["pending_servers"]:
            self.reply_log[msg_id]["pending_servers"].remove(server_address)
            if os.environ["DEBUG"] == "on": 
                print("Reply for message {} received from {}".format(msg_id, server_address))
        
        # Remove msg_id from reply_log if all messages have been acknowledged
        if len(self.reply_log[msg_id]["pending_servers"]) == 0:
            del self.reply_log[msg_id]
