import zmq
import time
import random
from collections import deque

import threading

import constants 



''' 
    Global variables from tracking connection requests , packet loss and packet loss rate 
'''
connected = False
seq_num = 0
socket = None
packet_loss = False

 
def connect(ip_address:str, port:str):
    global connected, socket
    
    address = f'tcp://{ip_address}:{port}'
    
    if(connected):
        print("Already connected")
        return True

    context = zmq.Context()
    socket = context.socket(zmq.REQ)  # REQ socket for requests
    socket.connect(address)
    
    if socket:
        connected = True
        print("Connection established")
        return True
    
    else:
        print("Connection failed")
        return False
    
    
    
def close():
    global connected, socket
    
    if not connected:
        print("Not connected")
        return

    socket.send(b"close")
    socket.close()
    connected = False
    socket = None
    
    print("Connection closed")
    



def initiate_connection():
    global socket
    
    ip_address = input("Enter the server IP address: ")
    port = input("Enter the server port: ")
    
    if not connect(ip_address, port):
        return False
    
    # Send connection request
    socket.send(bytes(constants.INITIATE_CONNECTION_REQUEST, 'utf-8'))
    
    # Wait for acknowledgment
    message = socket.recv()
    recieved_msg = message.decode()
    
    if socket and recieved_msg == constants.CONNECTION_SUCCESS:
        print("Connection established")
        return socket
    
    else:
        print("Connection failed")
        return False
    

def handle_acknowledgment(socket: zmq.Socket, seq_num: int, packet_num: int, queue: list[tuple[int, int]]):
    message = socket.recv()
    decoded_message = message.decode()
    
    ack_seq_num = int(decoded_message.split(":")[1])
    
    ack_msg = decoded_message.split(":")[0]
    if ack_msg == constants.ACKNOWLEDGMENT:
        seq_num = ack_seq_num + 1
        
    return seq_num

def send_by_sliding_window(socket: zmq.Socket):    
    # Implement sliding window and packet loss logic here
    seq_num = 0
    packet_num = 0
    val =(0,1)
    queue:list[tuple[int, int]] = []
    for i in range(constants.WINDOW_SIZE):
        queue.append((seq_num, packet_num))
      
    # send initial packets  
    for (seq_num, packet_num) in queue:
        socket.send(f"Data: {seq_num}:{packet_num}".encode())
    
    
    while True:
        message = socket.recv()
        decoded_message = message.decode()
        
        ack_seq_num = int(decoded_message.split(":")[1])
        
        ack_msg = decoded_message.split(":")[0]
        if ack_msg == constants.ACKNOWLEDGMENT:
            seq_num = handle_acknowledgment(socket, seq_num, packet_num, queue)
        
        
        
        if decoded_message == constants.ACKNOWLEDGMENT:
            print("Received: ACK")

        print(f"Received: {message.decode()}")
        seq_num += 1
        packet_num += 1
        if packet_num == constants.TOTAL_PACKETS:
            break
        queue.pop(0)
        queue.append((seq_num, packet_num))
        socket.send(f"Data: {seq_num}:{packet_num}".encode())
    
    return seq_num + 1


def __main__():
    global socket
    
    initiate_connection()
    
    if not socket:
        return
    
    close()
    # Implement sliding window and packet loss logic here
    

__main__()
