import sys
import os
import struct
import threading
import json

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# importing interfaces
from backend.interfaces.business_logic_interface import BusinessLogicInterface
from backend.interfaces.db_interface import MongoDBInterface
from backend.interfaces.serialization_interface import SerializationInterface

# importing implementations
from backend.interactor.business_logic import BusinessLogic
from backend.database.mongo_operations import MongoOperation

# importing protocols
from backend.protocol.wire_protocol import WireProtocol
from backend.protocol.json_protocol import JsonProtocol
import socket

class Controller:
    def __init__(self, business_logic: BusinessLogicInterface, wire_protocol: SerializationInterface):
        self.business_logic = business_logic
        self.wire_protocol = wire_protocol
        self.online_users = {}  # Track online users {username: client_socket}
        self.lock = threading.Lock()  # For thread-safe operations

    def handle_incoming_message(self, data: bytes, client_socket: socket.socket, is_json: bool):
        print(f"Received data: {data}")
        print(f"Client socket: {client_socket}")
        
        try:
            if is_json:
                # For JSON, decode the entire message
                json_data = json.loads(data.decode('utf-8'))
                msg_type = json_data['type']
                payload = json_data['payload']
            else:
                # For wire protocol, use existing header parsing
                header = data[:5]
                msg_type_code, payload_len = struct.unpack('!BI', header)
                msg_type = chr(msg_type_code)
                payload = data[5:5+payload_len]
            
            # Process message based on type
            if msg_type == 'R':  # Register
                username, password = self.wire_protocol.deserialize_register(payload)
                success = self.business_logic.create_user(username, password)
                if success:
                    return self.wire_protocol.serialize_success("User created successfully")
                else:
                    return self.wire_protocol.serialize_error("Failed to create user")
                
            elif msg_type == 'L':  # Login
                username, password = self.wire_protocol.deserialize_login(payload)
                    
                maybe_success = self.business_logic.login_user(username, password)
                self.online_users[username] = client_socket
                
                if maybe_success:
                    messages = self.business_logic.get_messages(username)
                    user = self.business_logic.get_user(username)
                    
                    client_socket.sendall(self.wire_protocol.serialize_success("Login successful"))
                    if messages:
                        client_socket.sendall(self.wire_protocol.serialize_all_messages(messages))
                    
                    log_off_time = user.get('log_off_time')
                    view_count = user.get('view_count', 5)
                    return self.wire_protocol.serialize_user_stats(log_off_time, view_count)
                else:
                    return self.wire_protocol.serialize_error("Login failed")
                
            elif msg_type == 'M':  # Message
                sender, recipient, msg_content = self.wire_protocol.deserialize_message(payload)
                    
                did_message_send = self.business_logic.send_message(sender, recipient, msg_content)
                
                with self.lock:
                    if recipient in self.online_users:
                        recipient_socket = self.online_users[recipient]
                        recipient_socket.sendall(data)

                if did_message_send:
                    return self.wire_protocol.serialize_success("Message sent")
                else:
                    return self.wire_protocol.serialize_error("Message not sent")
            elif msg_type == 'G':  # Get User List
                user_list = self.business_logic.get_all_users()
                return self.wire_protocol.serialize_user_list(user_list)
            elif msg_type == 'D':  # Delete Message
                message, timestamp, sender, receiver = self.wire_protocol.deserialize_delete_message(payload)
                    
                did_delete = self.business_logic.delete_message(message, timestamp, sender, receiver)
                if did_delete:
                    return self.wire_protocol.serialize_success("Message deleted")
                else:
                    return self.wire_protocol.serialize_error("Message not deleted")
                
            elif msg_type == 'U':  # Delete User
                username = self.wire_protocol.deserialize_delete_user(payload)
                    
                success = self.business_logic.delete_user(username)
                if success:
                    return self.wire_protocol.serialize_success("User deleted successfully")
                else:
                    return self.wire_protocol.serialize_error("Failed to delete user")
                
            elif msg_type == 'W':  # Update view count
                username, new_count = self.wire_protocol.deserialize_view_count_update(payload)
                    
                success = self.business_logic.update_view_count(new_count, username)
                if success:
                    return self.wire_protocol.serialize_success("View count updated")
                else:
                    return self.wire_protocol.serialize_error("Failed to update view count")
                
            else:
                return self.wire_protocol.serialize_error("Invalid message type")
                
        except Exception as e:
            print(f"Error processing message: {e}")
            return self.wire_protocol.serialize_error(str(e))

def start_server():
    # Implement database operations
    mongo_operations = MongoOperation()

    # Implement business logic
    business_logic = BusinessLogic(mongo_operations)

    # Implement protocols
    wire_protocol = WireProtocol()  
    json_protocol = JsonProtocol()
    protocol_of_choice = wire_protocol # change protocol here
    is_json = protocol_of_choice == json_protocol

    # Initialize controller
    controller = Controller(business_logic, protocol_of_choice)

    # Start the server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 8081))
    server.listen(5)
    print("Server is running on port 8081")

    try:
        while True:
            client_socket, client_address = server.accept()
            print(f"Connection established with {client_address}")
            handle_client_connection(client_socket, client_address, controller, is_json)
    finally:
        server.close()

def handle_client_connection(client_socket, client_address, controller, is_json):
    """Handle a client connection in a separate thread."""
    thread = threading.Thread(
        target=handle_client_messages,
        args=(client_socket, client_address, controller, is_json)
    )
    thread.daemon = True
    thread.start()

def handle_client_messages(client_socket, client_address, controller, is_json):
    """Handle messages from a client."""
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                print(f"Client {client_address} disconnected")
                break

            response = controller.handle_incoming_message(data, client_socket, is_json)
            if response:
                client_socket.sendall(response)
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
    finally:
        client_socket.close()
        with controller.lock:
            # Find username by socket and remove from online users
            username_to_remove = None
            for username, sock in controller.online_users.items():
                if sock == client_socket:
                    username_to_remove = username
                    break
            
            if username_to_remove:
                print(f"User {username_to_remove} logged off")
                controller.business_logic.update_log_off_time(username_to_remove)
                del controller.online_users[username_to_remove]
            else:
                print("Client disconnected before login")
                
        print(f"Connection closed with {client_address}")


if __name__ == "__main__":
    start_server()

        