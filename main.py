#!/usr/bin/env python

# Imports, sorted alphabetically.

# Python packages
from ConfigParser import NoSectionError, NoOptionError
import argparse
import os
import random
import time
import gettext
import sys

# Third-party packages
import pyglet
# Disable error checking for increased performance
pyglet.options['debug_gl'] = False
from pyglet.gl import *
from pyglet.window import key

# Modules from this project
from controllers import MainMenuController
import globals as G
from timer import Timer
from debug import log_info
from mod import load_modules
from savingsystem import save_world


class Window(pyglet.window.Window):
    def __init__(self, **kwargs):
        kwargs.update(
            caption=G.APP_NAME,
        )
        super(Window, self).__init__(
            G.WINDOW_WIDTH, G.WINDOW_HEIGHT, **kwargs)
        self.exclusive = False
        self.reticle = None
        self.controller = None
        controller = MainMenuController(self)
        self.switch_controller(controller)

        if G.FULLSCREEN:
            self.set_fullscreen()
        self.total_fps = 0.0
        self.iterations = 0
        pyglet.clock.schedule_interval(self.update, 1.0 / G.MAX_FPS)

        if G.FOG_ENABLED:
            self.enableFog()

    def enableFog(self):
        glEnable(GL_FOG)
        glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.5, 0.69, 1.0, 1))
        glHint(GL_FOG_HINT, GL_DONT_CARE)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        glFogf(GL_FOG_START, 30.0)
        glFogf(GL_FOG_END, 120)

    def disableFog(self):
        glDisable(GL_FOG)

    def set_exclusive_mouse(self, exclusive):
        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive

    def update(self, dt):
        self.controller.update(dt)
        self.total_fps += pyglet.clock.get_fps()
        self.iterations += 1

    def switch_controller(self, new_controller):
        if self.controller:
            self.controller.pop_handlers()
        self.controller = new_controller
        self.controller.push_handlers()

    def on_key_press(self, symbol, modifiers):
        if self.exclusive:
            if symbol == G.ESCAPE_KEY and not self.fullscreen:
                self.set_exclusive_mouse(False)
            elif symbol == key.Q and self.fullscreen:  # FIXME: Better fullscreen mode.
                pyglet.app.exit()  # for fullscreen

    def on_draw(self):
        if self.exclusive:
            self.reticle.draw(GL_LINES)
            if G.MOTION_BLUR:
                glAccum(GL_MULT, 0.65)
                glAccum(GL_ACCUM, 0.35)
                glAccum(GL_RETURN, 1.0)

    def on_resize(self, width, height):
        if self.reticle:
            self.reticle.delete()
        x, y = width / 2, height / 2
        n = 10
        self.reticle = pyglet.graphics.vertex_list(
            4,
            ('v2i', (x - n, y, x + n, y, x, y - n, x, y + n))
        )

    def on_close(self):
        log_info('Average FPS: %f' % (self.total_fps / self.iterations))
        super(Window, self).on_close()


def main(options):
    G.GAME_MODE = options.game_mode
    G.SAVE_FILENAME = options.save
    G.DISABLE_SAVE = options.disable_save
    for name, val in options._get_kwargs():
        setattr(G.LAUNCH_OPTIONS, name, val)

    if options.fast:
        G.TIME_RATE /= 20

    if G.LANGUAGE != 'default':
        reload(sys)
        sys.setdefaultencoding('UTF-8')
        gettext.install(True, localedir=None, unicode=1)
        gettext.find(G.APP_NAME.lower(), 'locale')
        gettext.textdomain(G.APP_NAME.lower())
        gettext.bind_textdomain_codeset(G.APP_NAME.lower(), 'UTF-8')
        language = gettext.translation(G.APP_NAME.lower(), 'locale', languages=[G.LANGUAGE], fallback=True)
        G._ = lambda s: language.ugettext(s)

    load_modules()

    # try:
        # window_config = Config(sample_buffers=1, samples=4) #, depth_size=8)  #, double_buffer=True) #TODO Break anti-aliasing/multisampling into an explicit menu option
        # window = Window(resizable=True, config=window_config)
    # except pyglet.window.NoSuchConfigException:
    window = Window(resizable=True, vsync=False)
    pyglet.app.run()

    if G.CLIENT:
        G.CLIENT.stop()
        
    if G.SERVER:
        print 'Saving...'
        save_world(G.SERVER, "world")
        print 'Shutting down internal server...'
        G.main_timer.stop()
        G.SERVER._stop.set()
        G.SERVER.shutdown()

if __name__ == '__main__':
    log_info('Starting pyCraft...')

    parser = argparse.ArgumentParser(description='Play a Python made Minecraft clone.')

    game_group = parser.add_argument_group('Game options')
    game_group.add_argument("--fast", action="store_true", default=False, help="Makes time progress faster then normal.")
    game_group.add_argument("--game-mode", choices=G.GAME_MODE_CHOICES, default=G.GAME_MODE)

    save_group = parser.add_argument_group('Save options')
    save_group.add_argument("--disable-auto-save", action="store_false", default=True, help="Do not save world on exit.")
    save_group.add_argument("--save", default=G.SAVE_FILENAME, help="Type a name for the world to be saved as.")
    save_group.add_argument("--disable-save", action="store_false", default=True, help="Disables saving.")

    parser.add_argument("--seed", default=None)

    options = parser.parse_args()
    main(options)
