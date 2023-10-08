from abc import ABC, abstractmethod

class MessageListener(ABC):
    @abstractmethod
    def notify_server_message(self, server_message):
        pass