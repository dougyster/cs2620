import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.interfaces.db_interface import MongoDBInterface
from datetime import datetime
from backend.interfaces.business_logic_interface import BusinessLogicInterface

class BusinessLogic(BusinessLogicInterface):
    def __init__(self, db_operations: MongoDBInterface):
        self.db_operations = db_operations

    def create_user(self, user_name, user_password) -> bool:
        user_data = {
            "user_name": user_name,
            "user_password": user_password,
            "view_count": 5 # default view count of 5
        }

        print(f"Inserting user: {user_data}")
        result = self.db_operations.insert("users", user_data)
        return result


    def get_user(self, user_name) -> dict:
        query = {"user_name": user_name}
        return self.db_operations.read("users", query) or {}
    
    def login_user(self, user_name, user_password) -> bool:
        print(f"Logging in user: {user_name} with password: {user_password}")
        query = {"user_name": user_name}
        user_doc = self.db_operations.read("users", query)
        print(f"User doc: {user_doc}")
        if user_doc is None:
            return False
        if user_doc[0].get("user_password") != user_password:
            return False
        print(f"Login successful for user: {user_name}")
        return True

    def send_message(self, sender, receiver, message) -> bool:
        check_receiver = self.get_user(receiver)
        if check_receiver is None:
            print(f"Receiver {receiver} not found")
            return False
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
        print(f"Messages: {messages}")
        return sorted(messages, key=lambda x: x["timestamp"])
    
    # def update_online_status(self, user_name, online_status) -> bool:
    #     query = {"user_name": user_name}
    #     update_values = {"online": online_status}
    #     try:
    #         result = self.db_operations.update("users", query, update_values)
    #         print(f"Updated online status for user {user_name} to {online_status}")
    #         return result is not None and result > 0
    #     except Exception:
    #         return False
        
    def update_view_count(self, view_count, user_email) -> bool:
        query = {"user_email": user_email}
        update_values = {"view_count": view_count}
        try:
            result = self.db_operations.update("users", query, update_values)
            return result is not None and result > 0
        except Exception:
            return False
        
if __name__ == "__main__":
    from backend.database.mongo_operations import MongoOperation
    business_logic = BusinessLogic(MongoOperation())
    # print(business_logic.create_user("John Doe", "john.doe@example.com", "password123"))
    # print(business_logic.get_user("john.doe@example.com"))
    # print(business_logic.send_message("John Doe", "Jane Smith", "Hello, how are you?"))
    print(business_logic.get_messages("John Doe", "Jane Smith"))
    print(business_logic.update_view_count(10, "john.doe@example.com"))

