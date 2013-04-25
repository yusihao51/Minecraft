# Python packages
from _socket import SHUT_RDWR
import socket
from threading import Thread, Event, Lock
import struct
# Third-party packages

# Modules from this project
from globals import BLOCKS_DIR, SECTOR_SIZE
from savingsystem import null2, structuchar2, sector_to_blockpos

class PacketReceiver(Thread):
    def __init__ (self, world, ipport=("127.0.0.1", 1486)):
        Thread.__init__(self)
        self.world = world
        self._stop = Event()
        self.lock = Lock()
        try:
            self.sock = socket.socket()
            self.sock.connect(ipport)
        except socket.error as e:
            print "Socket Error:", e

    def run(self):
        packetcache, packetsize = "", 0
        while 1:
            resp = self.sock.recv(16384)
            if self._stop.isSet() or not resp:
                print "Client PacketReceiver:",self._stop.isSet() and "Shutting down" or "We've been disconnected by the server"
                return

            packetcache += resp
            if not packetsize:
                packetsize = struct.unpack("i", packetcache[:4])[0]

            if len(packetcache) >= packetsize:
                packetid = struct.unpack("b",packetcache[4])[0]
                packet = packetcache[5:packetsize]
                if packetid == 1: #Receiving sector
                    with self.lock:
                        self.world.sector_packets.append((1,packet))
                elif packetid == 2: #Receiving blank sector
                    with self.lock:
                        self.world.sector_packets.append((2,struct.unpack("iii", packet)))
                else:
                    print "Received unknown packetid", packetid
                packetcache = packetcache[packetsize:]
                packetsize = 0

    #The following functions are run by the Main Thread
    def dequeue_packet(self):
        with self.lock:
            packetid, packet = self.world.sector_packets.popleft()
        if packetid == 1: #Sector
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
        elif packetid == 2: #Blank Sector
            self.world.sectors[packet] = []

    def request_sector(self, sector):
        self.sock.send("\1"+struct.pack("iii", *sector))

    def stop(self):
        self._stop.set()
        self.sock.shutdown(SHUT_RDWR)