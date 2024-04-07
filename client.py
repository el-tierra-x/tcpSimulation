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
send_base = 0
next_seq_num = 0
total_recieved_segments = 0
last_ack = 0
time_heap = []  # Heap to manage packet timeouts
packet_status = defaultdict(lambda: PACKET_STATUS.NOT_SENT)
send_lock = threading.Lock()



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
    global packet_status, time_heap, window_size, connected, send_base
    while connected:
        
        with send_lock:
            current_time = time.time()
            while time_heap and time_heap[0][0] < current_time:
                _, seq_num = heapq.heappop(time_heap)  # Pop the packet with the earliest timeout
                if packet_status[seq_num] == PACKET_STATUS.SENT:  # Check if it hasn't been acknowledged
                    print(f"Timeout for packet {seq_num}, retransmitting...")
                    window_size = max(window_size - 1, 1)  # Reduce window size on timeout
                    send_packet(seq_num)  # Retransmit packet
        time.sleep(5)  # Check timeouts periodically
    return

def receive_acknowledgments():
    global packet_status, connected, last_ack, send_base, total_recieved_segments, window_size
    
    while connected:
        try:
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
                        window_size = min(window_size + 1, constants.MAX_WINDOW_SIZE)  # Adjust growth rate as needed
                        
        except zmq.Again:
            pass  # No message received
        time.sleep(0.1)  # Reduce CPU usage

        
# def receive_acknowledgments():
#     """Non-blocking receive for acknowledgments from the server."""
#     global packet_status, connected, window_size, last_ack, total_recieved_segments, socket, send_base
#     poller = zmq.Poller()
#     poller.register(socket, zmq.POLLIN)
    
#     while connected:
#         socks = dict(poller.poll(timeout=1000))
#         if socket in socks and socks[socket] == zmq.POLLIN:
#             message = socket.recv_string(flags=zmq.NOBLOCK)
#             if message:
#                 ack_seq_num = int(message.split(':')[1])  # Extract seq_num from message
#                 with send_lock:
#                     if packet_status[ack_seq_num] == PACKET_STATUS.SENT:
#                         packet_status[ack_seq_num] = PACKET_STATUS.ACKED
#                         total_recieved_segments += 1
#                         print(f"Packet {ack_seq_num} acknowledged")
#                         # Update window size and send base as needed
#                         if ack_seq_num == send_base:
#                             send_base += 1
#                             # Adjust window size here if needed
#                         window_size = min(window_size * 2, constants.MAX_WINDOW_SIZE)
#         time.sleep(0.2)  # Brief pause to prevent tight loop

def send_packet(seq_num):
    """Enhanced send_packet to not block if waiting for acks."""
    global packet_status, time_heap, send_lock, send_base, last_ack, socket, window_size
    
    with send_lock:
        if packet_status[seq_num] != PACKET_STATUS.ACKED and seq_num <= send_base + window_size:  # Only send if not already acknowledged
            
            if simulate_packet_loss():
                print(f"Simulating packet loss for sequence number: {seq_num}")
                # send_base = min(next_seq_num - 1, last_ack)
                
            else:
                print(f"Packet {seq_num} sent")
                socket.send_string(f"DATA:{seq_num}", zmq.NOBLOCK)  # Use NOBLOCK if necessary
            
            packet_status[seq_num] = PACKET_STATUS.SENT
            # Record the timeout for this packet
            timeout = time.time() + constants.TIMEOUT
            heapq.heappush(time_heap, (timeout, seq_num))


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
            print(next_seq_num , send_base, last_ack,window_size)
            send_packet(next_seq_num)
            
            next_seq_num += 1
            time.sleep(0.2)

    # Ensure threads are joined back before exiting
    ack_thread.join()
    timeout_thread.join()

def __main__():
    if initiate_connection():
        sliding_window_protocol()
    close()

if __name__ == '__main__':
    __main__()
