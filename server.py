# Python packages
from _socket import SHUT_RDWR
import socket
import struct
import time

try:  # Python 3
    import socketserver
except ImportError:  # Python 2
    import SocketServer as socketserver
import threading
# Third-party packages

# Modules from this project
import globals as G
from savingsystem import save_sector_to_string, save_blocks, save_world, load_player, save_player
from world_server import WorldServer
import blocks
from commands import CommandParser, COMMAND_HANDLED, CommandException, COMMAND_ERROR_COLOR
from utils import sectorize

#This class is effectively a serverside "Player" object
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    inventory = "\0"*(4*40)  # Currently, is serialized to be 4 bytes * (27 inv + 9 quickbar + 4 armor) = 160 bytes
    def sendpacket(self, size, packet):
        self.request.sendall(struct.pack("i", 5+size)+packet)
    def sendchat(self, txt, color=(255,255,255,255)):
        txt = txt.encode('utf-8')
        self.sendpacket(len(txt) + 4, "\5" + txt + struct.pack("BBBB", *color))

    def handle(self):
        self.username = str(self.client_address)
        print "Client connecting...", self.client_address
        self.server.players[self.client_address] = self
        try:
            self.loop()
        except socket.error as e:
            if self.server._stop.isSet():
                return  # Socket error while shutting down doesn't matter
            if e[0] in (10053, 10054):
                print "Client %s %s crashed." % (self.username, self.client_address)
            else:
                raise e

    def loop(self):
        world, players = self.server.world, self.server.players
        while 1:
            byte = self.request.recv(1)
            if not byte: return  # The client has disconnected intentionally

            packettype = struct.unpack("B", byte)[0]  # Client Packet Type
            if packettype == 1:  # Sector request
                sector = struct.unpack("iii", self.request.recv(4*3))

                if sector not in world.sectors:
                    with world.server_lock:
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
                blockid = G.BLOCKS_DIR[struct.unpack("BB", blockbytes)]
                with world.server_lock:
                    world.add_block(position, blockid, sync=False)

                for address in players:
                    if address is self.client_address: continue  # He told us, we don't need to tell him
                    players[address].sendpacket(14, "\3" + positionbytes + blockbytes)
            elif packettype == 4:  # Remove block
                positionbytes = self.request.recv(4*3)

                with world.server_lock:
                    world.remove_block(struct.unpack("iii", positionbytes), sync=False)

                for address in players:
                    if address is self.client_address: continue  # He told us, we don't need to tell him
                    players[address].sendpacket(12, "\4" + positionbytes)
            elif packettype == 5:  # Receive chat text
                txtlen = struct.unpack("i", self.request.recv(4))[0]
                txt = "%s: %s" % (self.username, self.request.recv(txtlen).decode('utf-8'))
                try:
                    #TODO: Enable the command parser again. This'll need some serverside controller object and player object
                    #ex = self.command_parser.execute(txt, controller=self, user=self.player, world=self.world)
                    ex = None
                    if ex != COMMAND_HANDLED:
                        # Not a command, send the chat to all players
                        for address in players:
                            players[address].sendchat(txt)
                        print txt  # May as well let console see it too
                except CommandException, e:
                    self.sendchat(str(e), COMMAND_ERROR_COLOR)
            elif packettype == 6:  # Player Inventory Update
                self.inventory = self.request.recv(4*40)
                #TODO: All player's inventories should be autosaved at a regular interval.
            elif packettype == 255:  # Initial Login
                txtlen = struct.unpack("i", self.request.recv(4))[0]
                self.username = self.request.recv(txtlen).decode('utf-8')
                load_player(self, "world")

                for player in self.server.players.itervalues():
                    player.sendchat("%s has connected." % self.username)
                print "%s's username is %s" % (self.client_address, self.username)

                position = (0,self.server.world.terraingen.get_height(0,0)+2,0)

                # Send user list
                userlist = '\7'
                for player in self.server.players.itervalues():
                    userlist += player.username.encode('utf-8') + '\7'
                for player in self.server.players.itervalues():
                    player.sendpacket(len(userlist) - 1, userlist)

                #Send them the sector under their feet first so they don't fall
                sector = sectorize(position)
                if sector not in world.sectors:
                    with world.server_lock:
                        world.open_sector(sector)
                msg = struct.pack("iii",*sector) + save_sector_to_string(world, sector) + world.get_exposed_sector(sector)
                self.sendpacket(len(msg), "\1" + msg)

                #Send them their spawn position
                self.sendpacket(12, struct.pack("B",255) + struct.pack("iii", *position))
                self.sendpacket(4*40, "\6" + self.inventory)
            else:
                print "Received unknown packettype", packettype
    def finish(self):
        print "Client disconnected,", self.client_address, self.username
        try: del self.server.players[self.client_address]
        except KeyError: pass
        for player in self.server.players.itervalues():
            player.sendchat("%s has disconnected." % self.username)
        # Send user list
        userlist = '\7'
        for player in self.server.players.itervalues():
            userlist += player.username.encode('utf-8') + '\7'
        for player in self.server.players.itervalues():
            player.sendpacket(len(userlist) - 1, userlist)
        save_player(self, "world")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        socketserver.ThreadingTCPServer.__init__(self, *args, **kwargs)
        self._stop = threading.Event()

        self.world = WorldServer(self)
        self.players = {}  # List of all players connected. {ipaddress: requesthandler,}

        self.command_parser = CommandParser()

    def show_block(self, position, block):
        blockid = block.id
        for player in server.players.itervalues():
            #TODO: Only if they're in range
            player.sendpacket(14, "\3" + struct.pack("iiiBB", *(position+(blockid.main, blockid.sub))))

    def hide_block(self, position):
        for player in server.players.itervalues():
            #TODO: Only if they're in range
            player.sendpacket(12, "\4" + struct.pack("iii", *position))


def start_server():
    localip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][0]
    server = Server((localip, 1486), ThreadedTCPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    threading.Thread(target=server.world.content_update, name="world_server.content_update").start()

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

    helptext = "Available commands: " + ", ".join(["say", "stop", "save"])
    while 1:
        args = raw_input().replace(chr(13), "").split(" ")  # On some systems CR is appended, gotta remove that
        cmd = args.pop(0)
        if cmd == "say":
            msg = "Server: %s" % " ".join(args)
            print msg
            for player in server.players.itervalues():
                player.sendchat(msg, color=(180,180,180,255))
        elif cmd == "help":
            print helptext
        elif cmd == "save":
            print "Saving..."
            save_world(server, "world")
            print "Done saving"
        elif cmd == "stop":
            server._stop.set()
            print "Disconnecting clients..."
            for address in server.players:
                server.players[address].request.shutdown(SHUT_RDWR)
                server.players[address].request.close()
            print "Shutting down socket..."
            server.shutdown()
            print "Saving..."
            save_world(server, "world")
            print "Goodbye"
            break
        else:
            print "Unknown command '%s'." % cmd, helptext
    while len(threading.enumerate()) > 1:
        threads = threading.enumerate()
        threads.remove(threading.current_thread())
        print "Waiting on these threads to close:", threads
        time.sleep(1)