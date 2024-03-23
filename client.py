import zmq

    
    
def close_connection(socket: zmq.Socket):
    socket.send(b"close")
    socket.close()
    print("Connection closed")


def initiate_connection():
    ip_address = input("Enter the server IP address: ")
    port = input("Enter the server port: ")
    
    context = zmq.Context()
    socket = context.socket(zmq.REQ)  # REQ socket for requests
    socket.connect(f'tcp://{ip_address}:{port}') 
    
    # Send connection request
    socket.send(b"network")
    
    # Wait for acknowledgment
    message = socket.recv()
    recieved_msg = message.decode()
    
    if socket and recieved_msg == "success":
        print("Connection established")
        return socket
    
    else:
        print("Connection failed")
        return False
    
    

def send_by_sliding_window(socket, seq_num, window_size):
    # Send packet (sequence number)
    socket.send(f"Packet {seq_num}".encode())
    
    # Wait for acknowledgment
    message = socket.recv()
    print(f"Received: {message.decode()}")
    
    # Implement sliding window and packet loss logic here
    
    sliding = []
    for i in range(window_size):
        sliding.append(seq_num + i)
      
    # send initial packets  
    for data in sliding:
        socket.send(f"Packet {data}".encode())
    
    
    while True:
        message = socket.recv()
        print(f"Received: {message.decode()}")
        if message.decode() == "ACK":
            break
        else:
            socket.send(f"Packet {data}".encode())
            print(f"Resending: {data}")
        
    for i in range(window_size):
        message = socket.recv()
        print(f"Received: {message.decode()}")
        sliding.pop(0)
        sliding.append(seq_num + window_size + i)
        print(sliding)
    
    return seq_num + 1


def __main__():
    socket = initiate_connection()
    
    if not socket:
        return
    
    
    close_connection(socket)
    # Implement sliding window and packet loss logic here
