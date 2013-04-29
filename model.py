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


def get_texture_coordinates(x, y, height, width):
    if x == -1 and y == -1:
        return ()
    return x, y, x + width, y, x + width, y + height, x, y + width

# not good at calculating coordinate things...there may be something wrong...
class BoxModel(object):
    # top bottom left right front back
    textures = [(-1, -1), (-1, -1), (-1, -1), (-1, -1), (-1, -1), (-1, -1)]
    texture_data = None
    display = None

    def __init__(self, position1, position2, filename):
        self.image = pyglet.image.load(filename)

        self.xpos1, self.ypos1, self.zpos1 = position1
        self.xpos2, self.ypos2, self.zpos2 = position2

        self.texture_data = []
        self.texture_data += get_texture_coordinates(self.textures[0][0], self.textures[0][-1], self.xpos2 - self.xpos1, self.zpos2 - self.zpos1)
        self.texture_data += get_texture_coordinates(self.textures[1][0], self.textures[1][-1], self.xpos2 - self.xpos1, self.zpos2 - self.zpos1)
        self.texture_data += get_texture_coordinates(self.textures[2][0], self.textures[2][-1], self.ypos2 - self.ypos1, self.zpos2 - self.zpos1)
        self.texture_data += get_texture_coordinates(self.textures[3][0], self.textures[3][-1], self.ypos2 - self.ypos1, self.zpos2 - self.zpos1)
        self.texture_data += get_texture_coordinates(self.textures[4][0], self.textures[4][-1], self.ypos2 - self.ypos1, self.xpos2 - self.xpos1)
        self.texture_data += get_texture_coordinates(self.textures[-1][0], self.textures[-1][-1], self.ypos2 - self.ypos1, self.xpos2 - self.xpos1)
        
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

    def draw(self):
        glPushMatrix()
        glBindTexture(self.image.texture.target, self.image.texture.id)
        glEnable(self.image.texture.target)
        self.display = pyglet.graphics.vertex_list(count,
            ('v3f/static', self.get_vertices()),
            ('t2f/static', self.texture_data),
        )
        self.display.draw(GL_QUAD)
        glPopMatrix()

# with BoxModel, it will be easier to create player model.
# because player model is made of many boxes.
