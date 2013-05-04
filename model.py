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
    x /= float(texture_width)
    y /= float(texture_height)
    height /= float(texture_height)
    width /= float(texture_width)
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
        self.length, self.width, self.height = length, width, height
        self.pixel_length, self.pixel_width, self.pixel_height = pixel_length, pixel_width, pixel_height
        self.texture_height = texture_height
        self.texture_width = texture_width

    def get_texture_data(self):
        texture_data = []
        texture_data += get_texture_coordinates(self.textures[0][0], self.textures[0][-1], self.pixel_width, self.pixel_length, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[1][0], self.textures[1][-1], self.pixel_width, self.pixel_length, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[2][0], self.textures[2][-1], self.pixel_height, self.pixel_width, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[3][0], self.textures[3][-1], self.pixel_height, self.pixel_width, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[4][0], self.textures[4][-1], self.pixel_height, self.pixel_length, self.texture_height, self.texture_width)
        texture_data += get_texture_coordinates(self.textures[-1][0], self.textures[-1][-1], self.pixel_height, self.pixel_length, self.texture_height, self.texture_width)
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

BODY_LENGTH = float(1)
BODY_WIDTH = BODY_LENGTH / 2
BODY_HEIGHT = BODY_LENGTH * 3 / 2
HEAD_LENGTH = BODY_LENGTH
HEAD_WIDTH = HEAD_LENGTH
HEAD_HEIGHT = HEAD_LENGTH
ARM_HEIGHT = BODY_HEIGHT
ARM_LENGTH = BODY_WIDTH
ARM_WIDTH = BODY_WIDTH
LEG_HEIGHT = BODY_HEIGHT
LEG_LENGTH = BODY_WIDTH
LEG_WIDTH = BODY_WIDTH

class PlayerModel(object):
    def __init__(self, position):
        self.position = None
        self.body_pos = None
        self.head_pos = None
        self.left_arm_pos = None
        self.right_arm_pos = None
        self.left_leg_pos = None
        self.right_leg_pos = None

        self.update_position(position, init=True)
        # head
        self.head = BoxModel(self.head_pos, HEAD_LENGTH, HEAD_WIDTH, HEAD_HEIGHT, 'resources/textures/char.png', 32, 32, 32, 128, 256)
        self.head.update_texture_data([(32, 96), (64, 96), (0, 64), (64, 64), (32, 64), (96, 64)])
        # body
        self.body = BoxModel(self.body_pos, BODY_LENGTH, BODY_WIDTH, BODY_HEIGHT, 'resources/textures/char.png', 32, 16, 48, 128, 256)
        self.body.update_texture_data([(80, 48), (112, 48), (64, 0), (112, 0), (80, 0), (128, 0)])
        # left/right arm
        self.left_arm = BoxModel(self.left_arm_pos, ARM_LENGTH, ARM_WIDTH, ARM_HEIGHT, 'resources/textures/char.png', 16, 16, 48, 128, 256)
        self.left_arm.update_texture_data([(176, 48), (176 + 16, 48), (176, 0), (176 + 32, 0), (176 - 16, 0), (176 + 16, 0)])
        self.right_arm = BoxModel(self.right_arm_pos, ARM_LENGTH, ARM_WIDTH, ARM_HEIGHT, 'resources/textures/char.png', 16, 16, 48, 128, 256)
        self.right_arm.update_texture_data([(176, 48), (176 + 16, 48), (176, 0), (176 + 32, 0), (176 - 16, 0), (176 + 16, 0)])
        # left/right leg
        self.left_leg = BoxModel(self.left_leg_pos, LEG_LENGTH, LEG_WIDTH, LEG_HEIGHT, 'resources/textures/char.png', 16, 16, 48, 128, 256)
        self.left_leg.update_texture_data([(16, 48), (16 + 16, 48), (0, 0), (32, 0), (16, 0), (48, 0)])
        self.right_leg = BoxModel(self.right_leg_pos, LEG_LENGTH, LEG_WIDTH, LEG_HEIGHT, 'resources/textures/char.png', 16, 16, 48, 128, 256)
        self.right_leg.update_texture_data([(16, 48), (16 + 16, 48), (0, 0), (32, 0), (16, 0), (48, 0)])

    def update_position(self, position, init=False):
        self.position = position
        self.body_pos = (position[0] - BODY_LENGTH / 2, position[1] - BODY_HEIGHT / 2, position[-1] - BODY_WIDTH / 2)
        self.head_pos = (position[0] - HEAD_LENGTH / 2, position[1] + BODY_HEIGHT / 2, position[-1] - HEAD_WIDTH / 2)
        self.left_arm_pos = (position[0] - BODY_LENGTH / 2 - ARM_LENGTH, position[1] - BODY_HEIGHT / 2, position[-1] - BODY_WIDTH / 2)
        self.right_arm_pos = (position[0] + BODY_LENGTH / 2, position[1] - BODY_HEIGHT / 2, position[-1] - BODY_WIDTH / 2)
        self.left_leg_pos = (self.body_pos[0], self.body_pos[1] - LEG_HEIGHT, self.body_pos[-1])
        self.right_leg_pos = (self.body_pos[0] + LEG_LENGTH, self.body_pos[1] - LEG_HEIGHT, self.body_pos[-1])

        if not init:
            self.head.update_position(self.head_pos)
            self.body.update_position(self.body_pos)
            self.left_arm.update_position(self.left_arm_pos)
            self.right_arm.update_position(self.right_arm_pos)
            self.left_leg.update_position(self.left_leg_pos)
            self.right_leg.update_position(self.right_leg_pos)

    def draw(self):
        self.head.draw()
        self.body.draw()
        self.left_arm.draw()
        self.right_arm.draw()
        self.left_leg.draw()
        self.right_leg.draw()