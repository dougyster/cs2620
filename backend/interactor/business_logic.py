import sys
import os
import bcrypt  # Add this import at the top

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.interfaces.db_interface import MongoDBInterface
from datetime import datetime
from backend.interfaces.business_logic_interface import BusinessLogicInterface

class BusinessLogic(BusinessLogicInterface):
    def __init__(self, db_operations: MongoDBInterface):
        self.db_operations = db_operations

    def create_user(self, user_name, user_password) -> bool:
        # Hash the password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user_password.encode('utf-8'), salt)
        
        user_data = {
            "user_name": user_name,
            "user_password": hashed_password,  # Store the hashed password
            "view_count": 5 # default view count of 5
        }

        print(f"Inserting user: {user_data}")
        result = self.db_operations.insert("users", user_data)
        return result
    
    def delete_user(self, user_name) -> bool:
        query = {"user_name": user_name}
        result = self.db_operations.delete("users", query)
        if result is not None and result > 0:
            print(f"User deleted: {user_name}")
            return True
        else:
            print(f"User deletion failed: {user_name}")
            return False

    def get_user(self, user_name) -> dict:
        query = {"user_name": user_name}
        return self.db_operations.read("users", query) or {}
    
    def get_all_users(self) -> list:
        docs = self.db_operations.read("users", {}) or []
        return [doc["user_name"] for doc in docs]
    
    def login_user(self, user_name, user_password) -> bool:
        print(f"Logging in user: {user_name}")  # Removed password from print for security
        query = {"user_name": user_name}
        user_doc = self.db_operations.read("users", query)
        
        if len(user_doc) == 0:
            return False
            
        # Compare the hashed passwords
        stored_password = user_doc[0].get("user_password")
        if not bcrypt.checkpw(user_password.encode('utf-8'), stored_password):
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
    def get_messages(self, user) -> dict:
        messages_dict = {}
        
        # Query for messages where the user is the sender
        query = {"sender": user}
        sent_messages = self.db_operations.read("messages", query) or []
        
        for message in sent_messages:
            receiver = message["receiver"]
            if receiver not in messages_dict:
                messages_dict[receiver] = []
            messages_dict[receiver].append(message)
        
        # Query for messages where the user is the receiver
        query = {"receiver": user}
        received_messages = self.db_operations.read("messages", query) or []
        
        for message in received_messages:
            sender = message["sender"]
            if sender not in messages_dict:
                messages_dict[sender] = []
            messages_dict[sender].append(message)
        
        # Sort messages for each user by timestamp
        for user in messages_dict:
            messages_dict[user] = sorted(messages_dict[user], key=lambda x: x["timestamp"])
        
        print(f"Messages: {messages_dict}")
        return messages_dict
    
    def delete_message(self, message:str, timestamp:str, sender:str, receiver:str) -> bool:
        from datetime import datetime
        try:
            # Parse the timestamp string to datetime
            timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            
            # Create a query with timestamp range to account for millisecond differences
            # This will match messages within the same second
            from datetime import timedelta
            start_time = timestamp_dt
            end_time = timestamp_dt + timedelta(seconds=1)
            
            query = {
                "message": message,
                "sender": sender,
                "receiver": receiver,
                "timestamp": {
                    "$gte": start_time,
                    "$lt": end_time
                }
            }
            
            result = self.db_operations.delete("messages", query)
            if result is not None and result > 0:
                print(f"Message deleted: {message} from {sender} to {receiver} at {timestamp}")
                return True
            else:
                print(f"Message failed to delete: {message} from {sender} to {receiver} at {timestamp}")
                return False
        except Exception as e:
            print(f"Error deleting message: {e}")
            return False
        
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
    print(business_logic.get_messages("John Doe"))
    print(business_logic.update_view_count(10, "john.doe@example.com"))

