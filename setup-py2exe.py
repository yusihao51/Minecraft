# Imports, sorted alphabetically.

# Python packages
from Cython.Distutils import build_ext
from distutils.core import setup
from distutils.extension import Extension
import os
import glob
import py2exe


# Third-party packages
# Nothing for now...

# Modules from this project
import globals as G


excluded_modules = (
    'globals',
    'gui',
    'views',
    'controllers',
	'mods',
	'build',
	'setup-py2exe',
    'pyglet.gl.glext_arb',
    'pyglet.gl.glext_nv',
    'pyglet.image.codecs',
    'pyglet.image.codecs.pypng',
    'pyglet.media',
    'pyglet.window',
    'pyglet.window.xlib.xlib',
)

excluded_includes = (
	'main',
	'manager',
)
	
def find_files(source, target, patterns):
    """Locates the specified data-files and returns the matches
    in a data_files compatible format.

    source is the root of the source data tree.
        Use '' or '.' for current directory.
    target is the root of the target data tree.
        Use '' or '.' for the distribution directory.
    patterns is a sequence of glob-patterns for the
        files you want to copy.
    """
    if glob.has_magic(source) or glob.has_magic(target):
        raise ValueError("Magic not allowed in src, target")
    ret = {}
    for pattern in patterns:
        pattern = os.path.join(source,pattern)
        for filename in glob.glob(pattern):
            if os.path.isfile(filename):
                targetpath = os.path.join(target,os.path.relpath(filename,source))
                path = os.path.dirname(targetpath)
                ret.setdefault(path,[]).append(filename)
    return sorted(ret.items())

def get_modules(path=None):
    first = False
    if path is None:
        path = os.path.abspath(os.path.dirname(__file__))
        first = True
    for f_or_d in os.listdir(path):
        if not first:
            f_or_d = os.path.join(path, f_or_d)
        if os.path.isdir(f_or_d) and f_or_d not in excluded_modules:
            d = f_or_d
            for name, f in get_modules(d):
                yield name, f
        else:
            f = f_or_d
            if f.endswith(('.py', 'pyx')):
                name = '.'.join(s for s in f.split('.')[0].split('/')
                                if s != '__init__')
                if name and name not in excluded_modules:
                    yield name, f

ext_modules = [Extension(name, [f]) for name, f in get_modules()]
includes = [ name for name, f in get_modules() if name not in excluded_includes ]
includes.extend(['SocketServer', 'importlib'])

setup(
    name=G.APP_NAME,
    cmdclass={'build_ext': build_ext},
        data_files = find_files('.','',[
        'resources/fonts/*',
        'resources/sounds/*',
        'resources/textures/*',
		'resources/textures/blocks/*',
		'resources/textures/items/*',
        'resources/textures/icons/*',
        'resources/textures/xcf source files/*',
		'resources/environment/*',
		'resources/misc/*',
		'resources/gui/*',
		'resources/mob/*',
		'resources/*.jpg',
		'resources/title/bg/*',
    ]),
    version="1.0",
    description="A Minecraft demo clone in Python 2.7.x",
    author="github.com/boskee/Minecraft",
    windows=[{"script":'main.py', "dest_base":G.APP_NAME}],
    ext_modules=ext_modules, requires=['pyglet', 'Cython'],
	options={"py2exe":{"includes": includes}}
)
