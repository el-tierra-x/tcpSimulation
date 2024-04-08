import zmq
import time
import random
import heapq  # Import heapq for heap operations
from collections import deque, defaultdict
import threading
import constants

from constants import PACKET_STATUS

# Constants and global variables setup

connected = False
socket = None
context = zmq.Context()
window_size = 1
last_max_window_size = None
send_base = 0
send_buffer = []
heapq.heapify(send_buffer) 
next_seq_num = 0
total_recieved_segments = 0
last_ack = 0
time_heap = []  # Heap to manage packet timeouts
heapq.heapify(time_heap)
packet_status = defaultdict(lambda: PACKET_STATUS.NOT_SENT)
send_lock = threading.Lock()
is_packet_dropped = False



def simulate_packet_loss():
    """Simulates a 1% chance of packet loss."""
    return random.random() < constants.PACKET_LOSS_RATE

def connect(ip_address:str, port:str):
    global connected, socket, context
    address = f'tcp://{ip_address}:{port}'
    if(connected):
        print("Already connected")
        return True
    # socket = context.socket(zmq.REQ)
    # socket.connect(address)
    
    # Setup Dealer socket
    socket = context.socket(zmq.DEALER)
    socket.connect(address)
    
    if socket:
        connected = True
        print("Connection established")
        return True
    else:
        print("Connection failed")
        return False

def close():
    global connected, socket, context
    if not connected:
        print("Not connected")
        return
    socket.send_string("close")
    message = socket.recv_string()  # Expecting a confirmation message
    socket.close()
    context.term()  # Terminate the ZMQ context
    connected = False
    socket = None
    print("Connection closed")

def initiate_connection():
    global socket
    # ip_address = input("Enter the server IP address: ")
    # port = input("Enter the server port: ")
    ip_address = "127.0.0.1"
    port = "5555"
    if not connect(ip_address, port):
        return False
    socket.send_string(constants.INITIATE_CONNECTION_REQUEST)
    message = socket.recv_string()
    if socket and message == constants.CONNECTION_SUCCESS:
        print("Connection successfully established")
        return True
    else:
        print("Connection failed")
        return False

def check_timeouts_and_retransmit():
    """Check for timeouts and retransmit packets as necessary."""
    global packet_status, time_heap, window_size, connected, send_base, is_packet_dropped
    
    is_dropped = False
    while connected:
        current_time = time.time()
        while time_heap and time_heap[0][0] < current_time:
            _, seq_num = heapq.heappop(time_heap)  # Pop the packet with the earliest timeout
            if packet_status[seq_num] == PACKET_STATUS.SENT:  # Check if it hasn't been acknowledged
                print(f"Timeout for packet {seq_num}, retransmitting...")
                window_size = max(window_size - 1, 1)  # Reduce window size on timeout
                send_packet(seq_num)  # Retransmit packet
                is_packet_dropped = True
                is_dropped = True
        if is_dropped:
            is_dropped = False
            update_window_size(False)
            
        # time.sleep(3)  # Check timeouts periodically
    return

def update_window_size(increase:bool):
    global window_size, last_max_window_size, is_packet_dropped
    
    if increase:
        if is_packet_dropped:
            window_size += 1
        else:
            window_size = min(window_size * 2, constants.MAX_WINDOW_SIZE)
    else:
        window_size = max(window_size // 2, 1)

def receive_acknowledgments():
    global packet_status, connected, last_ack, send_base, total_recieved_segments, window_size
    
    while connected:
        try:
            while True:
                message = socket.recv_string(zmq.NOBLOCK)
                ack_seq_num = int(message.split(':')[1])
                print(f"Received ack for packet {ack_seq_num}")
                
                with send_lock:
                    if packet_status[ack_seq_num] == PACKET_STATUS.SENT:
                        packet_status[ack_seq_num] = PACKET_STATUS.ACKED
                        total_recieved_segments += 1
                        
                        if ack_seq_num > last_ack:
                            last_ack = ack_seq_num
                            
                        while send_base in packet_status and packet_status[send_base] == PACKET_STATUS.ACKED:
                            send_base += 1
                        update_window_size(True)

        except zmq.Again:
            pass  # No message received
        time.sleep(0.1)  # Reduce CPU usage

def send_packet(seq_num, is_retransmission=False):
    global send_buffer, send_lock
    priority = 0 if is_retransmission else 1  # Retransmissions have higher priority
    packet_data = (priority, seq_num)
    heapq.heappush(send_buffer, packet_data)
        

def send_thread_function():
    global connected, socket
    while connected:
        if send_buffer:
            with send_lock:
                _, seq_num = heapq.heappop(send_buffer)
                if packet_status[seq_num] != PACKET_STATUS.ACKED:  # Check to avoid sending acked packets
                    if not simulate_packet_loss():
                        print(f"Sending packet {seq_num}")
                        socket.send_string(f"DATA:{seq_num}")
                    packet_status[seq_num] = PACKET_STATUS.SENT
                    timeout = time.time() + constants.TIMEOUT
                    heapq.heappush(time_heap, (timeout, seq_num))
            time.sleep(0.1)  # Prevent spamming the network too fast; adjust based on your requirements


def sliding_window_protocol():
    global packet_status, next_seq_num, window_size, last_ack, total_recieved_segments, send_base
    total_packets = constants.TOTAL_PACKETS
    
    
     # Start thread for receiving acknowledgments
    ack_thread = threading.Thread(target=receive_acknowledgments)
    ack_thread.start()

    # Start thread for checking timeouts and potential retransmits
    timeout_thread = threading.Thread(target=check_timeouts_and_retransmit)
    timeout_thread.start()

    while total_recieved_segments <= constants.TOTAL_PACKETS:
        while next_seq_num < (send_base + window_size) and next_seq_num < total_packets:
            print(next_seq_num , window_size, send_base)
            send_packet(next_seq_num)
            next_seq_num += 1

    # Ensure threads are joined back before exiting
    ack_thread.join()
    timeout_thread.join()

def __main__():
    global send_thread
    if initiate_connection():
        send_thread = threading.Thread(target=send_thread_function)
        send_thread.start()
        sliding_window_protocol()
    close()
    send_thread.join()


if __name__ == '__main__':
    __main__()
