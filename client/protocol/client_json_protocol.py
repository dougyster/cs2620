import json
from datetime import datetime
from typing import Tuple, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) # add parent directory to python path
from interfaces.client_serialization_interface import ClientSerializationInterface

class ClientJsonProtocol(ClientSerializationInterface):
    def __init__(self):
        super().__init__()

    def serialize_message(self, msg_type: str, payload_data: list) -> bytes:
        """Serialize a message with type and payload"""
        if msg_type == 'M':  # Chat message
            data = {
                "type": msg_type,
                "payload": {
                    "sender": payload_data[0],
                    "recipient": payload_data[1],
                    "message": payload_data[2]
                }
            }
        elif msg_type == 'D':  # Delete message
            data = {
                "type": msg_type,
                "payload": {
                    "message": payload_data[0],
                    "timestamp": payload_data[1],
                    "sender": payload_data[2],
                    "receiver": payload_data[3]
                }
            }
        elif msg_type == 'U':  # Delete user
            data = {
                "type": msg_type,
                "payload": {
                    "username": payload_data[0]
                }
            }
        elif msg_type == 'W':  # Update view count
            data = {
                "type": msg_type,
                "payload": {
                    "username": payload_data[0],
                    "new_count": payload_data[1]
                }
            }
        else:
            data = {
                "type": msg_type,
                "payload": payload_data
            }
        
        return json.dumps(data).encode('utf-8')

    def serialize_user_list(self) -> bytes:
        """Serialize a request for user list"""
        data = {
            "type": "G",
            "payload": None
        }
        return json.dumps(data).encode('utf-8')

    def deserialize_message(self, payload: dict) -> Tuple[str, str, str]:
        """Deserialize a chat message"""
        return (
            payload["sender"],
            payload["recipient"],
            payload["message"]
        )

    def deserialize_bulk_messages(self, payload: dict, username: str, messages_by_user: dict) -> List[Tuple[str, str]]:
        """Deserialize bulk messages"""
        messages_to_process = []
        
        for user, messages in payload.items():
            if user not in messages_by_user:
                messages_by_user[user] = []
            
            for msg in messages:
                timestamp = datetime.fromisoformat(msg["timestamp"])
                formatted_msg = f"[{timestamp}] [{msg['sender']} -> {msg['receiver']}]: {msg['message']}"
                messages_by_user[user].append(formatted_msg)
                messages_to_process.append((user, formatted_msg))
        
        return messages_to_process

    def deserialize_user_list(self, payload: list) -> List[str]:
        """Deserialize list of users"""
        print(f"Deserialized json user list: {payload}")
        return payload

    def deserialize_user_stats(self, payload: dict) -> Tuple[str, int]:
        """Deserialize user stats (log-off time and view count)"""
        print(f"Deserialized json user stats: {payload}")
        return (
            payload["log_off_time"],
            payload["view_count"]
        )

    def deserialize_success(self, payload: str) -> str:
        """Deserialize success message"""
        return payload

    def serialize_delete_message(self, message: str, timestamp: str, sender: str, receiver: str) -> bytes:
        """Serialize message deletion request"""
        data = {
            "type": "D",
            "payload": {
                "message": message,
                "timestamp": timestamp,
                "sender": sender,
                "receiver": receiver
            }
        }
        return json.dumps(data).encode('utf-8')
    

    