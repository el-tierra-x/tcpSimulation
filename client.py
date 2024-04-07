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
window_size = 4
packet_loss_rate = 0.2
time_heap = []  # Heap to manage packet timeouts
packet_status = defaultdict(lambda: 'not_sent')
send_lock = threading.Lock()

def connect(ip_address:str, port:str):
    global connected, socket, context
    address = f'tcp://{ip_address}:{port}'
    if(connected):
        print("Already connected")
        return True
    socket = context.socket(zmq.REQ)
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
    ip_address = input("Enter the server IP address: ")
    port = input("Enter the server port: ")
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

def send_packet(seq_num):
    global packet_status, time_heap
    with send_lock:
        print(f"Packet {seq_num} sent")
        socket.send_string(f"DATA:{seq_num}")
        packet_status[seq_num] = PACKET_STATUS.SENT
        # Calculate and push the timeout for this packet into the heap
        timeout = time.time() + constants.TIMEOUT
        heapq.heappush(time_heap, (timeout, seq_num))

def check_timeouts_and_retransmit():
    """Check for timeouts and retransmit packets as necessary."""
    global packet_status, time_heap
    while connected:
        current_time = time.time()
        while time_heap and time_heap[0][0] < current_time:
            _, seq_num = heapq.heappop(time_heap)  # Pop the packet with the earliest timeout
            if packet_status[seq_num] == PACKET_STATUS.SENT:  # Check if it hasn't been acknowledged
                print(f"Timeout for packet {seq_num}, retransmitting...")
                send_packet(seq_num)  # Retransmit packet
        time.sleep(1)  # Check timeouts periodically
        
def receive_acknowledgments():
    """Non-blocking receive for acknowledgments from the server."""
    global packet_status, connected
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    
    while connected:
        socks = dict(poller.poll(timeout=1000))  # Adjust timeout as needed
        if socket in socks and socks[socket] == zmq.POLLIN:
            message = socket.recv_string(flags=zmq.NOBLOCK)
            ack_seq_nums = message.split()  # Assuming the server sends acks as a space-separated list of seq nums
            with send_lock:
                for seq_num in ack_seq_nums:
                    if seq_num.isdigit() and int(seq_num) in packet_status:
                        packet_status[int(seq_num)] = PACKET_STATUS.ACKED
                        print(f"Packet {seq_num} acknowledged")
        time.sleep(0.1)  # Brief pause to prevent tight loop

def send_packet(seq_num):
    """Enhanced send_packet to not block if waiting for acks."""
    global packet_status, time_heap
    with send_lock:
        if packet_status[seq_num] != 'acknowledged':  # Only send if not already acknowledged
            print(f"Packet {seq_num} sent")
            socket.send_string(f"DATA {seq_num}", zmq.NOBLOCK)  # Use NOBLOCK if necessary
            packet_status[seq_num] = 'sent'
            # Record the timeout for this packet
            timeout = time.time() + constants.TIMEOUT
            heapq.heappush(time_heap, (timeout, seq_num))


def sliding_window_protocol():
    global packet_status
    seq_num = 0
    total_packets = constants.TOTAL_PACKETS
    
     # Start thread for receiving acknowledgments
    ack_thread = threading.Thread(target=receive_acknowledgments)
    ack_thread.start()

    # Start thread for checking timeouts and potential retransmits
    timeout_thread = threading.Thread(target=check_timeouts_and_retransmit)
    timeout_thread.start()

    while any(status != PACKET_STATUS.ACKED for status in packet_status.values()) or seq_num < total_packets:
        with send_lock:
            if seq_num < total_packets:
                seq_num += 1
                send_packet(seq_num)

        time.sleep(2)  # Main loop delay to prevent too much CPU usage

    # Ensure threads are joined back before exiting
    ack_thread.join()
    timeout_thread.join()

def __main__():
    if initiate_connection():
        sliding_window_protocol()
    close()

if __name__ == '__main__':
    __main__()
