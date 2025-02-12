import sys
import os
import struct
import threading

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# importing interfaces
from backend.interfaces.business_logic_interface import BusinessLogicInterface
from backend.interfaces.db_interface import MongoDBInterface

# importing implementations
from backend.interactor.business_logic import BusinessLogic
from backend.database.mongo_operations import MongoOperation

# importing protocol
from backend.protocol.wire_protocol import serialize_success, serialize_error, serialize_all_messages

import socket

class Controller:
    def __init__(self, business_logic: BusinessLogicInterface):
        self.business_logic = business_logic
        self.online_users = {}  # Track online users {username: client_socket}
        self.lock = threading.Lock()  # For thread-safe operations

    def handle_incoming_message(self, data: bytes, client_socket: socket.socket):
        print(f"Received data: {data}")
        print(f"Client socket: {client_socket}")
        
        try:
            # Read header (5 bytes)
            header = data[:5]
            msg_type_code, payload_len = struct.unpack('!BI', header)
            msg_type = chr(msg_type_code)
            
            # Read payload
            payload = data[5:5+payload_len]
            
            # Process message based on type
            if msg_type == 'R':  # Register/Create User
                offset = 0
                user_len = struct.unpack_from('!H', payload, offset)[0]
                offset += 2
                username = payload[offset:offset+user_len].decode('utf-8')
                offset += user_len
                pass_len = struct.unpack_from('!H', payload, offset)[0]
                offset += 2
                password = payload[offset:offset+pass_len].decode('utf-8')
                
                # Call business logic
                success = self.business_logic.create_user(username, password)
                if success:
                    return serialize_success("User created successfully")
                else:
                    return serialize_error("Failed to create user or duplicate user")
            elif msg_type == 'L':  # Login
                offset = 0
                user_len = struct.unpack_from('!H', payload, offset)[0]
                offset += 2
                username = payload[offset:offset+user_len].decode('utf-8')
                offset += user_len
                pass_len = struct.unpack_from('!H', payload, offset)[0]
                offset += 2
                password = payload[offset:offset+pass_len].decode('utf-8')
                
                maybe_success = self.business_logic.login_user(username, password)
                self.online_users[username] = client_socket
                if maybe_success:
                    messages = self.business_logic.get_messages(username)
                    if messages:
                        client_socket.sendall(serialize_all_messages(messages))
                    return serialize_success("Login successful")
                else:
                    return serialize_error("Login failed")
            elif msg_type == 'M':  # Message handling
                offset = 0
                sender_len = struct.unpack_from('!H', payload, offset)[0]
                offset += 2
                sender = payload[offset:offset+sender_len].decode()
                offset += sender_len
                recipient_len = struct.unpack_from('!H', payload, offset)[0]
                offset += 2
                recipient = payload[offset:offset+recipient_len].decode()
                offset += recipient_len
                msg_len = struct.unpack_from('!I', payload, offset)[0]
                offset += 4
                msg_content = payload[offset:offset+msg_len].decode()

                did_message_send = self.business_logic.send_message(sender, recipient, msg_content)
                
                with self.lock:
                    if recipient in self.online_users:
                        # Recipient is online, forward immediately
                        recipient_socket = self.online_users[recipient]
                        recipient_socket.sendall(data)

                if did_message_send:
                    return serialize_success("Message sent")
                else:
                    return serialize_error("Message not sent")
            else:
                return serialize_error("Invalid message type")
                
        except Exception as e:
            print(f"Error processing message: {e}")
            return serialize_error(str(e))

def start_server():
    # Initialize the business logic
    business_logic = BusinessLogic(MongoOperation())
    controller = Controller(business_logic)

    # Start the server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 8081))
    server.listen(5)
    print("Server is running on port 8081")

    try:
        while True:
            client_socket, client_address = server.accept()
            print(f"Connection established with {client_address}")
            handle_client_connection(client_socket, client_address, controller)
    finally:
        server.close()

def handle_client_connection(client_socket, client_address, controller):
    """Handle a client connection in a separate thread."""
    thread = threading.Thread(
        target=handle_client_messages,
        args=(client_socket, client_address, controller)
    )
    thread.daemon = True
    thread.start()

def handle_client_messages(client_socket, client_address, controller):
    """Handle messages from a client."""
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                print(f"Client {client_address} disconnected")
                break

            response = controller.handle_incoming_message(data, client_socket)
            if response:
                client_socket.sendall(response)
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
    finally:
        client_socket.close()
        with controller.lock:
            if client_address[0] in controller.online_users:
                del controller.online_users[client_address[0]]
        print(f"Connection closed with {client_address}")


if __name__ == "__main__":
    start_server()

        