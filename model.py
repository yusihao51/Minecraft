# Imports, sorted alphabetically.

# Python packages
# Nothin for now...

# Third-party packages
import pyglet
from pyglet.gl import *

# Modules from this project
# Nothing for now...

__all__ = (
    'BoxModel',
)


def get_texture_coordinates(x, y, height, width, texture_height, texture_width):
    if x == -1 and y == -1:
        return ()
    x = x / float(texture_width)
    y = y / float(texture_height)
    height = height / float(texture_height)
    width = width / float(texture_width)
    return x, y, x + width, y, x + width, y + height, x, y + height

# not good at calculating coordinate things...there may be something wrong...
class BoxModel(object):
    # top bottom left right front back
    textures = [(-1, -1), (-1, -1), (-1, -1), (-1, -1), (-1, -1), (-1, -1)]
    texture_data = None
    display = None

    def __init__(self, position, length, width, height, filename, pixel_length, pixel_width, pixel_height, texture_height, texture_width):
        self.image = pyglet.image.load(filename)

        self.xpos1, self.ypos1, self.zpos1 = position
        self.xpos2 = self.xpos1 + length
        self.ypos2 = self.ypos1 + height
        self.zpos2 = self.zpos1 + width 
        self.height, self.width, self.height = height, width, height
        self.pixel_height, self.pixel_width, self.pixel_height = pixel_height, pixel_width, pixel_height
        self.texture_height = texture_height
        self.texture_width = texture_width

    def get_texture_data(self):
        texture_data = []
        texture_data += get_texture_coordinates(self.textures[0][0], self.textures[0][-1], self.pixel_height, self.pixel_width, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[1][0], self.textures[1][-1], self.pixel_height, self.pixel_width, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[2][0], self.textures[2][-1], self.pixel_width, self.pixel_height, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[3][0], self.textures[3][-1], self.pixel_width, self.pixel_height, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[4][0], self.textures[4][-1], self.pixel_height, self.pixel_width, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[-1][0], self.textures[-1][-1], self.pixel_height, self.pixel_width, self.texture_height, self.texture_width)
        return texture_data

    def update_texture_data(self, textures):
        self.textures = textures
        self.texture_data = self.get_texture_data()

    def get_vertices(self):
        xm = self.xpos1
        xp = self.xpos2
        ym = self.ypos1
        yp = self.ypos2
        zm = self.zpos1
        zp = self.zpos2
        
        vertices = (
            xm, yp, zm,   xm, yp, zp,   xp, yp, zp,   xp, yp, zm,  # top
            xm, ym, zm,   xp, ym, zm,   xp, ym, zp,   xm, ym, zp,  # bottom
            xm, ym, zm,   xm, ym, zp,   xm, yp, zp,   xm, yp, zm,  # left
            xp, ym, zp,   xp, ym, zm,   xp, yp, zm,   xp, yp, zp,  # right
            xm, ym, zp,   xp, ym, zp,   xp, yp, zp,   xm, yp, zp,  # front
            xp, ym, zm,   xm, ym, zm,   xm, yp, zm,   xp, yp, zm,  # back
        )
        return vertices

    def update_position(self, position):
        self.xpos1, self.ypos1, self.zpos1 = position
        self.xpos2 = self.xpos1 + self.length
        self.ypos2 = self.ypos1 + self.height
        self.zpos2 = self.zpos1 + self.width 

    def draw(self):
        glPushMatrix()
        glBindTexture(self.image.texture.target, self.image.texture.id)
        glEnable(self.image.texture.target)
        self.display = pyglet.graphics.vertex_list(24,
            ('v3f/static', self.get_vertices()),
            ('t2f/static', self.texture_data),
        )
        self.display.draw(GL_QUADS)
        glPopMatrix()

class PlayerModel(object):
    def __init__(self, position):
        # head
        self.position = position
        self.head = BoxModel(position, 1, 1, 1, 'resources/textures/char.png', 32, 32, 32, 128, 256)
        self.head.update_texture_data([(32, 96), (64, 96), (0, 64), (64, 64), (32, 64), (96, 64)])

    def draw(self):
        self.head.draw()