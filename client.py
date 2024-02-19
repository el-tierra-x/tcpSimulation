import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)  # REQ socket for requests
socket.connect("tcp://server_ip_address:5555")

for seq_num in range(1, 20 + 1):
    # Send packet (sequence number)
    socket.send(f"Packet {seq_num}".encode())
    
    # Wait for acknowledgment
    message = socket.recv()
    print(f"Received: {message.decode()}")
    
    # Implement sliding window and packet loss logic here
