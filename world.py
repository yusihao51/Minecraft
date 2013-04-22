# Imports, sorted alphabetically.

# Python packages
from collections import deque, OrderedDict
import os
from time import time
import warnings

# Third-party packages
import pyglet
from pyglet.gl import *
from sqlalchemy import Column, Integer, ForeignKey, Boolean, func, exists
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


# Modules from this project
from blocks import *
from debug import performance_info
import globals as G
import terrain


FACES = (
    ( 0,  1,  0),
    ( 0, -1,  0),
    (-1,  0,  0),
    ( 1,  0,  0),
    ( 0,  0,  1),
    ( 0,  0, -1),
)

FACES_WITH_DIAGONALS = FACES + (
    (-1, -1,  0),
    (-1,  0, -1),
    ( 0, -1, -1),
    ( 1,  1,  0),
    ( 1,  0,  1),
    ( 0,  1,  1),
    ( 1, -1,  0),
    ( 1,  0, -1),
    ( 0,  1, -1),
    (-1,  1,  0),
    (-1,  0,  1),
    ( 0, -1,  1),
)


def normalize_float(f):
    """
    This is faster than int(round(f)).  Nearly two times faster.
    Since it is run at least 500,000 times during map generation,
    and also in game logic, it has a major impact on performance.

    >>> normalize_float(0.2)
    0
    >>> normalize_float(-0.4)
    0
    >>> normalize_float(0.5)
    1
    >>> normalize_float(-0.5)
    -1
    >>> normalize_float(0.0)
    0
    """
    int_f = int(f)
    if f > 0:
        if f - int_f < 0.5:
            return int_f
        return int_f + 1
    if f - int_f > -0.5:
        return int_f
    return int_f - 1


def normalize(position):
    x, y, z = position
    return normalize_float(x), normalize_float(y), normalize_float(z)


def sectorize(position):
    x, y, z = normalize(position)
    x, y, z = (x / G.SECTOR_SIZE,
               y / G.SECTOR_SIZE,
               z / G.SECTOR_SIZE)
    return x, y, z


class TextureGroup(pyglet.graphics.Group):
    def __init__(self, path):
        super(TextureGroup, self).__init__()
        self.texture = pyglet.image.load(path).get_texture()

    def set_state(self):
        glBindTexture(self.texture.target, self.texture.id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glEnable(self.texture.target)

    def unset_state(self):
        glDisable(self.texture.target)


def get_or_create(model, **kwargs):
    try:
        return G.SQL_SESSION.query(model).filter_by(**kwargs).one()
    except NoResultFound:
        instance = model(**kwargs)
        G.SQL_SESSION.add(instance)
        return instance


class Sector(G.SQLBase):
    __tablename__ = 'sectors'

    pk = Column(Integer, primary_key=True)
    x = Column(Integer, index=True)
    y = Column(Integer, index=True)
    z = Column(Integer, index=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        super(Sector, self).__init__()

    def __eq__(self, other):
        return self.position == other.position

    def __hash__(self):
        return self.pk

    def __repr__(self):
        return '<Sector %d %d %d>' % self.position

    @property
    def position(self):
        return self.x, self.y, self.z

    @position.setter
    def position(self, value):
        self.x, self.y, self.z = value

    def has_blocks(self):
        return G.SQL_SESSION.query(exists(self.blocks.statement)).scalar()

    def is_empty(self):
        return not self.has_blocks()

    def get_blocks(self):
        if self.has_blocks():
            return self.blocks
        self.rebuild_blocks()
        return self.blocks

    def rebuild_blocks(self):
        d = G.SECTOR_SIZE - 1
        self.blocks = G.SQL_SESSION.query(Block).filter(
            Block.x.between(self.x, self.x + d),
            Block.y.between(self.y, self.y + d),
            Block.z.between(self.z, self.z + d),
        ).all()
        G.SQL_SESSION.add(self)

    def get_exposed_blocks(self):
        return self.get_blocks().filter(
            (Block.is_exposed == True) | (Block.is_exposed == None))

    def is_visible(self):
        return G.SQL_SESSION.query(exists(self.get_exposed_blocks().statement)).scalar()

    @staticmethod
    def exists_at(x, y, z):
        return G.SQL_SESSION.query(exists().where(
            Sector.x == x and Sector.y == y and Sector.z == z)).scalar()

    @staticmethod
    def get_from_block_position(block_position):
        x, y, z = sectorize(block_position)
        return get_or_create(Sector, x=x, y=y, z=z)

    @classmethod
    @performance_info
    def rebuild_sectors(cls):
        xm, xM, ym, yM, zm, zM = G.SQL_SESSION.query(
            func.min(Block.x),
            func.max(Block.x),
            func.min(Block.y),
            func.max(Block.y),
            func.min(Block.z),
            func.max(Block.z),
        ).all()[0]
        d = G.SECTOR_SIZE - 1

        max_blocks = G.SECTOR_SIZE ** 3
        for x in xrange(xm, xM, d):
            for y in xrange(ym, yM, d):
                for z in xrange(zm, zM, d):
                    sector = get_or_create(Sector, x=x, y=y, z=z)
                    blocks = sector.get_blocks()
                    if blocks.count() == max_blocks:
                        blocks.filter(
                            Block.is_exposed == None,
                            Block.x.between(x + 1, x + d - 1),
                            Block.y.between(y + 1, y + d - 1),
                            Block.z.between(z + 1, z + d - 1),
                        ).update({'is_exposed': False},
                                 synchronize_session=False)


class Block(G.SQLBase):
    __tablename__ = 'blocks'

    pk = Column(Integer, primary_key=True)
    x = Column(Integer, index=True)
    y = Column(Integer, index=True)
    z = Column(Integer, index=True)
    is_exposed = Column(Boolean, index=True)
    blocktype_id_main = Column(Integer)
    blocktype_id_sub = Column(Integer)
    sector_id = Column(Integer, ForeignKey(Sector.pk), nullable=True,
                       index=True)
    sector = relationship('Sector', backref=backref('blocks', lazy='dynamic'))

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        # if kwargs.get('sector', None) is None:
        #     self.sector = Sector.get_from_block_position(self.position)
        super(Block, self).__init__()

    def __eq__(self, other):
        return self.position == other.position \
            and self.blocktype == other.blocktype

    def __hash__(self):
        return self.pk

    def __repr__(self):
        return '<Block %d %d %d>' % self.position

    @property
    def position(self):
        return self.x, self.y, self.z

    @position.setter
    def position(self, value):
        self.x, self.y, self.z = value

    @property
    def blocktype_id(self):
        return BlockID(self.blocktype_id_main, self.blocktype_id_sub)

    @blocktype_id.setter
    def blocktype_id(self, value):
        self.blocktype_id_main, self.blocktype_id_sub = value.main, value.sub

    @property
    def blocktype(self):
        return G.BLOCKS_DIR[self.blocktype_id]

    @blocktype.setter
    def blocktype(self, value):
        self.blocktype_id = value.id


class World(dict):
    spreading_mutations = {
        dirt_block: grass_block,
    }

    def __init__(self):
        super(World, self).__init__()
        self.batch = pyglet.graphics.Batch()
        self.transparency_batch = pyglet.graphics.Batch()
        self.group = TextureGroup(os.path.join('resources', 'textures', 'texture.png'))

        self.to_be_added = {}
        self.shown = {}
        self.shown_sectors = []
        self.shown_blocks = []
        self.before_set = set()
        self.urgent_queue = deque()
        self.lazy_queue = deque()
        self.terraingen = terrain.TerrainGeneratorSimple(self, G.SEED)

        self.spreading_mutable_blocks = deque()
        self.spreading_time = 0.0

    def __delitem__(self, position):
        super(World, self).__delitem__(position)

        block = self.get_block(*position)

        if block in self.spreading_mutable_blocks:
            try:
                self.spreading_mutable_blocks.remove(block)
            except ValueError:
                warnings.warn('BlockType %s was unexpectedly not found in the '
                              'spreading mutations; your save is probably '
                              'corrupted' % repr(position))

    def add_block(self, position, blocktype, sync=True, force=True, sector=None):
        if position in self:
            if force:
                self.remove_block(None, position, sync=sync)

        block = Block(position=position, blocktype=blocktype, sector=sector)

        if blocktype.id == furnace_block.id:
            self[position] = FurnaceBlock()
        else:
            self[position] = blocktype

        if sync:
            G.SQL_SESSION.add(block)
            if self.is_exposed(block):
                self.show_block(block)
            self.check_neighbors(block)
        else:
            self.to_be_added[position] = block

    def remove_block(self, player, position, sync=True, sound=True):
        if sound and player is not None:
            self[position].play_break_sound(player, position)
        del self[position]

        if sync:
            x, y, z = position
            try:
                block = G.SQL_SESSION.query(Block).filter_by(x=x, y=y, z=z).one()
            except NoResultFound:
                return
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors(block)
            G.SQL_SESSION.delete(block)
        else:
            if position in self.to_be_added:
                del self.to_be_added[position]

    def neighbors_iterator(self, position, relative_neighbors_positions=FACES):
        x, y, z = position
        for dx, dy, dz in relative_neighbors_positions:
            yield x + dx, y + dy, z + dz

    def check_neighbors(self, block):
        for other_position in self.neighbors_iterator(block.position):
            block = self.get_block(*other_position)
            if block is None:
                continue
            block.is_exposed = None
            if self.is_exposed(block):
                self.check_spreading_mutable(block)
                if other_position not in self.shown:
                    self.show_block(block)
            else:
                if other_position in self.shown:
                    self.hide_block(other_position)

    def check_spreading_mutable(self, block):
        x, y, z = block.position
        above_position = x, y + 1, z
        if above_position in self \
                or block in self.spreading_mutable_blocks \
                or not self.is_exposed(block):
            return
        if block.blocktype in self.spreading_mutations and self.has_neighbors(
                block.position,
                is_in=(self.spreading_mutations[block.blocktype],),
                diagonals=True):
            self.spreading_mutable_blocks.appendleft(block)

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

    def is_exposed(self, block):
        if block.is_exposed is not None:
            return block.is_exposed

        for other_position in self.neighbors_iterator(block.position):
            if other_position in self:
                other_block = Block(position=other_position,
                                    blocktype=self[other_position])
            else:
                other_block = self.get_block(*other_position)
            if not other_block or other_block.blocktype.transparent:
                block.is_exposed = True
                G.SQL_SESSION.add(block)
                return True

        block.is_exposed = False
        G.SQL_SESSION.add(block)
        return False

    def get_block(self, x, y, z):
        try:
            return G.SQL_SESSION.query(Block).filter_by(x=x, y=y, z=z).one()
        except NoResultFound:
            return
        except MultipleResultsFound:
            warnings.warn('Two or more blocks were unexpectedly found '
                          'at ' + repr((x, y, z)))

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
        if immediate:
            self._hide_block(position)
        else:
            self.enqueue(self._hide_block, position)

    def _hide_block(self, position):
        self.shown.pop(position).delete()

    def show_block(self, block, immediate=True):
        self[block.position] = block.blocktype
        try:
            int(block.pk)
        except ValueError:
            pass
        else:
            self.shown_blocks.append(block.pk)
        if immediate:
            self._show_block(block)
        else:
            self.enqueue(self._show_block, block)

    def _show_block(self, block):
    #    x, y, z = position
        # only show exposed faces
    #    index = 0
        blocktype = block.blocktype
        position = block.position
        vertex_data = blocktype.get_vertices(*position)
        texture_data = blocktype.texture_data
        count = len(texture_data) / 2
        # FIXME: Do something of what follows.
    #    for dx, dy, dz in []:  # FACES:
    #        if (x + dx, y + dy, z + dz) in self:
    #            count -= 8  # 4
    #            i = index * 12
    #            j = index * 8
    #            del vertex_data[i:i + 12]
    #            del texture_data[j:j + 8]
    #        else:
    #            index += 1

        # create vertex list
        batch = self.transparency_batch if blocktype.transparent else self.batch
        self.shown[position] = batch.add(count, GL_QUADS, blocktype.group or self.group,
                                          ('v3f/static', vertex_data),
                                          ('t2f/static', texture_data))

    def show_sector(self, sector, immediate=False):
        if sector in self.shown_sectors:
            return
        self.delete_opposite_task(self._hide_sector, sector)

        if immediate:
            self._show_sector(sector)
        else:
            self.enqueue(self._show_sector, sector, urgent=True)

    def _show_sector(self, sector):
        if sector.is_empty():
            self.terraingen.generate_sector(sector.position)

        for block in sector.get_exposed_blocks().all():
            if block.position not in self.shown and self.is_exposed(block):
                self.show_block(block)

        self.shown_sectors.append(sector)

    def hide_sector(self, sector, immediate=False):
        if immediate:
            self._hide_sector(sector)
        else:
            self.enqueue(self._hide_sector, sector)

    def _hide_sector(self, sector):
        for block in sector.get_blocks():
            if block.position in self.shown:
                self.hide_block(block)

        self.shown_sectors.remove(sector)

    def change_sectors(self):
        xs, ys, zs = sectorize(self.controller.player.position)
        if not Sector.exists_at(xs, ys, zs):
            s = Sector(x=xs, y=ys, z=zs)
            G.SQL_SESSION.add(s)
            self.show_sector(s)
        x, y, z = self.controller.player.position

        d = G.VISIBLE_SECTORS_RADIUS * G.SECTOR_SIZE
        sectors = G.SQL_SESSION.query(Sector)
        if self.shown_sectors:
            sectors = sectors.filter(~Sector.pk.in_([s.pk for s in self.shown_sectors]))
        sectors = sectors.filter(
            Sector.x >= x - d, Sector.x <= x + d,
            Sector.y >= y - d, Sector.y <= y + d,
            Sector.z >= z - d, Sector.z <= z + d).all()

        for sector in sectors:
            self.show_sector(sector)

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

    def delete_opposite_task(self, func, *args, **kwargs):
        opposite_task = func, args, kwargs
        if opposite_task in self.lazy_queue:
            self.lazy_queue.remove(opposite_task)

    def process_queue(self, dt):
        stoptime = time() + G.QUEUE_PROCESS_SPEED
        # Process as much of the queues as we can
        while (self.urgent_queue or self.lazy_queue) and time() < stoptime:
            self.dequeue()

    def process_entire_queue(self):
        while self.urgent_queue or self.lazy_queue:
            self.dequeue()

    def content_update(self, dt):
        # Updates spreading
        # TODO: This is too simple
        self.spreading_time += dt
        if self.spreading_time >= G.SPREADING_MUTATION_DELAY:
            self.spreading_time = 0.0
            if self.spreading_mutable_blocks:
                block = self.spreading_mutable_blocks.pop()
                position = block.position
                self.add_block(position,
                               self.spreading_mutations[self[position]])
