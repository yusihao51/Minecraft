# Imports, sorted alphabetically.

# Python packages
from math import sin, cos, pi

# Third-party packages
import pyglet
from pyglet.gl import *
import globals as G

# Modules from this project
# Nothing for now...


__all__ = (
    'Skydome',
)

# radius of the sun (central angle)
SUN_RADIUS = pi / 6

class Skydome(object):
    def __init__(self, filename, brightness=1.0, size=1.0, direction=0):
        self.direction = direction
        self.image = pyglet.image.load(filename)
        self.color = [brightness] * 3

        self.sun_image = G.texture_pack_list.selected_texture_pack.load_texture(['environment', 'sun.png'])
        self.size = size

        self.time_of_day = 0.0

        self.sun_angle = 0

        t = self.image.get_texture().tex_coords
        u = t[3]
        pixel_width = u / self.image.width
        v = t[7]

        ustart = pixel_width
        uend = u - pixel_width
        vstart = 0
        vend = v

        vertex = list()
        uvs = list()
        count = 0

        def sphere_vert(i, j):
            i = i / 10.0
            j = j / 40.0
            s = sin(pi * i * 0.5)
            z = cos(pi * i * 0.5) * size
            x = sin(pi * j * 2.0) * s * size
            y = cos(pi * j * 2.0) * s * size

            u = (j * (uend - ustart)) + ustart
            v_length = vend - vstart
            v = (v_length-i * v_length) + vstart
            return (x, y, z), (u, v)
    
        for j in range(40):
            v, uv = sphere_vert(0, j)
            vertex.extend(v)
            uvs.extend(uv)
            v, uv = sphere_vert(1, j)
            vertex.extend(v)
            uvs.extend(uv)
            v, uv = sphere_vert(1, j+1)
            vertex.extend(v)
            uvs.extend(uv)
            count += 3
      
        for i in range(1, 10):
            for j in range(40):
                v, uv = sphere_vert(i, j)
                vertex.extend(v)
                uvs.extend(uv)
                v, uv = sphere_vert(i+1, j)
                vertex.extend(v)
                uvs.extend(uv)
                v, uv = sphere_vert(i+1, j+1)
                vertex.extend(v)
                uvs.extend(uv)
                
                v, uv = sphere_vert(i, j)
                vertex.extend(v)
                uvs.extend(uv)
                v, uv = sphere_vert(i+1, j+1)
                vertex.extend(v)
                uvs.extend(uv)
                v, uv = sphere_vert(i, j+1)
                vertex.extend(v)
                uvs.extend(uv)

                count += 6

        self.display = pyglet.graphics.vertex_list(count,
            ('v3f/static', vertex),
            ('t2f/static', uvs),
        )

    def sun_vertex(self, sun_angle):
        vertex_list = []
        uv_list = []
        r_sun_d2 = SUN_RADIUS / 2

        # x, y, z
        top_left = (-self.size * sin(r_sun_d2), self.size * cos(sun_angle + r_sun_d2), self.size * sin(sun_angle + r_sun_d2))
        top_right =  (self.size * sin(r_sun_d2), self.size * cos(sun_angle + r_sun_d2), self.size * sin(sun_angle + r_sun_d2))
        bottom_left = (-self.size * sin(r_sun_d2), self.size * cos(sun_angle - r_sun_d2), self.size * sin(sun_angle - r_sun_d2))
        bottom_right = (self.size * sin(r_sun_d2), self.size * cos(sun_angle - r_sun_d2), self.size * sin(sun_angle - r_sun_d2))
        vert_list = [bottom_left, top_right, top_left, bottom_right, top_right, bottom_left]
        for vert in vert_list:
            vertex_list.extend(vert)

        # u, v
        top_left = (0, 1)
        top_right = (1, 1)
        bottom_left = (0, 0)
        bottom_right = (1, 0)

        vert_list = [bottom_left, top_right, top_left, bottom_right, top_right, bottom_left]
        for vert in vert_list:
            uv_list.extend(vert)

        return pyglet.graphics.vertex_list(6,
            ('v3f/static', vertex_list),
            ('t2f/static', uv_list),
        )

    def draw(self):
        glPushMatrix()
        # draw skydome
        glBindTexture(self.image.texture.target, self.image.texture.id)
        glEnable(self.image.texture.target)
        glColor3f(*self.color)
        glRotatef(-self.direction, 0, 0, 1)
        self.display.draw(GL_TRIANGLES)
        glDisable(self.image.texture.target)
        # draw the sun
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_DST_ALPHA)
        glBindTexture(self.sun_image.texture.target, self.sun_image.texture.id)
        glEnable(self.sun_image.texture.target)
        self.sun_vertex(self.sun_angle).draw(GL_TRIANGLES)
        glDisable(self.sun_image.texture.target)
        glDisable(GL_BLEND)
        glPopMatrix()

    def update_time_of_day(self, time_of_day):
        self.time_of_day = time_of_day
        self.sun_angle = 2 * pi * time_of_day / 24.0 - pi / 4
