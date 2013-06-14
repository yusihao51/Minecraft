import globals as G
from blocks import *
from items import *

class EmeraldHoe(Hoe):
    material = G.IRON_TOOL
    tool_type = G.HOE
    max_stack_size = 1
    id = 292,1
    durability = 50
    name = "Emerald Hoe"

class RubyHoe(Hoe):
    material = G.IRON_TOOL
    tool_type = G.HOE
    max_stack_size = 1
    id = 292,2
    durability = 60
    name = "Ruby Hoe"

class SapphireHoe(Hoe):
    material = G.IRON_TOOL
    tool_type = G.HOE
    max_stack_size = 1
    id = 292,3
    durability = 80
    name = "Sapphire Hoe"

class EmeraldShovel(Tool):
    material = G.IRON_TOOL
    tool_type = G.SHOVEL
    max_stack_size = 1
    id = 256,1
    durability = 60
    name = "Emerald Shovel"

class RubyShovel(Tool):
    material = G.IRON_TOOL
    tool_type = G.SHOVEL
    max_stack_size = 1
    id = 256,2
    durability = 40
    name = "Ruby Shovel"

class SapphireShovel(Tool):
    material = G.IRON_TOOL
    tool_type = G.SHOVEL
    max_stack_size = 1
    id = 256,3
    durability = 70
    name = "Sapphire Shovel"

class EmeraldPickaxe(Tool):
    material = G.IRON_TOOL
    tool_type = G.PICKAXE
    max_stack_size = 1
    id = 257,1
    durability = 50
    name = "Emerald Pickaxe"

class RubyPickaxe(Tool):
    material = G.IRON_TOOL
    tool_type = G.PICKAXE
    max_stack_size = 1
    id = 257,2
    durability = 100
    name = "Ruby Pickaxe"

class SapphirePickaxe(Tool):
    material = G.IRON_TOOL
    tool_type = G.PICKAXE
    max_stack_size = 1
    id = 257,3
    durability = 200
    name = "Sapphire Pickaxe"

class EmeraldAxe(Tool):
    material = G.IRON_TOOL
    tool_type = G.AXE
    max_stack_size = 1
    id = 258,1
    durability = 70
    name = "Emerald Axe"

class RubyAxe(Tool):
    material = G.IRON_TOOL
    tool_type = G.AXE
    max_stack_size = 1
    id = 258,2
    durability = 80
    name = "Ruby Axe"

class SapphireAxe(Tool):
    material = G.IRON_TOOL
    tool_type = G.AXE
    max_stack_size = 1
    id = 258,3
    durability = 80
    name = "Sapphire Axe"

def initialize(server=False):
    emerald_shovel = EmeraldShovel()
    emerald_hoe = EmeraldHoe()
    emerald_axe = EmeraldAxe()
    emerald_pickaxe = EmeraldPickaxe()
    ruby_pickaxe = RubyPickaxe()
    ruby_shovel = RubyShovel()
    ruby_axe = RubyAxe()
    ruby_hoe = RubyHoe()
    sapphire_hoe = SapphireHoe()
    sapphire_pickaxe = SapphirePickaxe()
    sapphire_shovel = SapphireShovel()
    sapphire_axe = SapphireAxe()

    # don't need to initialize crafting recipes on server
    if server: return

    for material, toolset in [(emeraldore_block, [emerald_pickaxe, emerald_axe, emerald_shovel, emerald_hoe]),
                              (rubyore_block, [ruby_pickaxe, ruby_axe, ruby_shovel, ruby_hoe]),
                              (sapphireore_block, [sapphire_pickaxe, sapphire_axe, sapphire_shovel, sapphire_hoe])]:
        G.recipes.add_recipe(["###", " @ ", " @ "], {'#': material, '@': stick_item},
                             ItemStack(toolset[0].id, amount=1))
        G.recipes.add_recipe(["## ", "#@ ", " @ "], {'#': material, '@': stick_item},
                             ItemStack(toolset[1].id, amount=1))
        G.recipes.add_recipe([" # ", " @ ", " @ "], {'#': material, '@': stick_item},
                             ItemStack(toolset[2].id, amount=1))
        G.recipes.add_recipe(["## ", " @ ", " @ "], {'#': material, '@': stick_item},
                             ItemStack(toolset[-1].id, amount=1))