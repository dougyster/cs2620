from xmlrpc.client import ServerProxy
import threading
from typing import Callable
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) # add parent directory to python path
from interfaces.client_communication_interface import ClientCommunicationInterface

class ClientRpcHandler(ClientCommunicationInterface):
    def __init__(self):
        pass

    def start_server(self, host: str, port: int) -> None:
        pass

    def stop_server(self) -> None:
        pass

    def send_message(self, client, message: bytes) -> None:
        pass

    def get_message(self, num_messages: int) -> bytes:
        pass 