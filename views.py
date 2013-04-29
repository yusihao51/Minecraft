# Imports, sorted alphabetically.

# Python packages
import os
import socket
import subprocess
import sys

# Third-party packages
import pyglet
from pyglet.text import Label
from pyglet.gl import *

# Modules from this project
import globals as G
from gui import frame_image, Rectangle, backdrop, Button, button_image, \
    button_highlighted, ToggleButton, TextWidget
from utils import image_sprite


__all__ = (
    'View', 'MainMenuView', 'OptionsView', 'ControlsView', 'TexturesView',
)


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

        image = frame_image
        self.frame_rect = Rectangle(0, 0, image.width, image.height)
        self.background = image_sprite(backdrop, self.batch, 0)
        self.background.scale = max(float(self.controller.window.get_size()[0]) / self.background.width, float(self.controller.window.get_size()[1]) / self.background.height)
        self.frame = image_sprite(image, self.batch, 2)

    def Button(self, x=0, y=0, width=160, height=50, image=button_image, image_highlighted=button_highlighted, caption="Unlabeled", batch=None, group=None, label_group=None, font_name='ChunkFive Roman', on_click=None, enabled=True):
        button = Button(self, x=x, y=y, width=width, height=height, image=image, image_highlighted=image_highlighted, caption=caption, batch=(batch or self.batch), group=(group or self.group), label_group=(label_group or self.labels_group), font_name=font_name, enabled=enabled)
        if on_click:
            button.push_handlers(on_click=on_click)
        return button

    def ToggleButton(self, x=0, y=0, width=160, height=50, image=button_image, image_highlighted=button_highlighted, caption="Unlabeled", batch=None, group=None, label_group=None, font_name='ChunkFive Roman', on_click=None, enabled=True):
        button = ToggleButton(self, x=x, y=y, width=width, height=height, image=image, image_highlighted=image_highlighted, caption=caption, batch=(batch or self.batch), group=(group or self.group), label_group=(label_group or self.labels_group), font_name=font_name, enabled=enabled)
        if on_click:
            button.push_handlers(on_click=on_click)
        return button

    def on_resize(self, width, height):
        self.background.scale = 1.0
        self.background.scale = max(float(width) / self.background.width, float(height) / self.background.height)
        self.background.x, self.background.y = 0, 0
        self.frame.x, self.frame.y = (width - self.frame.width) / 2, (height - self.frame.height) / 2
        button_x, button_y = 0, self.frame.y + (self.frame.height) / 2 + 10
        for button in self.buttons:
            button_x = self.frame.x + (self.frame.width - button.width) / 2
            button.position = button_x, button_y
            button_y -= button.height + 10


class MainMenuView(MenuView):
    def setup(self):
        MenuView.setup(self)
        width, height = self.controller.window.width, self.controller.window.height

        self.text_input = TextWidget(self.controller.window, G.IP_ADDRESS, 0, 0, width=160, height=20, font_name='Arial', batch=self.batch)
        self.controller.window.push_handlers(self.text_input)
        self.text_input.focus()
        def text_input_callback(symbol, modifier):
            G.IP_ADDRESS = self.text_input.text
        self.text_input.push_handlers(key_released=text_input_callback)

        self.buttons.append(self.Button(caption="Connect to Server",on_click=self.controller.start_game))
        self.buttons.append(self.Button(caption="Launch Server",on_click=self.launch_server))
        self.buttons.append(self.Button(caption="Options...",on_click=self.controller.game_options))
        self.buttons.append(self.Button(caption="Exit game",on_click=self.controller.exit_game))
        self.label = Label(G.APP_NAME, font_name='ChunkFive Roman', font_size=50, x=width/2, y=self.frame.y + self.frame.height,
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
        self.label.y = self.frame.y + self.frame.height - 15
        self.label.x = width / 2
        self.text_input.resize(x=self.frame.x + (self.frame.width - self.text_input.width) / 2 + 5, y=self.frame.y + (self.frame.height) / 2 + 75, width=150)


class OptionsView(MenuView):
    def setup(self):
        MenuView.setup(self)
        width, height = self.controller.window.width, self.controller.window.height

        texturepacks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'texturepacks')

        self.text_input = TextWidget(self.controller.window, G.USERNAME, 0, 0, width=160, height=20, font_name='Arial', batch=self.batch)
        self.controller.window.push_handlers(self.text_input)
        self.text_input.focus()
        self.text_input.caret.mark = len(self.text_input.document.text)  # Don't select the whole text
        def text_input_callback(symbol, modifier):
            G.USERNAME = self.text_input.text
        self.text_input.push_handlers(key_released=text_input_callback)

        self.buttons.append(self.Button(caption="Controls...", on_click=self.controller.controls))
        self.buttons.append(self.Button(caption="Textures", on_click=self.controller.textures, enabled=os.path.exists(texturepacks_dir)))
        self.buttons.append(self.Button(caption="Done", on_click=self.controller.main_menu))

        self.on_resize(width, height)

    def on_resize(self, width, height):
        MenuView.on_resize(self, width, height)
        self.text_input.resize(x=self.frame.x + (self.frame.width - self.text_input.width) / 2 + 5, y=self.frame.y + (self.frame.height) / 2 + 75, width=150)


class ControlsView(MenuView):
    def setup(self):
        MenuView.setup(self)
        width, height = self.controller.window.width, self.controller.window.height

        self.key_buttons = []
        for identifier in ('move_backward', 'move_forward', 'move_left', 'move_right'):
            button = self.ToggleButton(caption=pyglet.window.key.symbol_string(getattr(G, identifier.upper() + '_KEY')))
            button.id = identifier
            self.buttons.append(button)
            self.key_buttons.append(button)
        self.button_return = self.Button(caption="Done",on_click=self.controller.game_options)
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

        self.texture_buttons = []

        button = self.ToggleButton(caption='Default')
        button.id = 'default'
        self.buttons.append(button)
        self.texture_buttons.append(button)

        texturepacks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'texturepacks')

        for directories in os.listdir(texturepacks_dir):
            dir = os.path.join(texturepacks_dir, directories)
            pack_name = os.path.basename(dir)

            button = self.ToggleButton(caption=pack_name)
            button.id = pack_name
            self.buttons.append(button)
            self.texture_buttons.append(button)
        self.button_return = self.Button(caption="Done",on_click=self.controller.game_options)
        self.buttons.append(self.button_return)

        self.on_resize(width, height)

    def on_mouse_press(self, x, y, button, modifiers):
        super(TexturesView, self).on_mouse_press(x, y, button, modifiers)
        for button in self.texture_buttons:
            if button.toggled:
                G.config.set("Graphics", "texture_pack", button.id)
                G.TEXTURE_PACK = button.id
                for block in G.BLOCKS_DIR.values():
                    block.__init__() #Reload textures

                G.save_config()
                button.toggled = False
