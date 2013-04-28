# Imports, sorted alphabetically.

# Python packages
from Cython.Distutils import build_ext
from distutils.core import setup
from distutils.extension import Extension
import os
from os.path import basename
from urlparse import urlsplit
import urllib2
import platform
import zipfile

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
            for name, f in get_modules(d):
                yield name, f
        else:
            f = f_or_d
            if f.endswith(('.py', 'pyx')):
                name = '.'.join(s for s in f.split('.')[0].split('/')
                                if s != '__init__')
                if name and name not in excluded_modules:
                    yield name, f

def url2name(url):
    return basename(urlsplit(url)[2])

def download(url, local_file_name = None):
    local_name = url2name(url)
    req = urllib2.Request(url)
    r = urllib2.urlopen(req)
    if r.info().has_key('Content-Disposition'):
        # If the response has Content-Disposition, we take file name from it
        local_name = r.info()['Content-Disposition'].split('filename=')[1]
        if local_name[0] == '"' or local_name[0] == "'":
            local_name = local_name[1:-1]
    elif r.url != url:
        # if we were redirected, the real file name we take from the final URL
        local_name = url2name(r.url)
    if local_file_name:
        # we can force to save the file as specified name
        local_name = local_file_name
    f = open(local_name, 'wb')
    f.write(r.read())
    f.close()

DEP_LIST_URL = ''
DEP_LIST_LOCAL = 'dep_list'
PYGLET_LOCAL = 'pyglet.zip'
AVBIN_LOCAL = 'avbin'

def fetch_dep_list():
    print('Fetching dependencies list from ' + DEP_LIST_URL + '-' + platform.system() + '...')
    download(DEP_LIST_URL + '-' + platform.system(), DEP_LIST_LOCAL)

def install_dep():
    print('Downloading dependencies...')
    os.mkdir('downloads')
    fetch_dep_list()
    top_dir = os.getcwd()
    os.chdir('downloads')
    dep_list = open(DEP_LIST_LOCAL)
    pyg_version = dep_list.readline().rstrip('\n')
    lib_url = dep_list.readline().rstrip('\n')
    # first pyglet
    downloads_dir = os.getcwd()
    print('Downloading pyglet from ' + lib_url + '...')
    download(lib_url, PYGLET_LOCAL)
    print('Extracting pyglet...')
    zipfile.ZipFile(PYGLET_LOCAL, 'r').extractall(downloads_dir)
    print('Installing pyglet...')
    os.chdir(pyg_version)
    if os.name == 'posix':
        os.system('sudo python setup.py install')
    else:
        os.system('python setup.py install')
    os.chdir(downloads_dir)
    lib_url = dep_list.readline().rstrip('\n')
    print('Downloading AVBin from ' + lib_url + '...')
    download(lib_url, AVBIN_LOCAL)
    print('Install AVBin...')
    if os.name == 'posix':
        os.system('sudo sh ./' + AVBIN_LOCAL)
    else:
        os.system(AVBIN_LOCAL)

install_dep()

ext_modules = [Extension(name, [f]) for name, f in get_modules()]

setup(
    name=G.APP_NAME,
    cmdclass={'build_ext': build_ext},
    ext_modules=ext_modules, requires=['pyglet', 'Cython']
)
