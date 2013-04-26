# Python packages
from _socket import SHUT_RDWR
import socket
from threading import Thread, Event, Lock
import struct
# Third-party packages

# Modules from this project
from warnings import warn
import blocks
from globals import BLOCKS_DIR, SECTOR_SIZE
from savingsystem import null2, structuchar2, sector_to_blockpos

class PacketReceiver(Thread):
    def __init__ (self, world, controller, ipport=("neb.nebtown.info", 1486)):
        Thread.__init__(self)
        self.world = world
        self.controller = controller
        self._stop = Event()
        self.lock = Lock()
        try:
            self.sock = socket.socket()
            self.sock.connect(ipport)
        except socket.error as e:
            print "Socket Error:", e

    def run(self):
        packetcache, packetsize = "", 0

        main_thread = self.world.sector_packets.append
        while 1:
            resp = self.sock.recv(16384)
            if self._stop.isSet() or not resp:
                print "Client PacketReceiver:",self._stop.isSet() and "Shutting down" or "We've been disconnected by the server"
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

    def request_sector(self, sector):
        self.sock.send("\1"+struct.pack("iii", *sector))
    def add_block(self, position, block):
        self.sock.send("\3"+struct.pack("iiibb", *(position+(block.id.main, block.id.sub))))
    def remove_block(self, position):
        self.sock.send("\4"+struct.pack("iii", *position))
    def send_chat(self, msg):
        self.sock.send("\5"+struct.pack("i", len(msg))+msg)

    def stop(self):
        self._stop.set()
        self.sock.shutdown(SHUT_RDWR)