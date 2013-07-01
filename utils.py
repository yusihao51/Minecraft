# Imports, sorted alphabetically.

# Python packages
import os
import struct

# Third-party packages
import pyglet
from pyglet.gl import *

# Modules from this project
import globals as G


__all__ = (
    'load_image', 'image_sprite', 'hidden_image_sprite', 'vec', 'FastRandom',
    'init_resources', 'init_font', 'get_block_icon',
    'FACES', 'FACES_WITH_DIAGONALS', 'normalize_float', 'normalize',
    'sectorize', 'TextureGroup', 'make_nbt_from_dict', 'extract_nbt'
)


def load_image(*args):
    path = os.path.join(*args)
    return pyglet.image.load(os.path.join(*args)) if os.path.isfile(
        path) else None


def image_sprite(image, batch, group, x=0, y=0, width=None, height=None):
    if image is None or batch is None or group is None:
        return None
    width = width or image.width
    height = height or image.height
    if isinstance(group, int):
        group = pyglet.graphics.OrderedGroup(group)
    return pyglet.sprite.Sprite(image.get_region(x, y, width, height),
                                batch=batch, group=group)


def hidden_image_sprite(*args, **kwargs):
    sprite = image_sprite(*args, **kwargs)
    if sprite:
        sprite.visible = False
    return sprite


def vec(*args):
    """Creates GLfloat arrays of floats"""
    return (GLfloat * len(args))(*args)


# fast math algorithms
class FastRandom(object):
    def __init__(self, seed):
        self.seed = seed

    def randint(self):
        self.seed = (214013 * self.seed + 2531011)
        return (self.seed >> 16) & 0x7FFF


def init_resources():
    init_font('resources/fonts/Chunkfive.ttf', 'ChunkFive Roman')
    init_font('resources/fonts/slkscr.ttf', 'Silkscreen Normal')


def init_font(filename, fontname):
    pyglet.font.add_file(filename)
    pyglet.font.load(fontname)


def get_block_icon(block, icon_size, world):
    print block.id.filename()
    block_icon = G.texture_pack_list.selected_texture_pack.load_texture(block.id.filename()) \
        or (block.group or world.group).texture.get_region(
            int(block.texture_data[2 * 8] * G.TILESET_SIZE) * icon_size,
            int(block.texture_data[2 * 8 + 1] * G.TILESET_SIZE) * icon_size,
            icon_size,
            icon_size)
    return block_icon


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

# Named Binary Tag
def make_int_packet(i):
    return struct.pack('i', i)

def extract_int_packet(packet):
    return packet[4:], struct.unpack('i', packet[:4])[0]

def make_string_packet(s):
    return struct.pack('i', len(s)) + s

def extract_string_packet(packet):
    strlen = struct.unpack('i', packet[:4])[0]
    packet = packet[4:]
    s = packet [:strlen]
    packet = packet[strlen:]
    return packet, s

def make_packet(obj):
    if type(obj) == int:
        return make_int_packet(obj)
    elif type(obj) == str:
        return make_string_packet(obj)
    else:
        print('make_packet: unsupported type: ' + str(type(obj)))
        return None

def extract_packet(packet):
    tag, packet = struct.unpack('B', packet[:1])[0], packet[1:]
    if tag == 0:
        return extract_int_packet(packet)
    elif tag == 1:
        return extract_string_packet(packet)

def type_tag(t):
    tag = 0
    if t == int:
        tag = 0
    elif t == str:
        tag = 1
    return struct.pack('B', tag)

def make_nbt_from_dict(d):
    packet = ''
    for key in d.keys():
        packet += make_string_packet(key) + type_tag(type(d[key])) + make_packet(d[key])
    return packet

def extract_nbt(nbt):
    result = {}
    while len(nbt) > 0:
        nbt, key = extract_string_packet(nbt)
        nbt, value = extract_packet(nbt)
        result[key] = value

    return result
