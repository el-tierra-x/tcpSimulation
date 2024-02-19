import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)  # REP socket for reply (acknowledgments)
socket.bind("tcp://*:5555")

while True:
    # Receive message
    message = socket.recv()
    
    # Process message (simulate packet handling, sequence tracking, etc.)
    
    # Send acknowledgment
    socket.send(b"ACK")
