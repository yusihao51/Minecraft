# Python packages
from _socket import SHUT_RDWR
import struct
try:  # Python 3
    import socketserver
except ImportError:  # Python 2
    import SocketServer as socketserver
import threading
# Third-party packages

# Modules from this project
import globals as G
from savingsystem import save_sector_to_string, save_blocks
from world_server import WorldServer


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def sendpacket(self, size, packet):
        self.request.sendall(struct.pack("i", 5+size)+packet)

    def handle(self):
        world = self.server.world
        while 1:
            packettype = struct.unpack("b",self.request.recv(1))[0]
            if packettype == 1: #Sector request
                sector = struct.unpack("iii", self.request.recv(4*3))
                #print "Received packet load",sector

                if sector not in world.sectors:
                    world.open_sector(sector)

                if not world.sectors[sector]:
                    #Empty sector, send packet 2
                    #print "Sending empty sector", sector
                    self.sendpacket(12, "\2" + struct.pack("iii",*sector))
                else:
                    msg = struct.pack("iii",*sector) + save_sector_to_string(world, sector) + world.get_exposed_sector(sector)
                    #print "sendding sector info",sector,len(msg)
                    self.sendpacket(len(msg), "\1" + msg)
            else:
                print "Received unknown packettype", packettype


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        socketserver.ThreadingTCPServer.__init__(self, *args, **kwargs)
        G.SEED = 'choose a seed here'
        self.world = WorldServer()

def start_server():
    server = Server(('127.0.0.1', 1486), ThreadedTCPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    return server, server_thread


if __name__ == '__main__':
    server, server_thread = start_server()
    print('Server loop running in thread: ' + server_thread.name)

    ip, port = server.server_address
    print "Listening on",ip,port

    while 1:
        cmd = raw_input()
        if cmd == "stop":
            print "Shutting down socket..."
            server.shutdown(SHUT_RDWR)
            print "Saving..."
            save_blocks(server.world, "world")
            print "Goodbye"
            break
        else:
            print "Unknown command. Have you considered running 'stop'?"
