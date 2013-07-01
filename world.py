# Imports, sorted alphabetically.

# Python packages
from collections import deque, defaultdict, OrderedDict
import os
from time import time
import warnings

# Third-party packages
import pyglet
from pyglet.gl import *

# Modules from this project
from blocks import *
from utils import FACES, FACES_WITH_DIAGONALS, normalize_float, normalize, sectorize, TextureGroup
import globals as G
from client import PacketReceiver
from entity import TileEntity


__all__ = (
    'World',
)


#The Client's world
class World(dict):
    spreading_mutations = {
        dirt_block: grass_block,
    }

    def __init__(self):
        super(World, self).__init__()
        self.batch = pyglet.graphics.Batch()
        self.transparency_batch = pyglet.graphics.Batch()
        self.group = TextureGroup(os.path.join('resources', 'textures', 'texture.png'))

        self.shown = {}
        self._shown = {}
        self.sectors = defaultdict(list)
        self.before_set = set()
        self.urgent_queue = deque()
        self.lazy_queue = deque()
        self.sector_queue = OrderedDict()

        self.packetreceiver = None
        self.sector_packets = deque()
        # biome generator for colorizer, set by packet receiver
        self.biome_generator = None

    # Add the block clientside, then tell the server about the new block
    def add_block(self, position, block, sync=True, force=True):
        self._add_block(position, block)  # For Prediction
        if sync:
            self.packetreceiver.add_block(position, block)

    # Clientside, add the block
    def _add_block(self, position, block):
        if position in self:
            self._remove_block(position, sync=True)
        if hasattr(block, 'entity_type'):
            # in world_server we have to create its entity to handle some tasks(growing, etc.)
            # but in client's world, we only create a TileEntity that contains the position
            # and the world to allow the block update itself and server will handle the task
            # and tell us
            self[position] = type(block)()
            self[position].entity = TileEntity(self, position)
        elif block.sub_id_as_metadata:
            self[position] = type(block)()
            self[position].set_metadata(block.get_metadata())
        else:
            self[position] = block

        self.sectors[sectorize(position)].append(position)
        if self.is_exposed(position):
            self.show_block(position)
        self.inform_neighbors_of_block_change(position)

    def remove_block(self, player, position, sync=True, sound=True):
        if sound and player is not None:
            self[position].play_break_sound(player, position)
        self._remove_block(position, sync=sync)
        if sync:
            self.packetreceiver.remove_block(position)

    # Clientside, delete the block
    def _remove_block(self, position, sync=True):
        del self[position]
        sector_position = sectorize(position)
        try:
            self.sectors[sector_position].remove(position)
        except ValueError:
            warnings.warn('Block %s was unexpectedly not found in sector %s;'
                          'your save is probably corrupted'
                          % (position, sector_position))
        if sync:
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors(position)
            self.inform_neighbors_of_block_change(position)

    def is_exposed(self, position):
        x, y, z = position
        for fx,fy,fz in FACES:
            other_position = (fx+x, fy+y, fz+z)
            if other_position not in self or self[other_position].transparent:
                return True
        return False

    def neighbors_iterator(self, position, relative_neighbors_positions=FACES):
        x, y, z = position
        for dx, dy, dz in relative_neighbors_positions:
            yield x + dx, y + dy, z + dz

    def check_neighbors(self, position):
        for other_position in self.neighbors_iterator(position):
            if other_position not in self:
                continue
            if self.is_exposed(other_position):
                if other_position not in self.shown:
                    self.show_block(other_position)
            else:
                if other_position in self.shown:
                    self.hide_block(other_position)

    def has_neighbors(self, position, is_in=None, diagonals=False,
                      faces=None):
        if faces is None:
            faces = FACES_WITH_DIAGONALS if diagonals else FACES
        for other_position in self.neighbors_iterator(
            position, relative_neighbors_positions=faces):
            if other_position in self:
                if is_in is None or self[other_position] in is_in:
                    return True
        return False

    def inform_neighbors_of_block_change(self, position):
        for neighbor in self.neighbors_iterator(position):
            if neighbor not in self:
                continue
            self[neighbor].on_neighbor_change(self, position, neighbor)
            #self.hide_block(neighbor)
            #self.show_block(neighbor)

    def hit_test(self, position, vector, max_distance=8, hitwater=False):
        m = 8
        x, y, z = position
        dx, dy, dz = vector
        dx, dy, dz = dx / m, dy / m, dz / m
        previous = ()
        for _ in xrange(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and key in self and (self[key].density != 0.5 or hitwater):
                return key, previous
            previous = key
            x, y, z = x + dx, y + dy, z + dz
        return None, None

    def hide_block(self, position, immediate=True):
        del self.shown[position]
        if immediate:
            self._hide_block(position)
        else:
            self.enqueue(self._hide_block, position)

    def _hide_block(self, position):
        self._shown.pop(position).delete()

    def show_block(self, position, immediate=True):
        block = self[position]
        self.shown[position] = block
        if immediate:
            self._show_block(position, block)
        else:
            self.enqueue(self._show_block, position, block)

    def _show_block(self, position, block):
        # only show exposed faces
        index = 0
        vertex_data = list(block.get_vertices(*position))
        texture_data = list(block.texture_data)
        color_data = None
        if hasattr(block, 'get_color') and self.biome_generator is not None:
            temp = self.biome_generator.get_temperature(position[0], position[-1])
            humidity = self.biome_generator.get_humidity(position[0], position[-1])
            color_data =  block.get_color(temp, humidity)
        count = len(texture_data) / 2
        # FIXME: Do something of what follows.
        #for neighbor in self.neighbors_iterator(position):
        #    if neighbor in self:
        #        count -= 4
        #        i = index * 12
        #        j = index * 8
        #        del vertex_data[i:i + 12]
        #        del texture_data[j:j + 8]
        #        if color_data is not None:
        #            del color_data[i:i+12]
        #    else:
        #       index += 1

        count = len(texture_data) / 2
        # create vertex list
        batch = self.transparency_batch if block.transparent else self.batch
        if color_data is not None:
            self._shown[position] = batch.add(count, GL_QUADS, block.group or self.group,
                                          ('v3f/static', vertex_data),
                                          ('t2f/static', texture_data),
                                          ('c3f/static', color_data))
        else:
            self._shown[position] = batch.add(count, GL_QUADS, block.group or self.group,
                                          ('v3f/static', vertex_data),
                                          ('t2f/static', texture_data))

    def show_sector(self, sector):
        if sector in self.sectors:
            self._show_sector(sector)
        else:
            self.sectors[sector] = [] #Initialize it so we don't keep requesting it
            self.packetreceiver.request_sector(sector)

    #Clientside, show a sector we've downloaded
    def _show_sector(self, sector):
        for position in self.sectors[sector]:
            if position not in self.shown and self.is_exposed(position):
                self.show_block(position)

    def _hide_sector(self, sector):
        if sector in self.sectors:
            for position in self.sectors[sector]:
                if position in self: del self[position]
                if position in self.shown:
                    self.hide_block(position)
            del self.sectors[sector]

    def change_sectors(self, after):
        before_set = self.before_set
        after_set = set()
        pad = G.VISIBLE_SECTORS_RADIUS
        x, y, z = after
        for distance in xrange(0, pad + 1):
            for dx in xrange(-distance, distance + 1):
                for dz in xrange(-distance, distance + 1):
                    if abs(dx) != distance and abs(dz) != distance:
                        continue
                    for dy in xrange(-4, 4):
                        if dx ** 2 + dy ** 2 + dz ** 2 > (pad + 1) ** 2:
                            continue
                        after_set.add((x + dx, y + dy, z + dz))
        #for sector in (after_set - before_set):
           # self.show_sector(sector)
        #Queue the sectors to be shown, instead of rendering them in real time
        for sector in (after_set - before_set):
            self.enqueue_sector(True, sector)
        self.before_set = after_set

    def enqueue_sector(self, state, sector): #State=True to show, False to hide
        self.sector_queue[sector] = state

    def dequeue_sector(self):
        sector, state = self.sector_queue.popitem(False)
        if state:
            self.show_sector(sector)
            pass
        else:
            self._hide_sector(sector)

    def enqueue(self, func, *args, **kwargs):
        task = func, args, kwargs
        urgent = kwargs.pop('urgent', False)
        queue = self.urgent_queue if urgent else self.lazy_queue
        if task not in queue:
            queue.appendleft(task)

    def dequeue(self):
        queue = self.urgent_queue or self.lazy_queue
        func, args, kwargs = queue.pop()
        func(*args, **kwargs)

    def process_queue(self, dt):
        stoptime = time() + G.QUEUE_PROCESS_SPEED
        while time() < stoptime:
            #Process as much of the queues as we can
            if self.sector_queue:
                self.dequeue_sector()
            elif self.sector_packets:
                self.packetreceiver.dequeue_packet()
            elif self.urgent_queue or self.lazy_queue:
                self.dequeue()
            else:
                break

    def process_entire_queue(self):
        while self.urgent_queue or self.lazy_queue:
            self.dequeue()

    def hide_sectors(self, dt, player):
        #TODO: This is pretty laggy, I feel an FPS drop once a second while sector changing because of this
        deload = G.DELOAD_SECTORS_RADIUS
        plysector = sectorize(player.position)
        if player.last_sector != plysector:
            px, py, pz = plysector
            for sector in self.sectors:
                x,y,z = sector
                if abs(px-x) > deload or abs(py-y) > deload or abs(pz-z) > deload:
                    self.enqueue_sector(False, sector)