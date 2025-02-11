import struct
import json

def serialize_success(message: str) -> bytes:
    """
    Serializes a success message with format:
    - 1 byte for message type ('S')
    - 4 bytes for payload length
    - Variable length UTF-8 encoded message
    """
    msg_type = ord('S')  # Convert 'S' to its ASCII value
    payload = message.encode('utf-8')
    header = struct.pack('!BI', msg_type, len(payload))
    return header + payload


def serialize_error(message: str) -> bytes:
    """
    Serializes an error message with format:
    - 1 byte for message type ('E')
    - 4 bytes for payload length
    - Variable length UTF-8 encoded message
    """
    msg_type = ord('E')  # Convert 'E' to its ASCII value
    payload = message.encode('utf-8')
    header = struct.pack('!BI', msg_type, len(payload))
    return header + payload
    
    
