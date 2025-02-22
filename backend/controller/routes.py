import sys
import os
import struct
import threading
import json
from enum import Enum

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
from backend.protocol.rpc_protocol import RpcProtocol
import socket
from backend.socket.socket_handler import SocketHandler
from backend.socket.rpc_handler import RpcHandler

class ProtocolType(Enum):
    WIRE = "wire"
    JSON = "json"
    RPC = "rpc"

class Controller:
    def __init__(self, business_logic: BusinessLogicInterface, wire_protocol: SerializationInterface):
        self.business_logic = business_logic
        self.wire_protocol = wire_protocol
        self.online_users = {}  # Track online users {username: client_socket}
        self.lock = threading.Lock()  # For thread-safe operations

    def handle_incoming_message(self, data: bytes, protocol_type: ProtocolType, client_socket: socket.socket=None):
        print(f"Received data: {data}")
        print(f"Client socket: {client_socket}")
        print(f"Protocol type: {protocol_type}")
        
        try:
            if protocol_type == ProtocolType.RPC:
                # For RPC, extract from params
                json_data = json.loads(data.decode('utf-8'))
                params = json_data.get('params', {})
                msg_type = params.get('type')
                payload = params  # The entire params object is our payload
            
            elif protocol_type == ProtocolType.JSON:
                # For JSON, decode the entire message
                json_data = json.loads(data.decode('utf-8'))
                msg_type = json_data['type']
                payload = json_data['payload']
            
            else:  # WIRE protocol
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
                
                if protocol_type == ProtocolType.RPC:
                    if maybe_success:
                        messages = self.business_logic.get_messages(username)
                        user = self.business_logic.get_user(username)
                        
                        # Format response with operation codes
                        response_data = {
                            # Success message
                            "S": "Login successful",
                            # Bulk messages
                            "B": self.wire_protocol.serialize_all_messages(messages),
                            # User stats
                            "V": self.wire_protocol.serialize_user_stats(user.get('log_off_time'), user.get('view_count', 5))
                        }
                        return self.wire_protocol.serialize_success(response_data)
                    else:
                        return self.wire_protocol.serialize_error("Login failed")
                
                else: # for json and wire protocol
                    if client_socket:
                        self.online_users[username] = client_socket
                    
                    if maybe_success:
                        messages = self.business_logic.get_messages(username)
                        user = self.business_logic.get_user(username)
                        
                        if client_socket:
                            client_socket.sendall(self.wire_protocol.serialize_success("Login successful"))
                        if messages:
                            serialized_messages = self.wire_protocol.serialize_all_messages(messages)
                            if client_socket:
                                client_socket.sendall(serialized_messages)
                        
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
                serialized_user_list = self.wire_protocol.serialize_user_list(user_list)
                print(f"Sending user list: {len(serialized_user_list)} bytes")  
                return serialized_user_list
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
            elif msg_type == 'O':  # Log off
                username = self.wire_protocol.deserialize_log_off(payload)
                
                success = self.business_logic.update_log_off_time(username)
                if success:
                    return self.wire_protocol.serialize_success("Log off time updated")
                else:
                    return self.wire_protocol.serialize_error("Failed to update log off time")
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

    # Choose protocol and communication handler
    wire_protocol = WireProtocol()  
    json_protocol = JsonProtocol()
    rpc_protocol = RpcProtocol()
    
    protocol_of_choice = rpc_protocol
    protocol_type = (ProtocolType.RPC if isinstance(protocol_of_choice, RpcProtocol)
                    else ProtocolType.JSON if isinstance(protocol_of_choice, JsonProtocol)
                    else ProtocolType.WIRE)
    
    # Choose communication handler based on protocol
    if isinstance(protocol_of_choice, RpcProtocol):
        comm_handler = RpcHandler()
    else:
        comm_handler = SocketHandler()

    # Initialize controller
    controller = Controller(business_logic, protocol_of_choice)

    # Start the server
    host = os.getenv('CHAT_APP_HOST', '0.0.0.0')
    port = int(os.getenv('CHAT_APP_PORT', '8081'))
    
    try:
        comm_handler.start_server(
            host, 
            port, 
            lambda data, client: controller.handle_incoming_message(data, protocol_type, client)
        )
        threading.Event().wait() # force main thread to block indefinitely
    except KeyboardInterrupt:
        print("\nShutting down server...")
        comm_handler.stop_server()
    except Exception as e:
        print(f"Server error: {e}")
        comm_handler.stop_server()

if __name__ == "__main__":
    start_server()

        