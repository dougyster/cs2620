# importing interfaces
from interfaces.business_logic_interface import BusinessLogicInterface
from interfaces.db_interface import MongoDBInterface

# importing implementations
from interactor.business_logic import BusinessLogic
from database.mongo_operations import MongoOperation

# importing protocol
from protocol.wire_protocol import WireProtocol
from protocol.message_types import MessageType

import socket
class Controller:
    def __init__(self, business_logic: BusinessLogicInterface):
        self.business_logic = business_logic

    def handle_incoming_message(self, data: bytes):
        msg_type, payload = WireProtocol.unpack_message(data)

        # maybe these functions should return a truthy value to indicate success?
        if msg_type == MessageType.CREATE_USER:
            maybe_success = self.business_logic.create_user(payload["user_name"], payload["user_email"], payload["user_password"])
            if maybe_success:
                return WireProtocol.pack_message(MessageType.SUCCESS, {"message": "User created successfully"})
            else:
                return WireProtocol.pack_message(MessageType.ERROR, {"message": "User creation failed"})
        elif msg_type == MessageType.GET_USER:
            maybe_user = self.business_logic.get_user(payload["user_email"])
            if maybe_user:
                return WireProtocol.pack_message(MessageType.SUCCESS, maybe_user)
            else:
                return WireProtocol.pack_message(MessageType.ERROR, {"message": "User not found"})
        elif msg_type == MessageType.SEND_MESSAGE:
            maybe_success = self.business_logic.send_message(payload["sender"], payload["receiver"], payload["message"])
            if maybe_success:
                return WireProtocol.pack_message(MessageType.SUCCESS, {"message": "Message sent successfully"})
            else:
                return WireProtocol.pack_message(MessageType.ERROR, {"message": "Message sending failed"})
        elif msg_type == MessageType.GET_MESSAGES:
            maybe_messages = self.business_logic.get_messages(payload["sender"], payload["receiver"])
            if maybe_messages:
                return WireProtocol.pack_message(MessageType.SUCCESS, maybe_messages)
            else:
                return WireProtocol.pack_message(MessageType.ERROR, {"message": "No messages found"})
        elif msg_type == MessageType.UPDATE_VIEW_COUNT:
            maybe_success = self.business_logic.update_view_count(payload["view_count"], payload["user_email"])
            if maybe_success:
                return WireProtocol.pack_message(MessageType.SUCCESS, {"message": "View count updated successfully"})
            else:
                return WireProtocol.pack_message(MessageType.ERROR, {"message": "View count update failed"})
        else:
            return WireProtocol.pack_message(MessageType.ERROR, {"message": "Invalid message type"})
        

def start_server():
    # initialize the business logic
    business_logic = BusinessLogic(MongoOperation())
    controller = Controller(business_logic)

    # start the server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 8080))
    server.listen(5)
    print("Server is running on localhost:8080")

    # handle a single client at a time
    try:
        while True:
            client_socket, client_address = server.accept()
            print(f"Connection established with {client_address}")

            data = client_socket.recv(1024)
            response = controller.handle_incoming_message(data)
            client_socket.sendall(response)
            client_socket.close()
    finally:
        server.close()

if __name__ == "__main__":
    start_server()

        