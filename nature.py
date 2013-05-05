# Imports, sorted alphabetically.

# Python packages
import random

# Third-party packages
# Nothing for now...

# Modules from this project
from blocks import *


#
# Base
#


class SmallPlant(object):
    block = None
    grows_on = grass_block, dirt_block

    @classmethod
    def add_to_world(cls, world, position, sync=False):
        world.add_block(position, cls.block, sync=sync)


class Trunk(object):
    block = None
    height_range = 4, 8
    grows_on = ()

    def __init__(self, position, block=None, height_range=None):
        if block is not None:
            self.block = block
        if height_range is not None:
            self.height_range = height_range

        x, y, z = position

        self.height = random.randint(*self.height_range)
        self.blocks = {}
        for dy in range(self.height):
            self.blocks[(x, y + dy, z)] = self.block

    @classmethod
    def add_to_world(cls, world, position, sync=False):
        trunk = cls(position)
        for item in trunk.blocks.items():
            world.add_block(*item, sync=sync)


class Tree(object):
    trunk_block = None
    leaf_block = None
    trunk_height_range = 4, 8
    grows_on = grass_block, dirt_block, snowgrass_block

    @classmethod
    def add_to_world(cls, world, position, sync=False):
        trunk = Trunk(position, block=cls.trunk_block,
                      height_range=cls.trunk_height_range)

        for item in trunk.blocks.items():
            world.add_block(*item, force=False, sync=sync)

        x, y, z = position
        height = trunk.height
        treetop = y + height

        # Leaves generation
        d = height / 3 + 1
        for xl in range(x - d, x + d):
            dx = abs(xl - x)
            for yl in range(treetop - d, treetop + d):
                for zl in range(z - d, z + d):
                    # Don't replace existing blocks
                    if (xl, yl, zl) in world:
                        continue
                    # Avoids orphaned leaves
                    if not world.has_neighbors((xl, yl, zl),
                                               set((cls.trunk_block,
                                                    cls.leaf_block))):
                        continue
                    dz = abs(zl - z)
                    # The farther we are (horizontally) from the trunk,
                    # the least leaves we can find.
                    if random.uniform(0, dx + dz) > 0.6:
                        continue
                    world.add_block((xl, yl, zl), cls.leaf_block, force=False,
                                    sync=sync)


#
# Small plants
#


class WaterMelon(SmallPlant):
    block = melon_block
    grows_on = grass_block, dirt_block, snowgrass_block


class Pumpkin(SmallPlant):
    block = pumpkin_block
    grows_on = grass_block, dirt_block, snowgrass_block


class YFlowers(SmallPlant):
    block = yflowers_block


class Potato(SmallPlant):
    block = potato_block


class Carrot(SmallPlant):
    block = carrot_block


class Rose(SmallPlant):
    block = rose_block


class TallGrass(SmallPlant):
    block = fern_block


class TallGrass0(SmallPlant):
    block = wildgrass0_block
    grows_on = grass_block, dirt_block


class TallGrass1(SmallPlant):
    block = wildgrass1_block
    grows_on = grass_block, dirt_block


class TallGrass2(SmallPlant):
    block = wildgrass2_block
    grows_on = grass_block, dirt_block


class TallGrass3(SmallPlant):
    block = wildgrass3_block
    grows_on = grass_block, dirt_block


class TallGrass4(SmallPlant):
    block = wildgrass4_block
    grows_on = grass_block, dirt_block


class TallGrass5(SmallPlant):
    block = wildgrass5_block
    grows_on = grass_block, dirt_block


class TallGrass6(SmallPlant):
    block = wildgrass6_block
    grows_on = grass_block, dirt_block


class TallGrass7(SmallPlant):
    block = wildgrass7_block
    grows_on = grass_block, dirt_block


class DeadBush(SmallPlant):
    block = deadbush_block
    grows_on = sand_block, sandstone_block

class DesertGrass(SmallPlant):
    block = desertgrass_block
    grows_on = sand_block, sandstone_block

#
# Tall plants
#


class Cactus(Trunk):
    block = cactus_block
    height_range = 1, 4
    grows_on = sand_block, sandstone_block


class TallCactus(Trunk):
    block = tallcactus_block
    height_range = 1, 10
    grows_on = sand_block, sandstone_block


class Reed(Trunk):
    block = reed_block
    height_range = 1, 4
    grows_on = sand_block, dirt_block


#
# Trees
#


class OakTree(Tree):
    trunk_block = oakwood_block
    leaf_block = oakleaf_block


class JungleTree(Tree):
    trunk_block = junglewood_block
    leaf_block = jungleleaf_block
    trunk_height_range = 8, 12


class BirchTree(Tree):
    trunk_block = birchwood_block
    leaf_block = birchleaf_block
    trunk_height_range = 5, 7


SMALL_PLANTS = set((
    WaterMelon,
    Pumpkin,
    YFlowers,
    Potato,
    Carrot,
    Rose,
    TallGrass,
    TallGrass0,
    TallGrass1,
    TallGrass2,
    TallGrass3,
    TallGrass4,
    TallGrass5,
    TallGrass6,
    TallGrass7,
    DeadBush,
    DesertGrass,
))

TALL_PLANTS = set((
    Cactus,
    TallCactus,
    Reed,
))

PLANTS = SMALL_PLANTS | TALL_PLANTS

TREES = set((
    OakTree,
    JungleTree,
    BirchTree,
))


VEGETATION = PLANTS | TREES

TREE_BLOCKS = set(tree.trunk_block for tree in TREES)
LEAF_BLOCKS = set(tree.leaf_block for tree in TREES)
PLANT_BLOCKS = set(plant.block for plant in PLANTS)

VEGETATION_BLOCKS = PLANT_BLOCKS | TREE_BLOCKS | LEAF_BLOCKS
