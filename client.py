# Python packages
from _socket import SHUT_RDWR
import socket
from threading import Thread, Event, Lock
import struct
from warnings import warn
# Third-party packages

# Modules from this project
import blocks
from globals import BLOCKS_DIR, SECTOR_SIZE
from savingsystem import null2, structuchar2, sector_to_blockpos

class PacketReceiver(Thread):
    def __init__ (self, world, controller, sock):
        Thread.__init__(self)
        self.world = world
        self.controller = controller
        self._stop = Event()
        self.lock = Lock()
        self.sock = sock

    def run(self):
        try:
            self.loop()
        except socket.error as e:
            if e[0] in (10053, 10054):
                #TODO: GUI tell the client they were disconnected
                print "Disconnected from server."
                self.controller.back_to_main_menu.set()
            else:
                raise e

    def loop(self):
        packetcache, packetsize = "", 0

        main_thread = self.world.sector_packets.append
        while 1:
            resp = self.sock.recv(16384)
            if self._stop.isSet() or not resp:
                print "Client PacketReceiver:",self._stop.isSet() and "Shutting down" or "We've been disconnected by the server"
                self.sock.shutdown(SHUT_RDWR)
                return

            packetcache += resp
            if not packetsize:
                packetsize = struct.unpack("i", packetcache[:4])[0]

            while packetsize and len(packetcache) >= packetsize:
                #Once we've obtained the whole packet
                packetid = struct.unpack("B",packetcache[4])[0]  # Server Packet Type
                packet = packetcache[5:packetsize]

                #Preprocess the packet as much as possible in this thread
                if packetid == 1:    # Receiving sector
                    with self.lock:
                        main_thread((packetid, packet))
                elif packetid == 2:  # Receiving blank sector
                    with self.lock:
                        main_thread((packetid, struct.unpack("iii", packet)))
                elif packetid == 3:  # Add Block
                    with self.lock:
                        main_thread((packetid,
                                     (struct.unpack("iii", packet[:12]),
                                     BLOCKS_DIR[blocks.BlockID(struct.unpack("BB", packet[12:]))])))
                elif packetid == 4:  # Remove Block
                    with self.lock:
                        main_thread((packetid, struct.unpack("iii", packet)))
                elif packetid == 5:  # Print Chat
                    with self.lock:
                        main_thread((packetid, (packet[:-4], struct.unpack("BBBB", packet[-4:]))))
                elif packetid == 255:  # Spawn Position
                    with self.lock:
                        main_thread((packetid, struct.unpack("iii", packet)))
                else:
                    warn("Received unknown packetid %s" % packetid)
                packetcache = packetcache[packetsize:]
                packetsize = struct.unpack("i", packetcache[:4])[0] if packetcache else 0

    #The following functions are run by the Main Thread
    def dequeue_packet(self):
        with self.lock:
            packetid, packet = self.world.sector_packets.popleft()
        if packetid == 1:  # Sector
            blocks, sectors = self.world, self.world.sectors
            secpos = struct.unpack("iii", packet[:12])
            sector = sectors[secpos]
            cx, cy, cz = sector_to_blockpos(secpos)
            fpos = 12
            exposed_pos = fpos + 1024
            for x in xrange(cx, cx+8):
                for y in xrange(cy, cy+8):
                    for z in xrange(cz, cz+8):
                        read = packet[fpos:fpos+2]
                        fpos += 2
                        unpacked = structuchar2.unpack(read)
                        if read != null2 and unpacked in BLOCKS_DIR:
                            position = x,y,z
                            blocks[position] = BLOCKS_DIR[unpacked]
                            sector.append(position)
                            if packet[exposed_pos] is "1":
                                blocks.show_block(position)
                        exposed_pos += 1
            if secpos in self.world.sector_queue:
                del self.world.sector_queue[secpos] #Delete any hide sector orders
        elif packetid == 2:  # Blank Sector
            self.world.sectors[packet] = []
        elif packetid == 3:  # Add Block
            self.world._add_block(packet[0], packet[1])
        elif packetid == 4:  # Remove Block
            self.world._remove_block(packet)
        elif packetid == 5:  # Chat Print
            self.controller.write_line(packet[0], color=packet[1])
        elif packetid == 255:  # Spawn Position
            self.controller.player.position = packet
            #Now that we know where the player should be, we can enable .update again
            self.controller.update = self.controller.update_disabled

    def request_sector(self, sector):
        self.sock.sendall("\1"+struct.pack("iii", *sector))
    def add_block(self, position, block):
        self.sock.sendall("\3"+struct.pack("iiiBB", *(position+(block.id.main, block.id.sub))))
    def remove_block(self, position):
        self.sock.sendall("\4"+struct.pack("iii", *position))
    def send_chat(self, msg):
        self.sock.sendall("\5"+struct.pack("i", len(msg))+msg)
    def request_spawnpos(self):
        self.sock.sendall(struct.pack("B", 255))

    def stop(self):
        self._stop.set()
        self.sock.shutdown(SHUT_RDWR)