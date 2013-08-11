# Imports, sorted alphabetically.

# Python packages
from math import radians, cos, sin

# Third-party packages
from pyglet.gl import *

# Modules from this project
# Nothing for now...


__all__ = (
    'Camera3D',
)


class Camera3D(object):
    def __init__(self, target=None):
        self.target = target
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.x_rotation = 0.0
        self.y_rotation = 0.0

        # if possible, we should use sinf and cosf from cython
        self.has_sinf = True
        try: sinf(1)
        except NameError: self.has_sinf = False

    def rotate(self, x, y):
        self.x_rotation = x
        self.y_rotation = y

    def update(self, dt):
        if self.target:
            self.x, self.y, self.z = self.target.position

    def transform(self):
        glRotatef(self.x_rotation, 0, 1, 0)
        x_r = radians(self.x_rotation)
        
        if self.has_sinf:
            glRotatef(-self.y_rotation, cosf(x_r), 0, sinf(x_r))
        else: 
            glRotatef(-self.y_rotation, cos(x_r), 0, sin(x_r))

        glTranslatef(-self.x, -self.y, -self.z)

    def look(self):
        glRotatef(self.x_rotation, 0, 1, 0)
        x_r = radians(self.x_rotation)

        if self.has_sinf:
            glRotatef(-self.y_rotation, cosf(x_r), 0, sinf(x_r))
        else:
            glRotatef(-self.y_rotation, cos(x_r), 0, sin(x_r))

        glTranslatef(0, -40.0, 0)
        glRotatef(-90.0, 1, 0, 0)
