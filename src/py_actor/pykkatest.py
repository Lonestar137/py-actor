import pykka
import zmq
import time
import threading


class ServerActor(pykka.ThreadingActor):

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")

    def on_start(self):
        threading.Thread(target=self.listen, daemon=True).start()

    def listen(self):
        while True:
            message = self.socket.recv_string()
            print(f"Received message: {message}")
            if message == 'ping':
                self.socket.send_string('pong')
            else:
                self.socket.send_string('Unknown command')

    def on_stop(self):
        self.socket.close()
        self.context.term()


class ClientActor(pykka.ThreadingActor):

    def __init__(self, server_address):
        super().__init__()
        self.server_address = server_address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{self.server_address}")

    def on_receive(self, message):
        self.socket.send_string(message)
        response = self.socket.recv_string()
        return response

    def on_stop(self):
        self.socket.close()
        self.context.term()


def client():
    server_address = "localhost:5555"  # Replace with the server's IP and port
    client_actor = ClientActor.start(server_address)
    print("ClientActor started")

    # Sending a ping message
    response = client_actor.ask('ping')
    print(f"Response from server: {response}")

    # Stop the actor
    client_actor.stop()


def server():
    port = 5555  # Port to listen on
    actor = ServerActor.start(port)
    print(f"ServerActor started on port {port}")


if __name__ == "__main__":
    # server()
    client()
