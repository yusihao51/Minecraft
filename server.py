"""
Prototype of a socket server that could be used both to parallelize computation
and for multiplayer.

The server is multithreaded and run as a daemon.
The main thread listens to connections while a new thread is started for every
request.

For the moment, this is only a demonstration to show how entire sectors could
be exchanged via sockets.  The client requests for a random sector.
The server generates then returns it.
"""

try:  # Python 3
    import socketserver
except ImportError:  # Python 2
    import SocketServer as socketserver
from collections import defaultdict
import cPickle as pickle
from random import randint
import socket
from sys import getsizeof
import threading

import globals as G
from world import World


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        world = self.server.world
        data = self.request.recv(16384)
        sector = pickle.loads(data)

        if sector not in world.sectors:
            world.terraingen.generate_sector(sector)

        response = defaultdict(list)
        for position in world.sectors[sector]:
            response[world[position].id].append(position)

        self.request.sendall(pickle.dumps(response))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        socketserver.ThreadingTCPServer.__init__(self, *args, **kwargs)
        G.SEED = 'choose a seed here'
        self.world = World()


def client(ip, port, message):
    sock = socket.socket()
    sock.connect((ip, port))
    try:
        sock.sendall(message)
        print('Sent %d bits' % getsizeof(message))
        response = sock.recv(16384)
        print('Received %d bits: %s' % (getsizeof(response),
                                        pickle.loads(response)))
    finally:
        sock.close()


def start_server():
    server = Server(('127.0.0.1', 1486), ThreadedTCPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    return server, server_thread


if __name__ == '__main__':
    server, server_thread = start_server()
    print('Server loop running in thread: ' + server_thread.name)

    ip, port = server.server_address

    for i in range(10):
        sector = (randint(-20, 20), 3, randint(-20, 20))
        # Requests this sector
        client(ip, port, pickle.dumps(sector))

    server.shutdown()
    print('Server closed')
