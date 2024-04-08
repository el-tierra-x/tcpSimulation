INITIATE_CONNECTION_REQUEST = "Connect network"
ACKNOWLEDGMENT = "ACK"
CONNECTION_SUCCESS = "success"

PACKET_LOSS_RATE = 0.1
TOTAL_PACKETS = 1000
BUFFER_SIZE = 100
MAX_WINDOW_SIZE = 100
PORT_NUMBER = 5555
TIMEOUT = 5  # Timeout duration in seconds
class PACKET_STATUS:
    NOT_SENT = 'not_sent'
    SENT = 'sent'
    ACKED = 'acked'
    TIMEOUT = 'timeout'
