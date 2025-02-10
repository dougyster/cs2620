from interfaces.db_interface import MongoDBInterface
from datetime import datetime
from interfaces.business_logic_interface import BusinessLogicInterface

class BusinessLogic(BusinessLogicInterface):
    def __init__(self, db_operations: MongoDBInterface):
        self.db_operations = db_operations

    def create_user(self, user_name, user_email, user_password) -> bool:
        user_data = {
            "user_name": user_name,
            "user_email": user_email,
            "user_password": user_password,
            "view_count": 5 # default view count of 5
        }
        try:
            result = self.db_operations.insert("users", user_data)
            return result is not None
        except Exception:
            return False

    def get_user(self, user_email) -> dict:
        query = {"user_email": user_email}
        return self.db_operations.read("users", query) or {}

    def send_message(self, sender, receiver, message) -> bool:
        message_data = {
            "sender": sender,
            "receiver": receiver,
            "message": message,
            "timestamp": datetime.now()
        }
        try:
            result = self.db_operations.insert("messages", message_data)
            return result is not None
        except Exception:
            return False
    
    # this needs to be constantly called to update the view count via websocket?
    def get_messages(self, sender, receiver) -> list:
        messages = []
        
        # add all messages from sender to receiver
        query = {"sender": sender, "receiver": receiver}
        sender_messages = self.db_operations.read("messages", query) or []
        messages.extend(sender_messages)

        # add all messages from receiver to sender
        query = {"sender": receiver, "receiver": sender}
        receiver_messages = self.db_operations.read("messages", query) or []
        messages.extend(receiver_messages)

        # sort by timestamp
        return sorted(messages, key=lambda x: x["timestamp"])
    
    def update_view_count(self, view_count, user_email) -> bool:
        query = {"user_email": user_email}
        update_values = {"view_count": view_count}
        try:
            result = self.db_operations.update("users", query, update_values)
            return result is not None and result > 0
        except Exception:
            return False
