# Imports, sorted alphabetically.

# Python packages
import os
from zipfile import ZipFile
from PIL import Image

# Third-party packages
import pyglet

# Modules from this project
import globals as G


__all__ = (
    'TexturePackList', 'TexturePackImplementation', 'TexturePackCustom', 'TexturePackDefault', 'TexturePackFolder',
)


class TexturePackImplementation(object):
    __texture_pack_id = None
    __texture_pack_file_name = ""
    __first_description_line = ""
    __second_description_line = ""
    __default_texture_pack = None
    __thumbnail_texture_name = -1
    texture_pack_file = None
    thumbnail_image = None
    
    def __init__(self, texture_pack_id, texture_pack_file, texture_pack_file_name, default_texture_pack=None):
        self.__texture_pack_id = texture_pack_id
        self.__texture_pack_file_name = texture_pack_file_name
        self.texture_pack_file = texture_pack_file
        self.__default_texture_pack = default_texture_pack
        if self.is_compatible():
            self.load_thumbnail_image()
            self.load_description()
    
    def load_thumbnail_image(self):
        try:
            fo = self.open_file(["pack.png"], False)
            if fo:
                if not isinstance(fo, pyglet.image.ImageData):
                    fo = pyglet.image.load("pack.png", file=fo)

                self.thumbnail_image = fo
        except:
            return
    
    def load_texture(self, path):
        try:
            fo = self.open_file(path, False)

            if fo:
                if not isinstance(fo, pyglet.image.ImageData):
                    fo = pyglet.image.load(path[-1], file=fo)

                return fo
        except:
            print 'Texture not found \'' + '/'.join(path) + '\''
            return None

    def load_description(self):
        try:
            fo = self.read_file(["pack.txt"])
            self.__first_description_line = fo.readline()[:34]
            self.__second_description_line = fo.readline()[:34]
        except:
            return

    def open_file(self, path, fallback):
        try:
            return self.read_file(path)
        except:
            if self.__default_texture_pack and fallback:
                return self.__default_texture_pack.open_file(path, True)

    def delete_texture_pack(self):
        if self.thumbnail_image and self.__thumbnail_texture_name != -1:
            pyglet.gl.glDeleteTextures(self.__thumbnail_texture_name)

    @property
    def texture_pack_id(self):
        return self.__texture_pack_id

    @property
    def texture_pack_file_name(self):
        return self.__texture_pack_file_name

    @property
    def first_description_line(self):
        return self.__first_description_line

    @property
    def second_description_line(self):
        return self.__second_description_line
        

class TexturePackCustom(TexturePackImplementation):
    __texture_pack_zip_file = None

    def __init__(self, texture_pack_id, texture_pack_path, default_texture_pack):
        super(TexturePackCustom, self).__init__(texture_pack_id, texture_pack_path, os.path.basename(texture_pack_path), default_texture_pack)
        
    def read_file(self, path):
        zipfile = self.open_texture_pack_file()

        zip_location = pyglet.resource.ZIPLocation(zipfile, "/".join(path[:-1]))
        return pyglet.image.load(path[-1], file=zip_location.open(path[-1]))

    def file_exists(self, path):
        try:
            zipfile = self.open_texture_pack_file()
            return zipfile.getinfo("/".join(path))
        except KeyError:
            return False

    def open_texture_pack_file(self):
        return ZipFile(self.texture_pack_file, "r")

    def is_compatible(self):
        zipfile = self.open_texture_pack_file()
        
        file_names = zipfile.namelist()
        
        for name in file_names:
            if name.startswith("textures/"):
                return True

        # file_exists = self.file_exists(["terrain.png"]) or self.file_exists(["gui", "items.png"])
        
        # return not file_exists

        file_exists = self.file_exists(["terrain.png"]) or self.file_exists(["gui", "items.png"])

        return file_exists


class TexturePackDefault(TexturePackImplementation):
    def __init__(self):
        super(TexturePackDefault, self).__init__("default", None, "Default", None)

    def load_description(self):
        self.__first_description_line = "The default look of %s" % G.APP_NAME

    def get_resource_as_stream(self, path):
        return self.open_file(path, True)

    def read_file(self, path):
        if self.file_exists(path):
            return open(os.path.join("resources", *path), "rb")

    def file_exists(self, path):
        file_path = os.path.join("resources", *path)
        return os.path.exists(file_path) and os.path.isfile(file_path)

    def is_compatible(self):
        return True

    def __repr__(self):
        return "The default look of %s" % G.APP_NAME
            

class TexturePackFolder(TexturePackImplementation):
    def __init__(self, texture_pack_id, texture_pack_path, default_texture_pack):
        super(TexturePackFolder, self).__init__(texture_pack_id, texture_pack_path, os.path.basename(texture_pack_path), default_texture_pack)

    def read_file(self, path):
        if self.file_exists(path):
            return open(os.path.join(self.texture_pack_file, *path), "r")

    def file_exists(self, path):
        file_path = os.path.join(self.texture_pack_file, *path)
        return os.path.exists(file_path) and os.path.isfile(file_path)

    def is_compatible(self):
        textures_path = os.path.join(self.texture_pack_file, "textures")
        is_dir = os.path.exists(textures_path) and os.path.isdir(textures_path)
        file_exists = self.file_exists(["terrain.png"]) or self.file_exists(["gui", "items.png"])
        return is_dir or not file_exists


class TexturePackList:
    __available_texture_packs = []
    
    def __init__(self, controller=None):
        self.default_texture_pack = TexturePackDefault()
        self.texture_pack_cache = {}
        self.controller = controller;
        self.texture_pack_dir = os.path.join(G.game_dir, "texturepacks")
        self.mp_texture_pack_folder = os.path.join(G.game_dir, "texturepacks-mp-cache")
        self.create_texture_pack_dirs()
        self.update_available_texture_packs(self.default_texture_pack)
        
    def create_texture_pack_dirs(self):
        if not os.path.isdir(self.texture_pack_dir):
            if os.path.exists(self.texture_pack_dir):
                os.remove(self.texture_pack_dir)
            os.makedirs(self.texture_pack_dir)

        if not os.path.isdir(self.mp_texture_pack_folder):
            if os.path.exists(self.mp_texture_pack_folder):
                os.remove(self.mp_texture_pack_folder)
            os.makedirs(self.mp_texture_pack_folder)
            
    def update_available_texture_packs(self, default_texture_pack=None):
        texture_packs = []
        self.__selected_texture_pack = default_texture_pack
        texture_packs.append(default_texture_pack)

        for name in os.listdir(self.texture_pack_dir):
            texture_pack_path = os.path.join(self.texture_pack_dir, name)
            texture_pack_id = self.generate_texture_pack_id(texture_pack_path)
            
            if texture_pack_id:
                texture_pack = None
                
                if texture_pack_id in self.texture_pack_cache:
                    texture_pack = self.texture_pack_cache[texture_pack_id]
                else:
                    if os.path.isdir(texture_pack_path):
                        texture_pack = TexturePackFolder(texture_pack_id, texture_pack_path, default_texture_pack)
                    else:
                        texture_pack = TexturePackCustom(texture_pack_id, texture_pack_path, default_texture_pack)

                if texture_pack and texture_pack.is_compatible():
                    self.texture_pack_cache[texture_pack_id] = texture_pack

                    if texture_pack.texture_pack_file_name == G.TEXTURE_PACK:
                        self.__selected_texture_pack = texture_pack
                  
                    texture_packs.append(texture_pack)
        
        self.__available_texture_packs = [texture_pack for texture_pack in self.__available_texture_packs if texture_pack not in texture_packs]
        
        for texture_pack in self.__available_texture_packs:
            texture_pack.delete_texture_pack()
            del self.texture_pack_cache[texture_pack.texture_pack_id]

        self.__available_texture_packs = texture_packs

    def generate_texture_pack_id(self, texture_path):
        if os.path.isfile(texture_path) and texture_path.lower().endswith(".zip"):
            statinfo = os.stat(texture_path)
            return "%s:%d:%d" % (os.path.basename(texture_path), statinfo.st_size, statinfo.st_mtime)
        elif os.path.isdir(texture_path) and os.path.exists(os.path.join(texture_path, "pack.txt")):
            statinfo = os.stat(texture_path)
            return "%s:folder:%d" % (os.path.basename(texture_path), statinfo.st_mtime)
         
        return None

    @property
    def available_texture_packs(self):
        return self.__available_texture_packs

    @property
    def selected_texture_pack(self):
        return self.__selected_texture_pack

G.texture_pack_list = TexturePackList()
