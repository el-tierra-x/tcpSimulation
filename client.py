import zmq
import time
import random
import heapq
from collections import deque, defaultdict, Counter
import threading
import constants
import pandas as pd
import matplotlib.pyplot as plt

from constants import PACKET_STATUS

# Constants and global variables setup
connected = False
socket = None
context = zmq.Context()
window_size = 1
window_size_lock = threading.Lock()
last_max_window_size = 1
is_packet_dropped = False
send_base = 0
send_buffer = []
retransmit_buffer = []
heapq.heapify(send_buffer)
next_seq_num = 1
total_recieved_segments = 0
last_ack = 0
time_heap = []  # Heap to manage packet timeouts
heapq.heapify(time_heap)
packet_status = defaultdict(lambda: PACKET_STATUS.NOT_SENT)
send_lock = threading.Lock()
num_retransmissions = Counter()

window_size_df = pd.DataFrame(columns=['Time', 'WindowSize'])

#simulating packet loss
def simulate_packet_loss():
    """Simulates a 1% chance of packet loss."""
    return random.random() < constants.PACKET_LOSS_RATE

def increment_sequence_number(seq_num):      
    return (seq_num + 1)
      
    # return (seq_num + 1) % constants.MAX_WINDOW_SIZE  # 2^16

#reporting window size 
def report_window_size():
#   while connected:
    global window_size, window_size_df
    current_time = time.time()
    print(f"Current window size: {window_size}")
    new_row = {'Time': current_time, 'WindowSize': window_size}
    window_size_df = window_size_df._append(new_row, ignore_index=True)

    
def plot_window_size():
    global window_size_df
    # Convert 'Time' to a more readable format by subtracting the start time
    start_time = window_size_df['Time'].min()
    window_size_df['Time'] -= start_time
    
    plt.figure(figsize=(10, 6))
    plt.plot(window_size_df['Time'], window_size_df['WindowSize'], marker='o', linestyle='-')
    plt.title('Window Size Over Time')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Window Size')
    plt.grid(True)
    plt.show()  
        
#initial connection
def connect(ip_address: str, port: str, retries=5, retry_delay=5):
    global connected, socket, context
    address = f"tcp://{ip_address}:{port}"
    attempt = 0
    while not connected and attempt < retries:
        try:
            if socket is None:
                socket = context.socket(zmq.DEALER)
            socket.connect(address)
            # The connection is not actually established here in ZMQ until a message is sent
            print(f"Attempt {attempt + 1}: Trying to connect to {address}...")
            # Try initiating connection by sending a connection request
            socket.send_string(constants.INITIATE_CONNECTION_REQUEST)
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            if poller.poll(5000):  # 5-second for the server to reply
                message = socket.recv_string()
                if message == constants.CONNECTION_SUCCESS:
                    connected = True
                    print("Connection successfully established")
                    return True
            attempt += 1
            time.sleep(retry_delay)
        except zmq.ZMQError as e:
            print(f"Connection attempt failed: {e}")
            attempt += 1
            socket.close()
            socket = None  # Reset socket for a fresh connection attempt
            time.sleep(retry_delay)
    print("Connection failed after retries")
    return False

#close connection on complete
def close():
    global connected, socket, context
    if not connected:
        print("Not connected")
        return
    socket.send_string("close")
    # message = socket.recv_string()  # Expecting a confirmation message
    socket.close()
    context.term()  # Terminate the ZMQ context
    connected = False
    socket = None
    print("Connection closed")

def initiate_connection():
    global socket
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

"""Check for timeouts and retransmit packets as necessary."""
def check_timeouts_and_retransmit():
    global packet_status, time_heap, window_size, connected, send_base, is_packet_dropped, num_retransmissions
    packet_dropped = False
  
    while connected:
        # print("Checking timeouts...")
        print(packet_status[send_base])
        if total_recieved_segments == constants.TOTAL_PACKETS-1:
            break
          
        current_time = time.time()
        while time_heap and time_heap[0][0] < current_time:
            _, seq_num = heapq.heappop(time_heap)  # Pop the packet with the earliest timeout
            if packet_status[seq_num] == PACKET_STATUS.SENT:  # Check if it hasn't been acknowledged
                print(f"Timeout for packet {seq_num}, retransmitting...")
                if (num_retransmissions.get(seq_num, 0)):
                    num_retransmissions[seq_num] += 1
                else:
                    num_retransmissions[seq_num] = 1
                    
                send_packet(seq_num, is_retransmission=True)  # Retransmit packet
                is_packet_dropped = True
                packet_dropped = True
        if packet_dropped:
            with window_size_lock:
              update_window_size(False)
            packet_dropped = False
        
        time.sleep(constants.TIMEOUT_CHECK_INTERVAL)  # Check timeouts periodically

#update window size based on packet drop
def update_window_size(increase:bool, is_slow_restart=False):
    global window_size, last_max_window_size, is_packet_dropped
    
    if increase:
        if is_packet_dropped and not is_slow_restart:
            window_size += 1
        else:
            window_size = min(window_size * 2, constants.MAX_WINDOW_SIZE)
    else:
        window_size = max(window_size // 2, 1)
    report_window_size()

def receive_acknowledgments():
    global packet_status, connected, last_ack, send_base, total_recieved_segments, window_size, socket, is_packet_dropped
    
    is_recieved = False
    while connected:
        # print("Checking acknowledgments...")
        try:
          while True:
            if total_recieved_segments == constants.TOTAL_PACKETS-1:
              return
          
            message = socket.recv_string(flags=zmq.NOBLOCK)
            
            if message == constants.CLOSE_CONNECTION:
              return
            
            ack_seq_num = int(message.split(':')[1])
            print(f"Received ack for packet {ack_seq_num}")

            with send_lock:
                if packet_status[ack_seq_num] == PACKET_STATUS.SENT:
                    packet_status[ack_seq_num] = PACKET_STATUS.ACKED
                    total_recieved_segments += 1

                    if ack_seq_num > last_ack:
                        last_ack = ack_seq_num
                    is_recieved = True
                    
                    while send_base in packet_status and packet_status[send_base] == PACKET_STATUS.ACKED:
                        print("here")
                        send_base += 1
                        # packet_status[send_base-1] = PACKET_STATUS.NOT_SENT
                        
                        # send_base = (send_base + 1) % constants.MAX_WINDOW_SIZE

                    # with window_size_lock:
                    #   update_window_size(True)
                elif packet_status[ack_seq_num] == PACKET_STATUS.ACKED:
                    is_packet_dropped = False
                    with window_size_lock:
                      update_window_size(True, True)
                    
                    

        except zmq.Again:
          if is_recieved:
            is_recieved = False
            with window_size_lock:
              update_window_size(True)
          pass  # No message received, continue the loop
        # time.sleep(0.1)  # Reduce CPU usage

def send_packet(seq_num, is_retransmission=False):
    global send_buffer, send_lock
    priority = 0 if is_retransmission else 1  # Retransmissions have higher priority
    packet_data = (priority, seq_num)
    with send_lock:
        if is_retransmission:
            heapq.heappush(retransmit_buffer, packet_data)
        else:
            heapq.heappush(send_buffer, packet_data)

def send_thread_function():
    global connected, socket, send_base, window_size, packet_status, send_lock

    while connected:
        with send_lock:
            current_time = time.time()
            if retransmit_buffer:
                while retransmit_buffer and packet_status[retransmit_buffer[0][1]] != PACKET_STATUS.ACKED:
                    _, seq_num = retransmit_buffer[0]
                    if packet_status[seq_num] == PACKET_STATUS.SENT:
                        heapq.heappop(retransmit_buffer)
                        if not simulate_packet_loss():
                            print(f"Sending packet {seq_num}")
                            socket.send_string(f"DATA:{seq_num}")
                        # Update the timeout for this packet
                        else:
                            print(f"Simulating packet loss for packet {seq_num}")
                        timeout = current_time + constants.TIMEOUT
                        heapq.heappush(time_heap, (timeout, seq_num))
                        packet_status[seq_num] = PACKET_STATUS.SENT
            else: 
                while send_buffer and packet_status[send_buffer[0][1]] != PACKET_STATUS.ACKED:
                    _, seq_num = send_buffer[0]  # Peek at the top packet without popping it

                    # Check if the packet is within the window and ready to send
                    if send_base <= seq_num <= send_base + window_size:
                        heapq.heappop(send_buffer)  # Now pop the packet since it's being processed
                        if not simulate_packet_loss():
                            print(f"Sending packet {seq_num}")
                            socket.send_string(f"DATA:{seq_num}")
                            # Update the timeout for this packet
                        else:
                            print(f"Simulating packet loss for packet {seq_num}")
                        timeout = current_time + constants.TIMEOUT
                        heapq.heappush(time_heap, (timeout, seq_num))
                        packet_status[seq_num] = PACKET_STATUS.SENT
                    else:
                        break  # Exit if the top packet is outside the window
        time.sleep(0.1)

def sliding_window_protocol():
    global packet_status, next_seq_num, window_size, last_ack, total_recieved_segments, send_base
    total_packets = constants.TOTAL_PACKETS

    # Start thread for receiving acknowledgments
    ack_thread = threading.Thread(target=receive_acknowledgments)
    ack_thread.start()

    # Start thread for checking timeouts and potential retransmits
    timeout_thread = threading.Thread(target=check_timeouts_and_retransmit)
    timeout_thread.start()


    while total_recieved_segments < total_packets -1:
        print(total_recieved_segments, window_size, send_base , next_seq_num, len(send_buffer))
        while next_seq_num <= (send_base + window_size) and  next_seq_num <= constants.TOTAL_PACKETS:
            
            send_packet(next_seq_num)
            next_seq_num = increment_sequence_number(next_seq_num)
            if send_base == 0 and total_recieved_segments > 500000:
                ack_thread.join()
                timeout_thread.join()
                
                exit()
        time.sleep(0.1)  # Reduce CPU usage
        # print(f"Total received segments: {total_recieved_segments} , window size: {window_size} , send base: {send_base}, next seq num: {next_seq_num}")

    # Ensure threads are joined back before exiting
    ack_thread.join()
    timeout_thread.join()
    
    close()
    
def __main__():
    global send_thread
    if initiate_connection():
        send_thread = threading.Thread(target=send_thread_function)
        send_thread.start()
        sliding_window_protocol()
    # close()
    send_thread.join()
    r = Counter(num_retransmissions.values())
    
    print("Total retransmissions:")
    print(f"Retransmissions 1: {r[1]}")
    print(f"Retransmissions 2: {r[2]}")
    print(f"Retransmissions 3: {r[3]}")
    print(f"Retransmissions 4: {r[4]}")
    
    
    plot_window_size()

if __name__ == '__main__':
    __main__()
