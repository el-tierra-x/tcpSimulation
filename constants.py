INITIATE_CONNECTION_REQUEST = "Connect network"
ACKNOWLEDGMENT = "ACK"
CONNECTION_SUCCESS = "success"
CLOSE_CONNECTION = "close"

PACKET_LOSS_RATE = 0.01
TOTAL_PACKETS = 1000000
MAX_WINDOW_SIZE =  2 ** 16
PORT_NUMBER = 5555
TIMEOUT = 2  # Timeout duration in seconds
TIMEOUT_CHECK_INTERVAL = 0.1
class PACKET_STATUS:
    NOT_SENT = 'not_sent'
    SENT = 'sent'
    ACKED = 'acked'
    TIMEOUT = 'timeout'
