# -*- coding: utf-8 -*-

# Imports, sorted alphabetically.

# Future imports
from __future__ import unicode_literals
from math import floor

# Python packages
# Nothing for now...
import struct   # for update_tile_entity

# Third-party packages
import pyglet
from pyglet.gl import *
from pyglet.image.atlas import TextureAtlas
from utils import load_image, make_nbt_from_dict, extract_nbt

# Modules from this project
import globals as G
from random import randint
import sounds
from entity import CropEntity, FurnaceEntity
from textures import TexturePackList

BLOCK_TEXTURE_DIR = {}


def get_texture_coordinates(x, y, tileset_size=G.TILESET_SIZE):
    if x == -1 and y == -1:
        return ()
    m = 1.0 / tileset_size
    dx = x * m
    dy = y * m
    return dx, dy, dx + m, dy, dx + m, dy + m, dx, dy + m


#To enable, extract a texture pack's blocks folder to resources/texturepacks/textures/blocks/
#For MC 1.5 Texture Packs
class TextureGroupIndividual(pyglet.graphics.Group):
    def __init__(self, names, height=1.0, width=1.0):
        super(TextureGroupIndividual, self).__init__()
        atlas = None
        # self.texture = atlas.texture
        self.texture_data = []
        i=0
        texture_pack = G.texture_pack_list.selected_texture_pack
        for name in names:
            
            if not name in BLOCK_TEXTURE_DIR:
                BLOCK_TEXTURE_DIR[name] = texture_pack.load_texture(['textures', 'blocks', name + '.png'])

            if not BLOCK_TEXTURE_DIR[name]:
                continue

            texture_size = BLOCK_TEXTURE_DIR[name].width

            if atlas == None:
                atlas = TextureAtlas(texture_size * len(names), texture_size)
                self.texture = atlas.texture

            subtex = atlas.add(BLOCK_TEXTURE_DIR[name].get_region(0,0,texture_size,texture_size))
            for val in subtex.tex_coords:
                i += 1
                if i % 3 != 0: self.texture_data.append(val) #tex_coords has a z component we don't utilize
        if atlas == None:
            atlas = TextureAtlas(1, 1)
        self.texture = atlas.texture
        #Repeat the last texture for the remaining sides
        # (top, bottom, side, side, side, side)
        # ie: ("dirt",) ("grass_top","dirt","grass_side")
        # Becomes ("dirt","dirt","dirt","dirt","dirt","dirt") ("grass_top","dirt","grass_side","grass_side","grass_side","grass_side")
        self.texture_data += self.texture_data[-8:]*(6-len(names))

        # resize the texture
        if height != 1.0 or width != 1.0 :
            if len(self.texture_data) == 0:
                return

            tex_width = tex_height = self.texture_data[2] - self.texture_data[0]
            h_margin = tex_height * (1.0 - height)
            w_margin = tex_width * (1.0 - width) / 2
            # top and bottom
            for i in (0, 1):
                for j in (0, 1, 3, 6): self.texture_data[i * 8 + j] += w_margin
                for j in (2, 4, 5, 7): self.texture_data[i * 8 + j] -= w_margin

            # side
            for i in range(2, 6):
                for j in (0, 6): self.texture_data[i * 8 + j] += w_margin
                for j in (2, 4): self.texture_data[i * 8 + j] -= w_margin
                for j in (5, 7): self.texture_data[i * 8 + j] -= h_margin

    def set_state(self):
        if self.texture:
            glBindTexture(self.texture.target, self.texture.id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glEnable(self.texture.target)

    def unset_state(self):
        if self.texture:
            glDisable(self.texture.target)


class BlockID(object):
    """
    Datatype for Block and Item IDs

    Creation: BlockID(1)   BlockID(35)   BlockID(35, 3)   BlockID((35,
    3))   BlockID("35.3")
    str(id) : "1.0"        "35.0"        "35.3"           "35.3"
    "35.3"
    Typical uses: id == 1    id == BlockID(35, 3)   id < 255
    """

    main = 0
    sub = 0  # A.k.a. DataID, damageID, metadata, etc
    icon_name = None

    def __init__(self, main, sub=0, icon_name=None):
        if isinstance(main, tuple):
            self.main, self.sub = main
        elif isinstance(main, basestring):
            # Allow "35", "35.0", or "35,0"
            spl = main.split(".") if "." in main else main.split(",") if "," in main else (main, 0)
            if len(spl) == 2:
                a, b = spl
            elif len(spl) == 1:
                a = spl[0]
                b = 0
            else:
                raise ValueError("Expected #.# or #,#. Got %s" % main)
            self.main = int(a)
            self.sub = int(b or 0)
        elif isinstance(main, self.__class__):
            self.main = main.main
            self.sub = main.sub
        else:
            self.main = int(main)
            self.sub = int(sub)

        self.icon_name = icon_name

    def __repr__(self):
        return '%d.%d' % (self.main, self.sub)

    def __hash__(self):
        return hash((self.main, self.sub))

    def __cmp__(self, other):
        if isinstance(other, tuple):
            return cmp((self.main, self.sub), other)
        if isinstance(other, float):
            return cmp(float(repr(self.main)), other)
        if isinstance(other, int):
            return cmp(self.main, other)
        if isinstance(other, BlockID):
            return cmp(self.main, other.main) or cmp(self.sub, other.sub)

    def __nonzero__(self):
        """Checks whether it is an AirBlock."""
        return self.main != 0

    def is_item(self):
        return self.main > 255

    def filename(self):
        if self.icon_name != None: return ["textures", "blocks" if self.main < G.ITEM_ID_MIN else "items", str(self.icon_name) + ".png"]
        if self.sub == 0: return ["textures", "icons", str(self.main) + ".png"]
        return ["textures", "icons", '%d.%d.png' % (self.main, self.sub)]


class Block(object):
    id = None  # Original minecraft id (also called data value).
               # Verify on http://www.minecraftwiki.net/wiki/Data_values
               # when creating a new "official" block.

    _drop_id = None
    _drop_quantity = None
    player_damage = 0

    @property
    def drop_id(self):
        return self._drop_id

    @drop_id.setter
    def drop_id(self, value):
        self._drop_id = value

    @property
    def drop_quantity(self):
        return self._drop_quantity

    @drop_quantity.setter
    def drop_quantity(self, value):
        self._drop_quantity = value

    _texture_data = None

    @property
    def texture_data(self):
        return self._texture_data

    @texture_data.setter
    def texture_data(self, value):
        self._texture_data = value

    width = 1.0
    height = 1.0

    # Texture coordinates from the tileset.
    top_texture = ()
    bottom_texture = ()
    side_texture = ()
    front_texture = None
    vertex_mode = G.VERTEX_CUBE
    group = None  # The texture (group) the block renders from
    texture_name = None  # A list of block faces, named what Mojang names their blocks/"file".png
    icon_name = None

    # Sounds
    break_sound = sounds.wood_break

    # Physical attributes
    hardness = 0.0  # hardness can be found on http://www.minecraftwiki.net/wiki/Digging#Blocks_by_hardness
    density = 1
    transparent = False
    regenerated_health = 0

    # Inventory attributes
    max_stack_size = 64
    amount_label_color = 255, 255, 255, 255
    name = "Block"

    digging_tool = -1
    # How long can this item burn (-1 for non-fuel items)
    burning_time = -1
    # How long does it take to smelt this item (-1 for unsmeltable items)
    smelting_time = -1

    render_as_normal_block = True

    # if sub_id_as_metadata, we will create an instance for this block when it's being added to the world
    # and use its sub id as metadata
    sub_id_as_metadata = False

    def __init__(self, width=None, height=None):
        self.id = BlockID(self.id or 0, 0, self.icon_name)
        self.drop_id = self.id
        self.drop_quantity = 1

        if width is not None:
            self.width = width
        if height is not None:
            self.height = height

        G.BLOCKS_DIR[self.id] = self

        if not self.render_as_normal_block:
            return

        self.update_texture()

    def __str__(self):
        return self.name

    def get_texture_data(self):
        textures = self.top_texture + self.bottom_texture \
                   + self.front_texture + self.side_texture
        if self.vertex_mode != G.VERTEX_CROSS:
            textures += self.side_texture * 2
        return list(textures)

    def get_vertices(self, x, y, z):
        w = self.width / 2.0
        h = self.height / 2.0

        y_offset = (1.0 - self.height) / 2
        y -= y_offset

        xm = x - w
        xp = x + w
        ym = y - h
        yp = y + h
        zm = z - w
        zp = z + w

        vertices = ()
        if len(self.top_texture) > 0 or len(self.side_texture) == 0:
            vertices += (
                xm, yp, zm,   xm, yp, zp,   xp, yp, zp,   xp, yp, zm  # top
            )
        if len(self.bottom_texture) > 0 or len(self.side_texture) == 0:
            vertices += (
                xm, ym, zm,   xp, ym, zm,   xp, ym, zp,   xm, ym, zp  # bottom
            )
        if self.vertex_mode == G.VERTEX_CROSS:
            vertices += (
                xm, ym, zm,   xp, ym, zp,   xp, yp, zp,   xm, yp, zm,
                xm, ym, zp,   xp, ym, zm,   xp, yp, zm,   xm, yp, zp,
            )
        elif self.vertex_mode == G.VERTEX_GRID:
            xm2 = x - w / 2.0
            xp2 = x + w / 2.0
            zm2 = z - w / 2.0
            zp2 = z + w / 2.0
            vertices += (
                xm2, ym, zm,   xm2, ym, zp,   xm2, yp, zp,   xm2, yp, zm,  # left
                xp2, ym, zp,   xp2, ym, zm,   xp2, yp, zm,   xp2, yp, zp,  # right
                xm, ym, zp2,   xp, ym, zp2,   xp, yp, zp2,   xm, yp, zp2,  # front
                xp, ym, zm2,   xm, ym, zm2,   xm, yp, zm2,   xp, yp, zm2,  # back
            )
        else:
            vertices += (
                xm, ym, zm,   xm, ym, zp,   xm, yp, zp,   xm, yp, zm,  # left
                xp, ym, zp,   xp, ym, zm,   xp, yp, zm,   xp, yp, zp,  # right
                xm, ym, zp,   xp, ym, zp,   xp, yp, zp,   xm, yp, zp,  # front
                xp, ym, zm,   xm, ym, zm,   xm, yp, zm,   xp, yp, zm,  # back
            )
        return vertices

    def get_metadata(self):
        if self.sub_id_as_metadata:
            return self.id.sub

    def set_metadata(self, metadata):
        if self.sub_id_as_metadata:
            self.id.sub = metadata

    def play_break_sound(self, player=None, position=None):
        if self.break_sound is not None:
            sounds.play_sound(self.break_sound, player=player, position=position)

    def update_tile_entity(self, value):
        pass

    def update_texture(self):
        if self.texture_name:
            self.group = TextureGroupIndividual(self.texture_name, self.height, self.width)

            if self.group:
                self.texture_data = self.group.texture_data
        
        if self.top_texture == ():
            return
            
        if self.front_texture is None:
            self.front_texture = self.side_texture
        if not self.texture_data:
            # Applies get_texture_coordinates to each of the faces to be textured.
            for k in ('top_texture', 'bottom_texture', 'side_texture', 'front_texture'):
                v = getattr(self, k)
                if v:
                    setattr(self, k, get_texture_coordinates(*v))
            self.texture_data = self.get_texture_data()

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        pass

    def can_place_on(self, block_id):
        return False

class BlockColorizer(object):
        def __init__(self, filename):
            self.color_data = G.texture_pack_list.selected_texture_pack.load_texture(['misc', filename])
            # if the texture is not available, don't colorize it
            if self.color_data is None:
                return
            self.color_data = self.color_data.get_data('RGB', self.color_data.width * 3)

        def get_color(self, temperature, humidity):
            temperature = 1 - temperature
            if temperature + humidity > 1:
                delta = (temperature + humidity - 1) / 2
                temperature -= delta
                humidity -= delta
            if self.color_data is None:
                return 1, 1, 1
            pos = int(floor(humidity * 255) * BYTE_PER_LINE + 3 * floor((temperature) * 255))
            return float(ord(self.color_data[pos])) / 255, float(ord(self.color_data[pos + 1])) / 255, float(ord(self.color_data[pos + 2])) / 255

class AirBlock(Block):
    max_stack_size = 0
    density = 0
    id = 0
    name = "Air"


class WoodBlock(Block):
    break_sound = sounds.wood_break
    digging_tool = G.AXE


class HardBlock(Block):
    break_sound = sounds.stone_break

class StoneBlock(HardBlock):
    texture_name = "stone",
    icon_name = "stone"
    hardness = 1.5
    id = 1
    name = "Stone"
    digging_tool = G.PICKAXE

    def __init__(self):
        super(StoneBlock, self).__init__()
        self.drop_id = BlockID(CobbleBlock.id)
    
    colorizer = BlockColorizer('stonecolor.png')

    def get_color(self, temperature, humidity):
        ret = []
        ret.extend(list(self.colorizer.get_color(temperature, humidity)) * 24)
        return ret


PIXEL_PER_LINE = 256
BYTE_PER_LINE = PIXEL_PER_LINE * 3

class GrassBlock(Block):
    texture_name = "grass_top", "dirt", "grass_side"
    icon_name = "grass_side"
    hardness = 0.6
    id = 2
    break_sound = sounds.dirt_break
    name = 'Grass'
    digging_tool = G.SHOVEL
    colorizer = BlockColorizer('grasscolor.png')

    def __init__(self):
        super(GrassBlock, self).__init__()
        self.drop_id = BlockID(DirtBlock.id)

    def get_color(self, temperature, humidity):
        ret = []
        # colorize only the top of the grass block
        ret.extend(list(self.colorizer.get_color(temperature, humidity)) * 4)
        ret.extend([1] * 60)
        return ret

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        # something has been put on this grass block, which makes it become dirt block
        if (self_pos[0], self_pos[1] + 1, self_pos[-1]) in world:
            world.remove_block(None, self_pos)
            world.add_block(self_pos, dirt_block)

class DirtBlock(Block):
    texture_name = "dirt",
    icon_name = "dirt"
    hardness = 0.5
    id = 3
    name = "Dirt"
    digging_tool = G.SHOVEL
    break_sound = sounds.dirt_break

class SnowBlock(Block):
    texture_name = "snow",
    icon_name = "snow"
    hardness = 0.5
    id = 80
    name = "Snow"
    amount_label_color = 0, 0, 0, 255
    break_sound = sounds.dirt_break

class SandBlock(Block):
    texture_name = "sand",
    icon_name = "sand"
    hardness = 0.5
    amount_label_color = 0, 0, 0, 255
    id = 12
    name = "Sand"
    digging_tool = G.SHOVEL
    break_sound = sounds.sand_break
    colorizer = BlockColorizer('sandcolor.png')

    def get_color(self, temperature, humidity):
        ret = []
        ret.extend(list(self.colorizer.get_color(temperature, humidity)) * 24)
        return ret


class GoldOreBlock(HardBlock):
    texture_name = "oreGold",
    icon_name = "oreGold"
    hardness = 3
    id = 14
    digging_tool = G.PICKAXE
    name = "Gold Ore"


class IronOreBlock(HardBlock):
    texture_name = "oreIron",
    icon_name = "oreIron"
    hardness = 3
    id = 15
    digging_tool = G.PICKAXE
    name = "Iron Ore"
    smelting_time = 10

class DiamondOreBlock(HardBlock):
    texture_name = "oreDiamond",
    icon_name = "oreDiamond"
    hardness = 3
    id = 56
    digging_tool = G.PICKAXE
    def __init__(self):
        super(DiamondOreBlock, self).__init__()
        self.drop_id = BlockID(264)
    name = "Diamond Ore"


class CoalOreBlock(HardBlock):
    texture_name = "oreCoal",
    icon_name = "oreCoal"
    hardness = 3
    id = 16
    digging_tool = G.PICKAXE
    def __init__(self):
        super(CoalOreBlock, self).__init__()
        self.drop_id = BlockID(263)
    name = "Coal Ore"


class BrickBlock(HardBlock):
    texture_name = "brick",
    icon_name = "brick"
    hardness = 2
    id = 45
    digging_tool = G.PICKAXE
    name = "Bricks"


class LampBlock(Block):
    top_texture = 3, 1
    bottom_texture = 3, 1
    side_texture = 3, 1
    hardness = 0.3
    amount_label_color = 0, 0, 0, 255
    id = 124
    name = "Lamp"
    break_sound = sounds.glass_break


class GlassBlock(Block):
    texture_name = "glass",
    icon_name = "glass"
    transparent = True
    hardness = 0.2
    amount_label_color = 0, 0, 0, 255
    id = 20
    name = "Glass"
    break_sound = sounds.glass_break


class GravelBlock(Block):
    texture_name = "gravel",
    icon_name = "gravel"
    hardness = 0.4
    amount_label_color = 0, 0, 0, 255
    id = 13
    name = "Gravel"
    digging_tool = G.SHOVEL
    break_sound = sounds.gravel_break

    @property
    def drop_id(self):
        # 10% chance of dropping flint
        if randint(0, 10) == 0:
            return BlockID(318)
        else:
            return self._drop_id

    @drop_id.setter
    def drop_id(self, value):
        self._drop_id = value

class BedrockBlock(HardBlock):
    texture_name = "bedrock",
    icon_name = "bedrock"
    hardness = -1  # Unbreakable
    id = 7
    name = "Bedrock"


class WaterBlock(Block):
    height = 0.8
    texture_name = "water",
    transparent = True
    hardness = -1  # Unobtainable
    density = 0.5
    id = 8
    name = "Water"
    break_sound = sounds.water_break

    colorizer = BlockColorizer('watercolor.png')

    def get_color(self, temperature, humidity):
        ret = []
        ret.extend(list(self.colorizer.get_color(temperature, humidity)) * 24)
        return ret

class CraftTableBlock(WoodBlock):
    texture_name = "workbench_top","wood","workbench_front","workbench_side",
    icon_name = "workbench_front"
    hardness = 2.5
    id = 58
    name = "Crafting Table"
    burning_time = 15

class MetaBlock(WoodBlock): # this is a experimental block.
    hardness = 2.5
    id = 0.1
    name = "Action"


class SandstoneBlock(HardBlock):
    texture_name = "sandstone_top","sandstone_bottom","sandstone_side"
    icon_name = "sandstone_side"
    amount_label_color = 0, 0, 0, 255
    hardness = 0.8
    id = 24
    name = "Sandstone"

class EmeraldOreBlock(HardBlock):
    texture_name = "oreEmerald",
    icon_name = "oreEmerald"
    hardness = 2
    id = 129,0
    name = "Emerald Ore"

class LapisOreBlock(HardBlock):
    texture_name = "oreLapis",
    icon_name = "oreLapis"
    hardness = 2
    id = 21
    name = "Lapis Ore"

class RubyOreBlock(HardBlock):
    top_texture = 12, 0
    bottom_texture = 12, 0
    side_texture = 12, 0
    hardness = 2
    id = 129,1 # not in MC
    name = "Ruby Ore"

class SapphireOreBlock(HardBlock):
    top_texture = 12, 2
    bottom_texture = 12, 2
    side_texture = 12, 2
    hardness = 2
    id = 129,2 # not in MC
    name = "Sapphire Ore"

# Changed Marble to Quartz -- It seems that Quartz is MC's answer to Tekkit's Marble.
class QuartzBlock(HardBlock):
    texture_name = "quartzblock_top","quartzblock_bottom","quartzblock_side"
    icon_name = "quartzblock_side"
    id = 155,0
    hardness = 2
    name = "Quartz"
    amount_label_color = 0, 0, 0, 255
    digging_tool = G.PICKAXE

class ChiseledQuartzBlock(HardBlock):
    texture_name = "quartzblock_chiseled_top","quartzblock_chiseled_top","quartzblock_chiseled"
    icon_name = "quartzblock_chiseled"
    id = 155,1
    hardness = 2
    name = "Chiseled Quartz"
    amount_label_color = 0, 0, 0, 255
    digging_tool = G.PICKAXE

class ColumnQuartzBlock(HardBlock):
    texture_name = "quartzblock_lines_top","quartzblock_lines_top","quartzblock_lines"
    icon_name = "quartzblock_lines"
    id = 155,2
    hardness = 2
    name = "Column Quartz"
    amount_label_color = 0, 0, 0, 255
    digging_tool = G.PICKAXE

class QuartzBrickBlock(HardBlock):
    top_texture = 9, 7
    bottom_texture = 9, 7
    side_texture = 9, 7
    id = 155,3
    hardness = 2
    name = "Quartz Brick"
    amount_label_color = 0, 0, 0, 255
    digging_tool = G.PICKAXE

class BirchWoodPlankBlock(WoodBlock):
    texture_name = "wood_birch",
    icon_name = "wood_birch"
    hardness = 2
    id = 5,0
    burning_time = 15
    name = "Birch Wood Planks"


class OakWoodPlankBlock(WoodBlock):
    texture_name = "wood",
    icon_name = "wood"
    hardness = 2
    id = 5,1
    burning_time = 15
    name = "Oak Wood Planks"


class JungleWoodPlankBlock(WoodBlock):
    texture_name = "wood_jungle",
    icon_name = "wood_jungle"
    hardness = 2
    id = 5,3
    burning_time = 15
    name = "Jungle Wood Planks"


# FIXME: Can't find its specific id on minecraftwiki.
# from ronmurphy: This is just the snowy side grass from the above texture pack.  MC has one like this also.
class SnowGrassBlock(Block):
    texture_name = "snow","dirt","snow_side"
    icon_name = "snow_side"
    hardness = 0.6
    id = 80
    break_sound = sounds.dirt_break

    def __init__(self):
        super(SnowGrassBlock, self).__init__()
        self.drop_id = BlockID(DirtBlock.id)


class OakWoodBlock(WoodBlock):
    texture_name = "tree_top","tree_top","tree_side"
    icon_name = "tree_side"
    hardness = 2
    id = 17,0
    name = "Oak wood"
    burning_time = 15


class OakBranchBlock(WoodBlock):
    top_texture = 7, 0
    bottom_texture = 7, 0
    side_texture = 7, 0
    hardness = 2
    id = 17,1
    name = "Oak wood"

    def __init__(self):
        super(OakBranchBlock, self).__init__()
        self.drop_id = BlockID(OakWoodBlock.id)


class JungleWoodBlock(WoodBlock):
    texture_name = "tree_top","tree_top","tree_jungle"
    icon_name = "tree_jungle"
    hardness = 2
    id = 17,1
    name = "Jungle wood"
    burning_time = 15


class BirchWoodBlock(WoodBlock):
    texture_name = "tree_top","tree_top","tree_birch"
    icon_name = "tree_birch"
    hardness = 2
    id = 17,2
    amount_label_color = 0, 0, 0, 255
    name = "Birch wood"
    burning_time = 15


class CactusBlock(Block):
    width = 0.8
    transparent = True
    texture_name = "cactus_top","cactus_bottom","cactus_side"
    icon_name = "cactus_side"
    hardness = 2
    player_damage = 1
    id = 81,0
    name = "Cactus"


class TallCactusBlock(Block):
    width = 0.3
    texture_name = "cactus_top","cactus_bottom","cactus_side"
    icon_name = "cactus_side"
    transparent = True
    hardness = 1
    player_damage = 1
    id = 81,1  # not a real MC block, so the last possible # i think.
    name = "Thin Cactus"


class LeafBlock(Block):
    break_sound = sounds.leaves_break
    colorizer = BlockColorizer('foliagecolor.png')

    def __init__(self):
        super(LeafBlock, self).__init__()
        self.drop_id = None

    def get_color(self, temperature, humidity):
        ret = []
        ret.extend(list(self.colorizer.get_color(temperature, humidity)) * 24)
        return ret


class OakLeafBlock(LeafBlock):
    texture_name = "leaves",
    icon_name = "leaves"
    hardness = 0.3
    id = 18,0
    name = "Oak Leaves"


class JungleLeafBlock(LeafBlock):
    texture_name = "leaves_jungle",
    icon_name = "leaves_jungle"
    hardness = 0.3
    id = 18,1
    name = "Jungle Leaves"


class BirchLeafBlock(LeafBlock):
    texture_name = "leaves",
    icon_name = "leaves"
    hardness = 0.3
    id = 18,2
    name = "Birch Leaves"

    def __init__(self):
        super(BirchLeafBlock, self).__init__()
        self.drop_id = None


class MelonBlock(Block):
    width = 0.8
    height = 0.8
    texture_name = "melon_top","melon_top","melon_side"
    icon_name = "melon_side"
    transparent = True
    hardness = 1
    id = 103
    name = "Melon"
    regenerated_health = 3
    break_sound = sounds.melon_break


class PumpkinBlock(Block):
    width = 0.8
    height = 0.8
    texture_name = "pumpkin_top","pumpkin_top","pumpkin_side"
    icon_name = "pumpkin_side"
    transparent = True
    hardness = 1
    id = 86
    name = "Pumpkin"
    regenerated_health = 3 # pumpkin pie
    break_sound = sounds.melon_break


class TorchBlock(WoodBlock):
    width = 0.1
    height = 0.55
    texture_name = "torch",
    icon_name = "torch"
    hardness = 1
    transparent = True
    id = 50
    name = "Torch"

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        # the block under this torch has been removed, so remove the torch too
        if (self_pos[0], self_pos[1] - 1, self_pos[-1]) not in world:
            world.remove_block(None, self_pos)

class YFlowersBlock(Block):
    vertex_mode = G.VERTEX_CROSS
    hardness = 0.0
    # prevent generating vertices for top and bottom
    side_texture = 0, 0
    transparent = True
    density = 0.3
    id = 37
    texture_name = "flower", "flower", "flower"
    icon_name = "flower"
    name = "Dandelion"
    break_sound = sounds.leaves_break

    def __init__(self):
        super(YFlowersBlock, self).__init__()
        self.texture_data = self.texture_data[0:2 * 4 * 2]

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        if (self_pos[0], self_pos[1] - 1, self_pos[-1]) not in world:
            world.remove_block(None,self_pos)


class StoneSlabBlock(HardBlock):
    texture_name = "stoneslab_top","stoneslab_top","stoneslab_side",
    icon_name = "stoneslab_side"
    hardness = 2
    id = 43
    name = "Full Stone Slab"


class ClayBlock(HardBlock):
    texture_name = "clay",
    icon_name = "clay"
    hardness = 0.6
    id = 82
    name = "Clay Block"


class CobbleBlock(HardBlock):
    texture_name = "stonebrick",
    icon_name = "stonebrick"
    hardness = 2
    id = 4,0
    name = "Cobblestone"


class CobbleFenceBlock(HardBlock):
    width = 0.6
    texture_name = "stonebrick",
    icon_name = "stonebrick"
    transparent = True
    hardness = 2
    id = 4,1
    name = "Cobblestone Fence Post"


class BookshelfBlock(WoodBlock):
    texture_name = "wood","wood","bookshelf"
    icon_name = "bookshelf"
    hardness = 1.5
    id = 47
    name = "Bookshelf"
    burning_time = 15


class FurnaceBlock(HardBlock):
    texture_name = "furnace_top","stonebrick","furnace_front","furnace_side"
    icon_name = "furnace_front"
    hardness = 3.5
    id = 61
    name = "Furnace"

    entity_type = FurnaceEntity
    entity = None

    slot_count = 2

    def __del__(self):
        if self.entity is not None:
            del self.entity

    # compatible with inventory
    def set_slot(self, index, value):
        i = int(index)
        if i < 0 or i >= 2:
            return None
        if i == 0:
            self.set_smelting_item(value)
        else:
            self.set_fuel(value)

    def at(self, index):
        i = int(index)
        if i < 0 or i >= 2:
            return None
        return self.entity.fuel if i == 1 else self.entity.smelt_stack

    def remove_all_by_index(self, index):
        i = int(index)
        if i < 0 or i >= 2:
            return None
        if i == 0:
            self.entity.smelt_stack = None
        else:
            self.entity.fuel = None

    def get_items(self):
        return [self.entity.smelt_stack, self.entity.fuel]

    def remove_unnecessary_stacks(self):
        if self.entity.fuel is not None:
            if self.entity.fuel.amount == 0:
                self.entity.fuel = None
        if self.entity.smelt_stack is not None:
            if self.entity.smelt_stack.amount == 0:
                self.entity.smelt_stack = None


    def set_smelting_item(self, item):
        if item is None:
            return
        self.entity.smelt_stack = item
        self.entity.outcome_item = G.smelting_recipes.smelt(self.entity.smelt_stack.get_object())
        # no such recipe
        if self.entity.outcome_item is None:
            return
        else:
            self.entity.smelt()

    def set_fuel(self, fuel):
        if fuel is None:
            return
        self.entity.fuel = fuel
        # invalid fuel
        if self.entity.fuel.get_object().burning_time == -1:
            return
        else:
            self.entity.smelt()

    def set_outcome_callback(self, callback):
        self.entity.outcome_callback = callback

    def set_fuel_callback(self, callback):
        self.entity.fuel_callback = callback

    def get_smelt_outcome(self):
        return self.entity.smelt_outcome

class FarmBlock(Block):
    texture_name = "farmland_dry", "dirt", "dirt"
    icon_name = "farmland_dry"
    hardness = 0.5
    id = 60
    name = "Farm Dirt"
    break_sound = sounds.dirt_break

    def __init__(self):
        super(FarmBlock, self).__init__()
        self.drop_id = BlockID(DirtBlock.id)

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        # replace self with dirt
        if (self_pos[0], self_pos[1] + 1, self_pos[-1]) in world:
            world.remove_block(None, self_pos)
            world.add_block(self_pos, dirt_block)

class ChestBlock(Block):
    top_texture = 8, 4
    bottom_texture = 8, 2
    side_texture = 8, 3
    hardness = 2
    id = 54
    name = "Chest"
    burning_time = 15

# Wool blocks

class BlackWoolBlock(Block):
    texture_name = "cloth_15",
    icon_name = "cloth_15"
    hardness = 1
    id = 35,15
    name = "Black Wool"

class RedWoolBlock(Block):
    texture_name = "cloth_14",
    icon_name = "cloth_14"
    hardness = 1
    id = 35,14
    name = "Red Wool"

class GreenWoolBlock(Block):
    texture_name = "cloth_13",
    icon_name = "cloth_13"
    hardness = 1
    id = 35,13
    name = "Green Wool"

class BrownWoolBlock(Block):
    texture_name = "cloth_12",
    icon_name = "cloth_12"
    hardness = 1
    id = 35,12
    name = "Brown Wool"

class BlueWoolBlock(Block):
    texture_name = "cloth_11",
    icon_name = "cloth_11"
    hardness = 1
    id = 35,11
    name = "Blue Wool"

class PurpleWoolBlock(Block):
    texture_name = "cloth_10",
    icon_name = "cloth_10"
    hardness = 1
    id = 35,10
    name = "Purple Wool"

class CyanWoolBlock(Block):
    texture_name = "cloth_9",
    icon_name = "cloth_9"
    hardness = 1
    id = 35,9
    name = "Cyan Wool"

class LightGreyWoolBlock(Block):
    texture_name = "cloth_8",
    icon_name = "cloth_8"
    hardness = 1
    id = 35,8
    name = "Light Grey Wool"

class GreyWoolBlock(Block):
    texture_name = "cloth_7",
    icon_name = "cloth_7"
    hardness = 1
    id = 35,7
    name = "Grey Wool"

class PinkWoolBlock(Block):
    texture_name = "cloth_6",
    icon_name = "cloth_6"
    hardness = 1
    id = 35,6
    name = "Pink Wool"

class LimeWoolBlock(Block):
    texture_name = "cloth_5",
    icon_name = "cloth_5"
    hardness = 1
    id = 35,5
    name = "Lime Wool"

class YellowWoolBlock(Block):
    texture_name = "cloth_4",
    icon_name = "cloth_4"
    hardness = 1
    id = 35,4
    name = "Yellow Wool"

class LightBlueWoolBlock(Block):
    texture_name = "cloth_3",
    icon_name = "cloth_3"
    hardness = 1
    id = 35,3
    name = "Light Blue Wool"

class MagentaWoolBlock(Block):
    texture_name = "cloth_2",
    icon_name = "cloth_2"
    hardness = 1
    id = 35,2
    name = "Magenta Wool"

class OrangeWoolBlock(Block):
    texture_name = "cloth_1",
    icon_name = "cloth_1"
    hardness = 1
    id = 35,1
    name = "Orange Wool"

class WhiteWoolBlock(Block):
    texture_name = "cloth_0",
    icon_name = "cloth_0"
    hardness = 1
    id = 35,0
    name = "White Wool"
    amount_label_color = 0, 0, 0, 255

# Carpet blocks

class BlackCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_15",
    icon_name = "cloth_15"
    hardness = 1
    id = 171,15
    name = "Black Carpet"

class RedCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_14",
    icon_name = "cloth_14"
    hardness = 1
    id = 171,14
    name = "Red Carpet"

class GreenCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_13",
    icon_name = "cloth_13"
    hardness = 1
    id = 171,13
    name = "Green Carpet"

class BrownCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_12",
    icon_name = "cloth_12"
    hardness = 1
    id = 171,12
    name = "Brown Carpet"

class BlueCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_11",
    icon_name = "cloth_11"
    hardness = 1
    id = 171,11
    name = "Blue Carpet"

class PurpleCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_10",
    icon_name = "cloth_10"
    hardness = 1
    id = 171,10
    name = "Purple Carpet"

class CyanCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_9",
    icon_name = "cloth_9"
    hardness = 1
    id = 171,9
    name = "Cyan Carpet"

class LightGreyCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_8",
    icon_name = "cloth_8"
    hardness = 1
    id = 171,8
    name = "Light Grey Carpet"

class GreyCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_7",
    icon_name = "cloth_7"
    hardness = 1
    id = 171,7
    name = "Grey Carpet"

class PinkCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_6",
    icon_name = "cloth_6"
    hardness = 1
    id = 171,6
    name = "Pink Carpet"

class LimeCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_5",
    icon_name = "cloth_5"
    hardness = 1
    id = 171,5
    name = "Lime Carpet"

class YellowCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_4",
    icon_name = "cloth_4"
    hardness = 1
    id = 171,4
    name = "Yellow Carpet"

class LightBlueCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_3",
    icon_name = "cloth_3"
    hardness = 1
    id = 171,3
    name = "Light Blue Carpet"

class MagentaCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_2",
    icon_name = "cloth_2"
    hardness = 1
    id = 171,2
    name = "Magenta Carpet"

class OrangeCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_1",
    icon_name = "cloth_1"
    hardness = 1
    id = 171,1
    name = "Orange Carpet"

class WhiteCarpetBlock(Block):
    height = 0.05
    texture_name = "cloth_0",
    icon_name = "cloth_0"
    hardness = 1
    id = 171,0
    name = "White Carpet"
    amount_label_color = 0, 0, 0, 255

# moreplants
class RoseBlock(Block):
    vertex_mode = G.VERTEX_CROSS
    side_texture = 0, 0
    hardness = 0.0
    transparent = True
    density = 0.3
    id = 38
    texture_name = "rose", "rose", "rose"
    icon_name = "rose"
    name = "Rose"
    break_sound = sounds.leaves_break
    amount_label_color = 0, 0, 0, 255

    def __init__(self):
        super(RoseBlock, self).__init__()
        self.texture_data = self.texture_data[0:2 * 4 * 2]

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        if (self_pos[0], self_pos[1] - 1, self_pos[-1]) not in world:
            world.remove_block(None, self_pos)

class ReedBlock(Block):
    texture_name = "reeds"
    icon_name = "reeds"
    hardness = 0.0
    transparent = True
    vertex_mode = G.VERTEX_CROSS
    id = 83
    density = 0.8
    name = "Reed"
    crossed_sides = True
    max_stack_size = 16
    amount_label_color = 0, 0, 0, 255

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        if (self_pos[0], self_pos[1] - 1, self_pos[-1]) not in world:
            world.remove_block(None, self_pos)

class CropBlock(Block):
    top_texture = -1, -1
    bottom_texture = -1, -1
    side_texture = -1, -1
    vertex_mode = G.VERTEX_GRID
    hardness = 0.0
    transparent = True
    break_sound = sounds.leaves_break

    sub_id_as_metadata = True
    growth_stage = 0
    entity_type = CropEntity
    entity = None

    render_as_normal_block = False

    def __init__(self):
        super(CropBlock, self).__init__()
        self.top_texture = get_texture_coordinates(-1, -1)
        self.bottom_texture = get_texture_coordinates(-1, -1)

    def __del__(self):
        if self.entity is not None:
            del self.entity

    @property
    def texture_data(self):
        return self.get_texture_data()

    @texture_data.setter
    def texture_data(self, value):
        self._texture_data = value

    @property
    def drop_id(self):
        if self.growth_stage == self.max_growth_stage:
            return BlockID(296) # wheat
        else:
            return BlockID(295) #seed

    @drop_id.setter
    def drop_id(self, value):
        self._drop_id = value

    @property
    def growth_stage(self):
        return self.get_metadata()

    @growth_stage.setter
    def growth_stage(self, value):
        self.set_metadata(value)

    # called on client side
    def fertilize(self):
        if self.growth_stage == self.max_growth_stage:
            return False
        G.CLIENT.update_tile_entity(self.entity.position, make_nbt_from_dict({'action'.encode(): 'fertilize'.encode()}))
        return True
        
    def update_tile_entity(self, value):
        nbt = extract_nbt(value)
        # client side
        if 'growth_stage' in nbt:
            self.growth_stage = nbt['growth_stage']
            # update the texture
            self.entity.world.hide_block(self.entity.position)
            self.entity.world.show_block(self.entity.position)
        # server side
        elif 'action' in nbt:
            if nbt['action'] == 'fertilize':
                self.entity.fertilize()

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        if (self_pos[0], self_pos[1] - 1, self_pos[-1]) not in world:
            world.remove_block(None, self_pos)

class PotatoBlock(CropBlock):
    id = 142
    name = "Potato"
    max_stack_size = 16
    amount_label_color = 0, 0, 0, 255

    max_growth_stage = 3

    @property
    def texture_data(self):
        self.side_texture = get_texture_coordinates(self.growth_stage + 4, 9)
        self.front_texture = self.side_texture
        return self.get_texture_data()

    @property
    def drop_id(self):
        return BlockID(392)

    @drop_id.setter
    def drop_id(self, value):
        self._drop_id = value

class CarrotBlock(CropBlock):
    id = 141
    name = "Carrot"
    max_stack_size = 16
    amount_label_color = 0, 0, 0, 255

    max_growth_stage = 3

    @property
    def texture_data(self):
        self.side_texture = get_texture_coordinates(self.growth_stage, 9)
        self.front_texture = self.side_texture
        return self.get_texture_data()

    @property
    def drop_id(self):
        return BlockID(391)

    @drop_id.setter
    def drop_id(self, value):
        self._drop_id = value


class WheatCropBlock(CropBlock):
    id = 59
    name = "Wheat Crop"
    max_stack_size = 16
    amount_label_color = 0, 0, 0, 255

    max_growth_stage = 7

    # special hack to return different texture, which depends on the growth stage
    @property
    def texture_data(self):
        self.side_texture = get_texture_coordinates(14, self.growth_stage)
        self.front_texture = self.side_texture
        return self.get_texture_data()

    @property
    def drop_id(self):
        if self.growth_stage == self.max_growth_stage:
            return BlockID(296) # wheat
        else:
            return BlockID(295) #seed

    @drop_id.setter
    def drop_id(self, value):
        self._drop_id = value

class TallGrassBlock(Block):
    width = 0.9
    height = 0.9
    top_texture = -1, -1
    bottom_texture = -1, -1
    side_texture = 10, 4
    vertex_mode = G.VERTEX_CROSS
    hardness = 0.0
    transparent = True
    density = 0.3
    id = 31
    name = "Tall grass"
    break_sound = sounds.leaves_break
    amount_label_color = 0, 0, 0, 255

   # def __init__(self):
    #    super(TallGrassBlock, self).__init__()
    #    self.drop_id = BlockID(295) ## seed
    @property
    def drop_id(self):
        # 10% chance of dropping seed
        if randint(0, 10) == 0:
            return BlockID(295)
        return BlockID(0)

    @drop_id.setter
    def drop_id(self, value):
        self._drop_id = value

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        if (self_pos[0], self_pos[1] - 1, self_pos[-1]) not in world:
            world.remove_block(None, self_pos)

# More tall grass blocks

# Tall grass of different heights...


class Grass0Block(TallGrassBlock):
    density = 0.0
    id = 31, 1
    texture_name = 'wg_grass_06'


class Grass1Block(TallGrassBlock):
    density = 0.1
    id = 31, 2
    texture_name = 'wg_grass_00'


class Grass2Block(TallGrassBlock):
    density = 0.2
    id = 31, 3
    texture_name = 'wg_grass_01'


class Grass3Block(TallGrassBlock):
    density = 0.3
    id = 31, 4
    texture_name = 'wg_grass_03'


class Grass4Block(TallGrassBlock):
    density = 0.4
    id = 31, 5
    texture_name = 'wg_grass_02'


class Grass5Block(TallGrassBlock):
    density = 0.5
    id = 31, 6
    texture_name = 'wg_grass_04'


class Grass6Block(TallGrassBlock):
    density = 0.6
    id = 31, 7
    texture_name = 'wg_grass_05'


class Grass7Block(TallGrassBlock):
    density = 0.7
    id = 31, 8
    texture_name = 'wg_grass_07'


class DesertGrassBlock(TallGrassBlock):
    density = 0.3
    id = 31,1
    name = "Desert Grass"
    texture_name = 'wg_red_bush'

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        if (self_pos[0], self_pos[1] - 1, self_pos[-1]) not in world:
            world.remove_block(None, self_pos)


class DeadBushBlock(TallGrassBlock):
    density = 0.3
    id = 31,0
    name = "Dead bush"
    texture_name = 'deadbush'

    def on_neighbor_change(self, world, neighbor_pos, self_pos):
        if (self_pos[0], self_pos[1] - 1, self_pos[-1]) not in world:
            world.remove_block(None, self_pos)


class DiamondBlock(HardBlock):
    texture_name = "blockDiamond",
    icon_name = "blockDiamond"
    hardness = 5
    id = 57
    digging_tool = G.PICKAXE
    name = "Diamond Block"

class GoldBlock(HardBlock):
    texture_name = "blockGold",
    icon_name = "blockGold"
    hardness = 4
    id = 41
    digging_tool = G.PICKAXE
    name = "Gold Block"

class IronBlock(HardBlock):
    texture_name = "blockIron",
    icon_name = "blockIron"
    hardness = 4
    id = 42
    digging_tool = G.PICKAXE
    name = "Iron Block"

class StonebrickBlock(HardBlock):
    texture_name = "stonebricksmooth",
    icon_name = "stonebricksmooth"
    hardness = 1.5
    id = 98,0
    digging_tool = G.PICKAXE
    name = "Stone Bricks"

class CrackedStonebrickBlock(HardBlock):
    texture_name = "stonebricksmooth_cracked",
    icon_name = "stonebricksmooth_cracked"
    hardness = 1.5
    id = 98,1
    digging_tool = G.PICKAXE
    name = "Cracked Stone Bricks"

class MossyStonebrickBlock(HardBlock):
    texture_name = "stonebricksmooth_mossy",
    icon_name = "stonebricksmooth_mossy"
    hardness = 1.5
    id = 98,2
    digging_tool = G.PICKAXE
    name = "Mossy Stone Bricks"

class IceBlock(Block):
    texture_name = "ice",
    icon_name = "ice"
    id = 79
    hardness = 0.5
    transparent = True
    name = "Ice"
    amount_label_color = 0, 0, 0, 255

class MossyCobbleBlock(HardBlock):
    texture_name = "stoneMoss",
    icon_name = "stoneMoss"
    hardness = 1.5
    id = 48
    name = "Mossy Cobblestone"
    digging_tool = G.PICKAXE
    max_stack_size = 64


#  nether items

class NetherrackBlock(Block):
    texture_name = "dirt",
    hardness = 0.5
    id = 87
    name = "Netherrack"
    digging_tool = G.SHOVEL
    break_sound = sounds.dirt_break
    max_stack_size = 64

class NetherOreBlock(Block):
    texture_name = "dirt",
    hardness = 0.5
    id = 153
    name = "Nether Quartz Ore"
    digging_tool = G.SHOVEL
    break_sound = sounds.dirt_break
    max_stack_size = 64

class SoulsandBlock(Block):
    texture_name = "dirt",
    hardness = 0.5
    id = 88
    name = "Soul Sand"
    digging_tool = G.SHOVEL
    break_sound = sounds.dirt_break
    max_stack_size = 64

class CakeBlock(Block):
    height = 0.5
    width = 0.9
    texture_name = "cake_top", "cake_bottom", "cake_side"
    icon_name = "cake_top"
    hardness = 0.5
    id = 92
    name = "Cake"
    max_stack_size = 64

class BedBlock(Block):
    height = 0.5
    texture_name = "bed_head_top", "bed_head_top", "bed_head_end", "bed_head_side", "bed_head_side", "bed_head_side", \
                        "bed_feet_top", "bed_feet_top", "bed_feet_end", "bed_feet_side", "bed_feet_side", "bed_feet_side",
    id = 26

    # bed metadata
    # bit 7: 0 - head, 1 - tail
    # bit 1, bit 0: 00 - east, 01 - south, 10 - west, 11 - north
    sub_id_as_metadata = True

    hardness = 0.5
    digging_tool = G.AXE
    name = "Bed"    # cannot be obtained, doesn't matter

    def can_place_on(self, block_id):
        return (block_id != 0)

    def set_metadata(self, metadata):
        print 'metadata: ', metadata
        if self.sub_id_as_metadata:
            self.id.sub = metadata

CRACK_LEVELS = 10


# not a real block, used to store crack texture data
class CrackTextureBlock(object):
    def __init__(self):
        self.crack_level = CRACK_LEVELS
        self.texture_data = []
        texture_name = []
        for i in range(self.crack_level):
            texture_name.append('destroy_' + str(i))
        self.group = TextureGroupIndividual(texture_name)

        for i in range(self.crack_level):
            self.texture_data.append(self.group.texture_data[i * 8:(i + 1) * 8] * 6)

crack_textures = CrackTextureBlock()

# nether
nether_block = NetherrackBlock()
netherore_block = NetherOreBlock()
soulsand_block = SoulsandBlock()
# overworld blocks

air_block = AirBlock()
grass_block = GrassBlock()
sand_block = SandBlock()
brick_block = BrickBlock()
stone_block = StoneBlock()
dirt_block = DirtBlock()
lamp_block = LampBlock()
bedrock_block = BedrockBlock()
water_block = WaterBlock()
craft_block = CraftTableBlock()
sandstone_block = SandstoneBlock()
quartz_block = QuartzBlock()
stonebrick_block = StonebrickBlock()
birchwoodplank_block = BirchWoodPlankBlock()
junglewoodplank_block = JungleWoodPlankBlock()
oakwoodplank_block = OakWoodPlankBlock()
snowgrass_block = SnowGrassBlock()
oakwood_block = OakWoodBlock()
oakleaf_block = OakLeafBlock()
oakbranch_block = OakBranchBlock()
junglewood_block = JungleWoodBlock()
jungleleaf_block = JungleLeafBlock()
birchwood_block = BirchWoodBlock()
birchleaf_block = BirchLeafBlock()
cactus_block = CactusBlock()
coalore_block = CoalOreBlock()
ironore_block = IronOreBlock()
goldore_block = GoldOreBlock()
diamondore_block = DiamondOreBlock()
melon_block = MelonBlock()
stoneslab_block = StoneSlabBlock()
clay_block = ClayBlock()
cobble_block = CobbleBlock()
mossycobble_block = MossyCobbleBlock()
bookshelf_block = BookshelfBlock()
furnace_block = FurnaceBlock()
farm_block = FarmBlock()
glass_block = GlassBlock()
gravel_block = GravelBlock()
tallcactus_block = TallCactusBlock()
pumpkin_block = PumpkinBlock()
torch_block = TorchBlock()
yflowers_block = YFlowersBlock()
cobblefence_block = CobbleFenceBlock()
snow_block = SnowBlock()
meta_block = MetaBlock()
chest_block = ChestBlock()
cake_block = CakeBlock()
# wool
blackwool_block = BlackWoolBlock()
redwool_block = RedWoolBlock()
greenwool_block = GreenWoolBlock()
brownwool_block = BrownWoolBlock()
bluewool_block = BlueWoolBlock()
purplewool_block = PurpleWoolBlock()
cyanwool_block = CyanWoolBlock()
lightgreywool_block = LightGreyWoolBlock()
greywool_block = GreyWoolBlock()
pinkwool_block = PinkWoolBlock()
limewool_block = LimeWoolBlock()
yellowwool_block = YellowWoolBlock()
lightbluewool_block = LightBlueWoolBlock()
magentawool_block = MagentaWoolBlock()
orangewool_block = OrangeWoolBlock()
whitewool_block = WhiteWoolBlock()

# carpet
blackcarpet_block = BlackCarpetBlock()
redcarpet_block = RedCarpetBlock()
greencarpet_block = GreenCarpetBlock()
browncarpet_block = BrownCarpetBlock()
bluecarpet_block = BlueCarpetBlock()
purplecarpet_block = PurpleCarpetBlock()
cyancarpet_block = CyanCarpetBlock()
lightgreycarpet_block = LightGreyCarpetBlock()
greycarpet_block = GreyCarpetBlock()
pinkcarpet_block = PinkCarpetBlock()
limecarpet_block = LimeCarpetBlock()
yellowcarpet_block = YellowCarpetBlock()
lightbluecarpet_block = LightBlueCarpetBlock()
magentacarpet_block = MagentaCarpetBlock()
orangecarpet_block = OrangeCarpetBlock()
whitecarpet_block = WhiteCarpetBlock()

rose_block = RoseBlock()
reed_block = ReedBlock()
potato_block = PotatoBlock()
carrot_block = CarrotBlock()
diamond_block = DiamondBlock()
gold_block = GoldBlock()
iron_block = IronBlock()
stonebrickcracked_block = CrackedStonebrickBlock()
stonebrickmossy_block = MossyStonebrickBlock()
quartzcolumn_block = ColumnQuartzBlock()
quartzchiseled_block = ChiseledQuartzBlock()
quartzbrick_block = QuartzBrickBlock()
ice_block = IceBlock()
emeraldore_block = EmeraldOreBlock()
lapisore_block = LapisOreBlock()
rubyore_block = RubyOreBlock()
sapphireore_block = SapphireOreBlock()
fern_block = TallGrassBlock()
wheat_crop_block = WheatCropBlock()
#wild grass of different heights
wildgrass0_block = Grass0Block()
wildgrass1_block = Grass1Block()
wildgrass2_block = Grass2Block()
wildgrass3_block = Grass3Block()
wildgrass4_block = Grass4Block()
wildgrass5_block = Grass5Block()
wildgrass6_block = Grass6Block()
wildgrass7_block = Grass7Block()
desertgrass_block = DesertGrassBlock()
deadbush_block = DeadBushBlock()
bed_block = BedBlock()
