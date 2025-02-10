import struct
import json
from protocol.message_types import MessageType

class WireProtocol:
    HEADER_SIZE = 8  # 4 bytes for length, 4 bytes for message type
    
    @staticmethod
    def pack_message(msg_type: MessageType, payload: dict) -> bytes:
        payload_bytes = json.dumps(payload).encode('utf-8')
        header = struct.pack('!II', len(payload_bytes), msg_type.value)
        return header + payload_bytes
    
    @staticmethod
    def unpack_message(data: bytes) -> tuple[MessageType, dict]:
        msg_length, msg_type = struct.unpack('!II', data[:WireProtocol.HEADER_SIZE])
        payload = json.loads(data[WireProtocol.HEADER_SIZE:WireProtocol.HEADER_SIZE + msg_length])
        return MessageType(msg_type), payload
