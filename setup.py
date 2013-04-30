# Imports, sorted alphabetically.

# Python packages
from distribute_setup import use_setuptools
use_setuptools()
from Cython.Distutils import build_ext
from setuptools import setup, find_packages
from distutils.extension import Extension
import os

# Third-party packages
# Nothing for now...

# Modules from this project
import globals as G


excluded_modules = (
    'globals',
    'gui',
    'views',
    'controllers',
    'pyglet.gl.glext_arb',
    'pyglet.gl.glext_nv',
    'pyglet.image.codecs',
    'pyglet.image.codecs.pypng',
    'pyglet.media',
    'pyglet.window',
    'pyglet.window.xlib.xlib',
)


def get_modules(path=None):
    first = False
    if path is None:
        path = os.path.abspath(os.path.dirname(__file__))
        first = True
    for f_or_d in os.listdir(path):
        if not first:
            f_or_d = os.path.join(path, f_or_d)
        if os.path.isdir(f_or_d):
            d = f_or_d
          #  for name, f in get_modules(d):
           #     yield name, f
        else:
            f = f_or_d
            if f.endswith(('.py', 'pyx')):
                name = '.'.join(s for s in f.split('.')[0].split('/')
                                if s != '__init__')
                if name and name not in excluded_modules:
                    yield name, f

ext_modules = [Extension(name, [f]) for name, f in get_modules()]

setup(
    name=G.APP_NAME,
    cmdclass={'build_ext': build_ext},
    ext_modules=ext_modules, install_requires=['pyglet', 'Cython'], setup_requires=['pyglet', 'Cython'],
    packages = find_packages(), include_package_data=True
)
