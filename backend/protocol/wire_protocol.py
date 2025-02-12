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

def serialize_message(msg_type, payload):
    return struct.pack('!BI', ord(msg_type), len(payload)) + payload

def serialize_all_messages(messages_dict: dict) -> bytes:
    """
    Serialize a dictionary of messages where each key is a user and value is a list of message objects.
    Returns a success message ('S') with the serialized messages as payload.
    """
    bulk_payload = b''
    for user, messages in messages_dict.items():
        for msg in messages:
            packed_msg = (
                struct.pack('!H', len(msg['sender'])) + msg['sender'].encode() +
                struct.pack('!H', len(msg['receiver'])) + msg['receiver'].encode() + 
                struct.pack('!I', len(msg['message'])) + msg['message'].encode() + 
                struct.pack('!I', int(msg['timestamp'].timestamp()))  # Convert to integer
            )
            bulk_payload += struct.pack('!I', len(packed_msg)) + packed_msg
    
    bulk_response = serialize_message('B', bulk_payload)
    print(f"Serialized messages response: {bulk_response}")
    return bulk_response