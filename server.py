import zmq

import constants

socket = None
connected = False

def accept_connection():
    global socket, connected
    
    message = socket.recv()
    decoded_message = message.decode()
    
    if decoded_message == constants.INITIATE_CONNECTION_REQUEST:
        socket.send(bytes(constants.CONNECTION_SUCCESS, 'utf-8'))
        connected = True
        print("Server accepted connection")
        
        return True
    
    return False
        
    

def __main__():
    global socket , connected
    context = zmq.Context()
    socket = context.socket(zmq.REP)  # REP socket for reply (acknowledgments)
    socket.bind(f"tcp://*:{constants.PORT_NUMBER}")
    
    if not connected:
        print("Server waiting for connection")
        while not accept_connection():
            pass
    
    while True:
        message = socket.recv()
        decoded_message = message.decode()
        
        if decoded_message == "close":
            socket.send(b"closed")
            socket.close()
            connected = False
            socket = None
            print("Connection closed")
            return
        
        socket.send(b"ACK")

__main__()
    
    
    



