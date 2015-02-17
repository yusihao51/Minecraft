# -*- coding: utf-8 -*-

# Imports, sorted alphabetically.

# Python packages
import os
import socket
import subprocess
import sys
import datetime
from math import sin, pi

# Third-party packages
import pyglet
from pyglet.text import Label
from pyglet.gl import *

# Modules from this project
import globals as G
from gui import frame_image, Rectangle, backdrop, Button, button_image, \
    button_highlighted, ToggleButton, TextWidget, ScrollbarWidget, \
    button_disabled, resize_button_image
from textures import TexturePackList
from utils import image_sprite, load_image

__all__ = (
    'View', 'MainMenuView', 'OptionsView', 'ControlsView', 'TexturesView', 'MultiplayerView'
)

class Layout(object):
    def __init__(self, x, y):
        self.components = []
        self._position = x, y
        self.width, self.height = 0, 0

    def add(self, component):
        self.components.append(component)

    def _set_component_position(self, component, x, y):
        try:
            component.position = x, y
        except AttributeError:
            try:
                component.resize(x, y, component.width, component.height)
            except AttributeError:
                component.x, component.y = x, y

    @property
    def position(self):
        return _position

    @position.setter
    def position(self, value):
        self._position = value


class VerticalLayout(Layout):
    def add(self, component):
        self.components.append(component)
        self.height += component.height + 10
        self.width = max(component.width, self.width)
        self._put_components()

    def _put_components(self):
        c_x, c_y = self._position[0], self._position[-1] + self.height
        for component in self.components:
            self._set_component_position(component, c_x, c_y)
            c_y -= component.height + 10

    @property
    def position(self):
        return _position

    @position.setter
    def position(self, value):
        self._position = value
        self._put_components()


class HorizontalLayout(Layout):
    def add(self, component):
        self.components.append(component)
        self.width += component.width + 10
        self.height = max(component.height, self.height)
        self._put_components()

    def _put_components(self):
        c_x, c_y = self._position[0], self._position[-1]
        for component in self.components:
            self._set_component_position(component, c_x, c_y)
            c_x += component.width + 10

    @property
    def position(self):
        return _position

    @position.setter
    def position(self, value):
        self._position = value
        self._put_components()


class View(pyglet.event.EventDispatcher):
    def __init__(self, controller):
        super(View, self).__init__()

        self.controller = controller
        self.batch = pyglet.graphics.Batch()
        self.buttons = []

    def setup(self):
        pass

    def add_handlers(self):
        self.setup()
        self.controller.window.push_handlers(self)

    def pop_handlers(self):
        self.controller.window.set_mouse_cursor(None)
        self.controller.window.pop_handlers()

    def update(self, dt):
        pass

    def clear(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def on_mouse_press(self, x, y, button, modifiers):
        self.dispatch_event('on_mouse_click', x, y, button, modifiers)

    def on_mouse_motion(self, x, y, dx, dy):
        cursor = None
        for button in self.buttons:
            if button.enabled:
                if button.highlighted:
                    button.highlighted = False
                    button.draw()
                if button.hit_test(x, y):
                    button.highlighted = True
                    button.draw()
                    cursor = self.controller.window.get_system_mouse_cursor(pyglet.window.Window.CURSOR_HAND)
        self.controller.window.set_mouse_cursor(cursor)

    def on_draw(self):
        self.clear()
        glColor3d(1, 1, 1)
        self.controller.set_2d()
        self.batch.draw()

View.register_event_type('on_mouse_click')


class MenuView(View):
    def setup(self):
        self.group = pyglet.graphics.OrderedGroup(3)
        self.labels_group = pyglet.graphics.OrderedGroup(4)

        self.layout = Layout(0, 0)

        image = frame_image
        self.frame_rect = Rectangle(0, 0, image.width, image.height)
        self.background = G.texture_pack_list.selected_texture_pack.load_texture(['gui', 'background.png'])
        self.background = self.background.get_texture()
        self.background.height = 64
        self.background.width = 64
        self.frame = Rectangle(0, 0, image.width, image.height)

        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    def Button(self, x=0, y=0, width=400, height=40, image=button_image, image_highlighted=button_highlighted, caption="Unlabeled", batch=None, group=None, label_group=None, font_name='ChunkFive Roman', on_click=None, enabled=True):
        button = Button(self, x=x, y=y, width=width, height=height, image=resize_button_image(image, 400, width), image_highlighted=resize_button_image(image_highlighted, 400, width), caption=caption, batch=(batch or self.batch), group=(group or self.group), label_group=(label_group or self.labels_group), font_name=font_name, enabled=enabled)
        if on_click:
            button.push_handlers(on_click=on_click)
        return button

    def ToggleButton(self, x=0, y=0, width=400, height=40, image=button_image, image_highlighted=button_highlighted, caption="Unlabeled", batch=None, group=None, label_group=None, font_name='ChunkFive Roman', on_click=None, on_toggle=None, enabled=True):
        button = ToggleButton(self, x=x, y=y, width=width, height=height, image=resize_button_image(image, 400, width), image_highlighted=resize_button_image(image_highlighted, 400, width), caption=caption, batch=(batch or self.batch), group=(group or self.group), label_group=(label_group or self.labels_group), font_name=font_name, enabled=enabled)
        if on_click:
            button.push_handlers(on_click=on_click)
        if on_toggle:
            button.push_handlers(on_toggle=on_toggle)
        return button

    def Scrollbar(self, x=0, y=0, width=400, height=40, sb_width=40, sb_height=40, style=1, background_image=button_disabled, scrollbar_image=button_image, caption="Test", font_size=12, font_name=G.DEFAULT_FONT, batch=None, group=None, label_group=None, pos=0, on_pos_change=None):
        sb = ScrollbarWidget(self.controller.window, x=x, y=y, width=width, height=height,
                 sb_width=sb_width, sb_height=sb_height,
                 style=style, 
                 background_image=resize_button_image(background_image, 400, width),
                 scrollbar_image=resize_button_image(scrollbar_image, 400, sb_width), 
                 caption=caption, font_size=font_size, font_name=font_name,
                 batch=(batch or self.batch), group=(group or self.group), label_group=(label_group or self.labels_group),
                 pos=pos, on_pos_change=on_pos_change)
        return sb

    def draw_background(self):
        glBindTexture(self.background.target, self.background.id)
        glEnable(self.background.target)
        glColor4f(0.3, 0.3, 0.3, 1.0)

        width = float(self.controller.window.get_size()[0])
        height = float(self.controller.window.get_size()[1])
        bg_width = self.background.width
        bg_height = self.background.height
        vert_list = [0.0, 0.0, 0.0, width, 0.0, 0.0, width, height, 0.0, 0.0, height, 0.0]
        uv_list = [0.0, 0.0, width / bg_width, 0.0, width / bg_width, height / bg_height, 0.0, height / bg_height]
        l = pyglet.graphics.vertex_list(4,
            ('v3f/static', vert_list),
            ('t2f/static', uv_list),
        )
        l.draw(GL_QUADS)
        glDisable(self.background.target)

    def on_draw(self):
        self.clear()
        glColor3d(1, 1, 1)
        self.draw_background()
        self.controller.set_2d()
        self.batch.draw()

    def on_resize(self, width, height):
        self.frame.x, self.frame.y = (width - self.frame.width) / 2, (height - self.frame.height) / 2
        self.layout.position = (width - self.layout.width) / 2, self.frame.y


class MainMenuView(MenuView):
    def setup(self):
        self.group = pyglet.graphics.OrderedGroup(3)
        self.labels_group = pyglet.graphics.OrderedGroup(4)

        image = frame_image
        self.layout = VerticalLayout(0, 0)
        # Custom background
        self.background = None
        self.frame_rect = Rectangle(0, 0, self.controller.window.get_size()[0], image.height)
        self.frame = Rectangle(0, 0, self.controller.window.get_size()[0], image.height)

        width, height = self.controller.window.width, self.controller.window.height

        self.label = Label(G.APP_NAME, font_name='ChunkFive Roman', font_size=50, x=width/2, y=self.frame.y + self.frame.height,
            anchor_x='center', anchor_y='top', color=(255, 255, 255, 255), batch=self.batch,
            group=self.labels_group)
        self.label.height = self.label.content_height
        self.layout.add(self.label)

        button = self.Button(caption=G._("Singleplayer"),on_click=self.controller.start_singleplayer_game)
        self.layout.add(button)
        self.buttons.append(button)
        button = self.Button(caption=G._("Multiplayer"),on_click=self.controller.multiplayer)
        self.layout.add(button)
        self.buttons.append(button)
        button = self.Button(caption=G._("Options..."),on_click=self.controller.game_options)
        self.layout.add(button)
        self.buttons.append(button)
        button = self.Button(caption=G._("Exit game"),on_click=self.controller.exit_game)
        self.layout.add(button)
        self.buttons.append(button)

        # Splash text
        self.splash_text = 'Hello!'

        now = datetime.datetime.now()
        if now.month == 1 and now.day == 1:
            self.splash_text = 'Happy new year!'

        self.splash_text_label = Label(self.splash_text, font_name='Arial', font_size=30, x=self.label.x, y=self.label.y,
            anchor_x='center', anchor_y='top', color=(255, 255, 0, 255),
            group=self.labels_group)

        self.on_resize(width, height)

        # Panorama
        self.panorama = [G.texture_pack_list.selected_texture_pack.load_texture(['title', 'bg', 'panorama' + str(x) + '.png']) for x in range(6)]
        self.panorama_timer = 0

        pyglet.clock.schedule_interval(self.update_panorama_timer, .05)
        self.blur_texture = pyglet.image.Texture.create(256, 256)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def update_panorama_timer(self, dt):
        self.panorama_timer += 1

    def draw_panorama(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluPerspective(120.0, 1.0, 0.05, 10.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glRotatef(180.0, 1.0, 0.0, 0.0)
        glEnable(GL_BLEND)
        glDisable(GL_ALPHA_TEST)
        glDisable(GL_CULL_FACE)
        glDepthMask(False)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glPushMatrix()
        glRotatef(sin(float(self.panorama_timer) / 400.0) * 25.0 + 20.0, 1.0, 0.0, 0.0)
        glRotatef(-float(self.panorama_timer) * 0.1, 0.0, -1.0, 0.0)

        # 6 faces
        for i in range(6):
            glPushMatrix()

            if i == 1:
                glRotatef(90.0, 0.0, 1.0, 0.0)

            elif i == 2:
                glRotatef(180.0, 0.0, 1.0, 0.0)

            elif i == 3:
                glRotatef(-90.0, 0.0, 1.0, 0.0)

            elif i == 4:
                glRotatef(90.0, 1.0, 0.0, 0.0)

            elif i == 5:
                glRotatef(-90.0, 1.0, 0.0, 0.0)

            glBindTexture(self.panorama[i].texture.target, self.panorama[i].texture.id)
            glEnable(self.panorama[i].texture.target)
            vert_list = [-1.0, -1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0]
            uv_list = [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
            l = pyglet.graphics.vertex_list(4,
                ('v3f/static', vert_list),
                ('t2f/static', uv_list),
            )
            l.draw(GL_QUADS)
            glDisable(self.panorama[i].texture.target)
            glPopMatrix()

        glPopMatrix()
        glColorMask(True, True, True, False)

        glColorMask(True, True, True, True)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glDepthMask(True)
        glEnable(GL_CULL_FACE)
        glEnable(GL_ALPHA_TEST)
        glEnable(GL_DEPTH_TEST)

    def render_to_texture(self):
        glViewport(0, 0, 256, 256)
        self.draw_panorama()
        glBindTexture(GL_TEXTURE_2D, self.blur_texture.id)
        glCopyTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE, 0, 0, 256, 256, 0)

        glClearColor(0.0, 0.0, 0.5, 0.5)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(0, 0, self.controller.window.get_size()[0], self.controller.window.get_size()[1])

    def draw_blur(self, times=5):
        alpha = 0.5

        glDisable(GL_TEXTURE_GEN_S)
        glDisable(GL_TEXTURE_GEN_T)

        glEnable(GL_TEXTURE_2D)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glBindTexture(GL_TEXTURE_2D, self.blur_texture.id)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.controller.window.get_size()[0] , self.controller.window.get_size()[1] , 0, -1, 1 )
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        alphainc = alpha / float(times)
        spost = 0
        width = self.controller.window.get_size()[0]
        height = self.controller.window.get_size()[1]
        glBegin(GL_QUADS)
        for _ in range(times):
            glColor4f(1.0, 1.0, 1.0, alpha)

            glTexCoord2f(0, 1)
            glVertex2f(0, 0)

            glTexCoord2f(0, 0)
            glVertex2f(0, height)

            glTexCoord2f(1, 0)
            glVertex2f(width, height)

            glTexCoord2f(1, 1)
            glVertex2f(width, 0)

            alpha = alpha - alphainc
            if alpha < 0:
                alpha = 0

        glEnd()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glBindTexture(GL_TEXTURE_2D, 0)

    def draw_splash_text(self):
        glPushMatrix()
        glTranslatef(float(self.controller.window.get_size()[0] / 2 - self.label.content_width / 2), -float(self.controller.window.get_size()[1] / 3), 0.0)
        glRotatef(20.0, 0.0, 0.0, 1.0)
        self.splash_text_label.draw()
        glPopMatrix()

    def on_resize(self, width, height):
        MenuView.on_resize(self, width, height)
        self.label.y = self.frame.y + self.frame.height - 15
        self.label.x = width / 2
        self.splash_text_label.x = self.label.x
        self.splash_text_label.y = self.label.y

    def on_draw(self):
        self.clear()
        glColor3d(1, 1, 1)
        #self.render_to_texture()
        self.draw_panorama()
        #self.draw_blur()
        self.controller.set_2d()
        self.batch.draw()
        self.draw_splash_text()

class OptionsView(MenuView):
    def setup(self):
        MenuView.setup(self)
        width, height = self.controller.window.width, self.controller.window.height

        self.layout = VerticalLayout(0, 0)

        textures_enabled = len(G.texture_pack_list.available_texture_packs) > 1

        self.text_input = TextWidget(self.controller.window, G.USERNAME, 0, 0, width=160, height=20, font_name='Arial', batch=self.batch)
        self.controller.window.push_handlers(self.text_input)
        self.text_input.focus()
        self.text_input.caret.mark = len(self.text_input.document.text)  # Don't select the whole text
        def text_input_callback(symbol, modifier):
            G.USERNAME = self.text_input.text
        self.text_input.push_handlers(key_released=text_input_callback)

        hl = HorizontalLayout(0, 0)
        sb = self.Scrollbar(x=0, y=0, width=300, height=40, sb_width=20, sb_height=40, caption="Music")
        hl.add(sb)

        def change_sound_volume(pos):
            print G.EFFECT_VOLUME
            G.EFFECT_VOLUME = float(float(pos) / 100)
        sb = self.Scrollbar(x=0, y=0, width=300, height=40, sb_width=20, sb_height=40, caption="Sound", pos=int(G.EFFECT_VOLUME * 100), on_pos_change=change_sound_volume)
        hl.add(sb)
        self.layout.add(hl)

        hl = HorizontalLayout(0, 0)
        button = self.Button(width=300, caption=G._("Controls..."), on_click=self.controller.controls)
        hl.add(button)
        self.buttons.append(button)
        button = self.Button(width=300, caption=G._("Textures"), on_click=self.controller.textures, enabled=textures_enabled)
        hl.add(button)
        self.buttons.append(button)
        self.layout.add(hl)

        button = self.Button(width=610, caption=G._("Done"), on_click=self.controller.main_menu)
        self.layout.add(button)
        self.buttons.append(button)

        self.label = Label('Options', font_name='ChunkFive Roman', font_size=25, x=width/2, y=self.frame.y + self.frame.height,
            anchor_x='center', anchor_y='top', color=(255, 255, 255, 255), batch=self.batch,
            group=self.labels_group)

        self.on_resize(width, height)

    def on_resize(self, width, height):
        MenuView.on_resize(self, width, height)
        self.text_input.resize(x=self.frame.x + (self.frame.width - self.text_input.width) / 2 + 5, y=self.frame.y + (self.frame.height) / 2 + 75, width=150)


class ControlsView(MenuView):
    def setup(self):
        MenuView.setup(self)
        width, height = self.controller.window.width, self.controller.window.height

        self.layout = VerticalLayout(0, 0)

        self.key_buttons = []
        for identifier in ('move_backward', 'move_forward', 'move_left', 'move_right'):
            button = self.ToggleButton(width=200, caption=pyglet.window.key.symbol_string(getattr(G, identifier.upper() + '_KEY')))
            button.id = identifier
            self.buttons.append(button)
            self.key_buttons.append(button)
        self.button_return = self.Button(caption=G._("Done"),on_click=self.controller.game_options)
        self.buttons.append(self.button_return)

        self.on_resize(width, height)

    def on_resize(self, width, height):
        self.background.scale = 1.0
        self.background.scale = max(float(width) / self.background.width, float(height) / self.background.height)
        self.background.x, self.background.y = 0, 0
        self.frame.x, self.frame.y = (width - self.frame.width) / 2, (height - self.frame.height) / 2
        default_button_x = button_x = self.frame.x + 30
        button_y = self.frame.y + (self.frame.height) / 2 + 10
        i = 0
        for button in self.key_buttons:
            button.position = button_x, button_y
            if i%2 == 0:
                button_x += button.width + 20
            else:
                button_x = default_button_x
                button_y -= button.height + 20
            i += 1
        button_x = self.frame.x + (self.frame.width - self.button_return.width) / 2
        self.button_return.position = button_x, button_y

    def on_key_press(self, symbol, modifiers):
        active_button = None
        for button in self.buttons:
            if isinstance(button, ToggleButton) and button.toggled:
                active_button = button
                break

        if not active_button:
            return

        active_button.caption = pyglet.window.key.symbol_string(symbol)
        active_button.toggled = False

        G.config.set("Controls", active_button.id, pyglet.window.key.symbol_string(symbol))

        G.save_config()


class TexturesView(MenuView):
    def setup(self):
        MenuView.setup(self)
        width, height = self.controller.window.width, self.controller.window.height
        
        self.layout = VerticalLayout(0, 0)

        self.texture_buttons = []
        self.current_toggled = None

        texture_packs = G.texture_pack_list.available_texture_packs

        for texture_pack in texture_packs:
            button = self.ToggleButton(caption=texture_pack.texture_pack_file_name,on_toggle=self.on_button_toggle)
            button.id = texture_pack.texture_pack_file_name
            button.toggled = G.texture_pack_list.selected_texture_pack == texture_pack
            if button.toggled:
                self.current_toggled = button
            self.buttons.append(button)
            self.layout.add(button)
            self.texture_buttons.append(button)

        self.button_return = self.Button(caption="Done",on_click=self.controller.game_options)
        self.buttons.append(self.button_return)
        self.layout.add(self.button_return)

        self.on_resize(width, height)

    def on_button_toggle(self):
        for button in self.texture_buttons:
            if button != self.current_toggled and button.toggled:
                self.current_toggled.toggled = False
                self.current_toggled = button
                G.config.set("Graphics", "texture_pack", button.id)
                G.TEXTURE_PACK = button.id
                for block in G.BLOCKS_DIR.values():
                    block.update_texture() #Reload textures

                G.save_config()

    def on_resize(self, width, height):
        MenuView.on_resize(self, width, height)
        self.background.scale = 1.0
        self.background.scale = max(float(width) / self.background.width, float(height) / self.background.height)
        self.background.x, self.background.y = 0, 0
        self.frame.x, self.frame.y = (width - self.frame.width) / 2, (height - self.frame.height) / 2

class MultiplayerView(MenuView):
    def setup(self):
        MenuView.setup(self)
        width, height = self.controller.window.width, self.controller.window.height

        self.layout = VerticalLayout(0, 0)

        self.text_input = TextWidget(self.controller.window, G.IP_ADDRESS, 0, 0, width=160, height=20, font_name='Arial', batch=self.batch)
        self.controller.window.push_handlers(self.text_input)
        self.text_input.focus()
        def text_input_callback(symbol, modifier):
            G.IP_ADDRESS = self.text_input.text
        self.text_input.push_handlers(key_released=text_input_callback)

        button = self.Button(caption=G._("Connect to server"), on_click=self.controller.start_multiplayer_game)
        self.layout.add(button)
        self.buttons.append(button)
        button= self.Button(caption=G._("Launch server"), on_click=self.launch_server)
        self.layout.add(button)
        self.buttons.append(button)
        button= self.Button(caption=G._("Done"), on_click=self.controller.main_menu)
        self.layout.add(button)
        self.buttons.append(button)

        self.label = Label('Play Multiplayer', font_name='ChunkFive Roman', font_size=25, x=width/2, y=self.frame.y + self.frame.height,
            anchor_x='center', anchor_y='top', color=(255, 255, 255, 255), batch=self.batch,
            group=self.labels_group)

        self.on_resize(width, height)

    def launch_server(self):
        if os.name == 'nt':
            subprocess.Popen([sys.executable, "server.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen([sys.executable, "server.py"])
        localip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][0]
        self.text_input.text = localip
        G.IP_ADDRESS = localip

    def on_resize(self, width, height):
        MenuView.on_resize(self, width, height)
        self.text_input.resize(x=self.frame.x + (self.frame.width - self.text_input.width) / 2 + 5, y=self.frame.y + (self.frame.height) / 2 + 75, width=150)
