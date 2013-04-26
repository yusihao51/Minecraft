# Python packages
from _socket import SHUT_RDWR
import socket
import struct
from commands import CommandParser, COMMAND_HANDLED, CommandException, COMMAND_ERROR_COLOR

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
import blocks

world_server_lock = threading.Lock()

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def sendpacket(self, size, packet):
        self.request.sendall(struct.pack("i", 5+size)+packet)

    def handle(self):
        print "Client connected,", self.client_address
        self.server.players[self.client_address] = self

        world, players = self.server.world, self.server.players
        while 1:
            byte = self.request.recv(1)
            if not byte: return

            packettype = struct.unpack("B", byte)[0]  # Client Packet Type
            if packettype == 1:  # Sector request
                sector = struct.unpack("iii", self.request.recv(4*3))

                if sector not in world.sectors:
                    with world_server_lock:
                        world.open_sector(sector)

                if not world.sectors[sector]:
                    #Empty sector, send packet 2
                    self.sendpacket(12, "\2" + struct.pack("iii",*sector))
                else:
                    msg = struct.pack("iii",*sector) + save_sector_to_string(world, sector) + world.get_exposed_sector(sector)
                    self.sendpacket(len(msg), "\1" + msg)
            elif packettype == 3:  # Add block
                positionbytes = self.request.recv(4*3)
                blockbytes = self.request.recv(2)

                position = struct.unpack("iii", positionbytes)
                blockid = G.BLOCKS_DIR[blocks.BlockID(struct.unpack("BB", blockbytes))]
                world.add_block(position, blockid, sync=True)

                for address in players:
                    if address is self.client_address: continue  # He told us, we don't need to tell him
                    players[address].sendpacket(14, "\3" + positionbytes + blockbytes)
            elif packettype == 4:  # Remove block
                positionbytes = self.request.recv(4*3)

                world.remove_block(struct.unpack("iii", positionbytes), sync=True)

                for address in players:
                    if address is self.client_address: continue  # He told us, we don't need to tell him
                    players[address].sendpacket(12, "\4" + positionbytes)
            elif packettype == 5:  # Receive chat text
                txtlen = struct.unpack("i", self.request.recv(4))[0]
                txt = "%s: %s" % (self.client_address[0], self.request.recv(txtlen))
                try:
                    #TODO: Enable the command parser again. This'll need some serverside controller object and player object
                    #ex = self.command_parser.execute(txt, controller=self, user=self.player, world=self.world)
                    ex = None
                    if ex != COMMAND_HANDLED:
                        # Not a command, send the chat to all players
                        for address in players:
                            players[address].sendpacket(len(txt) + 4, "\5" + txt + struct.pack("BBBB", 255, 255, 255, 255))
                            #self.write_line("> %s" % txt, color=(255, 255, 255, 255))
                except CommandException, e:
                    error = str(e)
                    self.sendpacket(len(error) + 4, "\5" + error + struct.pack("BBBB", *COMMAND_ERROR_COLOR))
                    #self.write_line(error, color=COMMAND_ERROR_COLOR)
            else:
                print "Received unknown packettype", packettype
    def finish(self):
        print "Client disconnected,", self.client_address
        del self.server.players[self.client_address]

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        socketserver.ThreadingTCPServer.__init__(self, *args, **kwargs)
        self.world = WorldServer()
        self.players = {}  # List of all players connected. {ipaddress: requesthandler,}

        self.command_parser = CommandParser()


def start_server():
    localip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][0]
    server = Server((localip, 1486), ThreadedTCPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    return server, server_thread


if __name__ == '__main__':
    #TODO: Enable server launch options
    #In the mean time, manually set
    setattr(G.LAUNCH_OPTIONS, "seed", None)
    G.SAVE_FILENAME = "world"

    server, server_thread = start_server()
    print('Server loop running in thread: ' + server_thread.name)

    ip, port = server.server_address
    print "Listening on",ip,port

    while 1:
        cmd = raw_input()
        if cmd == "stop":
            print "Disconnecting clients..."
            for address in server.players:
                server.players[address].request.shutdown(SHUT_RDWR)
            print "Shutting down socket..."
            server.shutdown()
            print "Saving..."
            save_blocks(server.world, "world")
            print "Goodbye"
            break
        else:
            print "Unknown command. Have you considered running 'stop'?"
