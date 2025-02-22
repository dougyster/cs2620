from xmlrpc.server import SimpleXMLRPCServer
import threading
from typing import Callable
from backend.interfaces.communication_interface import CommunicationInterface

class RpcHandler(CommunicationInterface):
    def __init__(self):
        self.server = None
        self.running = False
        self.message_handler = None

    def start_server(self, host: str, port: int, message_handler: Callable) -> None:
        self.server = SimpleXMLRPCServer((host, port), allow_none=True)
        self.message_handler = message_handler
        self.running = True
        
        # Register RPC methods
        self.server.register_function(self.handle_rpc_message, "send_message")
        
        print(f"RPC server running on {host}:{port}")
        
        # Run server in a separate thread
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def stop_server(self) -> None:
        self.running = False
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def send_message(self, client, message: bytes) -> None:
        # In RPC, clients make calls to server, not vice versa
        # This would need to be implemented differently for bidirectional communication
        pass

    def handle_rpc_message(self, message_data):
        """Handle incoming RPC messages"""
        if self.message_handler and self.running:
            return self.message_handler(message_data, None)  # No client socket in RPC
        return None 