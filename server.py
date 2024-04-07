import zmq
import time
import random

# Assuming the constants module defines INITIATE_CONNECTION_REQUEST, CONNECTION_SUCCESS, and PORT_NUMBER
import constants

socket = None
connected = False
context = zmq.Context()

def simulate_packet_loss():
    """Simulates a 1% chance of packet loss."""
    return random.random() < constants.PACKET_LOSS_RATE

def accept_connection():
    global socket, connected
    
    client_id, data = socket.recv_multipart()
    decoded_message = data.decode()
    
    if decoded_message == constants.INITIATE_CONNECTION_REQUEST:
        socket.send_multipart([client_id, constants.CONNECTION_SUCCESS.encode()])
        connected = True
        print("Server accepted connection")
        return True
    
    return False

def handle_client_requests():
    global  socket , connected, context
    try:
        while True:
            # Wait for the next request from the client
            client_id, data = socket.recv_multipart()
            message = data.decode('utf-8')
            print(f"Received request: {message}")
            
            if message == "close":
                socket.send_multipart([client_id, "Connection closed".encode()])
                connected = False
                print("Connection closed")
            
            if constants.INITIATE_CONNECTION_REQUEST in message:
                # Handle initial connection request
                print("Handling initial connection...")
                socket.send_multipart([client_id, constants.CONNECTION_SUCCESS.encode()])  # Send a connection success message
                socket.send_string(constants.CONNECTION_SUCCESS)
                
            else:
                # Simulate packet processing and selective acknowledgment
                seq_num = message.split(":")[1]
                print(f"Acknowledging packet with sequence number: {seq_num}")
                    # Send an acknowledgment for the received packet
                data = f"ACK:{seq_num}"
                socket.send_multipart([client_id, data.encode()])  # Acknowledge the sequence number
                # if simulate_packet_loss():
                #     print(f"Simulating packet loss for sequence number: {seq_num}")
                #     socket.send_string("")  # Acknowledge the sequence number
                # else:
                #     print(f"Acknowledging packet with sequence number: {seq_num}")
                #     # Send an acknowledgment for the received packet
                #     socket.send_string(f"ACK:{seq_num}")  # Acknowledge the sequence number
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        socket.close()
        context.term()
        
        
def __main__():
    global socket, connected, context

    # Setup PUB socket for sending acknowledgments
    socket = context.socket(zmq.ROUTER)
    socket.bind(f"tcp://*:{constants.PORT_NUMBER}")
    
    print("Server waiting for connection")
    if not connected:
        while not accept_connection():
            # This loop waits until a successful connection is made
            pass
    
    # After a successful connection, handle client requests
    handle_client_requests()
    
    socket.close()
    context.term()  # Properly terminate ZMQ context

if __name__ == "__main__":
    __main__()
