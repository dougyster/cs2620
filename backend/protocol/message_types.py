from enum import Enum

class MessageType(Enum):
    # User operations
    CREATE_USER = 1
    GET_USER = 2
    
    # Message operations
    SEND_MESSAGE = 3
    GET_MESSAGES = 4
    
    # View count operations
    UPDATE_VIEW_COUNT = 5
    
    # Response types
    SUCCESS = 6
    ERROR = 7
