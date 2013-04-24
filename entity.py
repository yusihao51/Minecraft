# Imports, sorted alphabetically.

# Python packages
# Nothing for now...

# Third-party packages
# Nothing for now...

# Modules from this project
# Nothing for now...
import globals as G


__all__ = (
    'Entity', 'TileEntity', 'WheatCropEntity',
)


class Entity(object):
    """
    Base class for players, mobs, TNT and so on.
    """
    def __init__(self, position, rotation, velocity=0, health=0, max_health=0,
                 attack_power=0, sight_range=0, attack_range=0):
        self.position = position
        self.rotation = rotation
        self.velocity = velocity
        self.health = health
        self.max_health = max_health
        # Attack power in hardness per second.  We will probably need to change
        # that later to include equiped weapon etc.
        self.attack_power = attack_power
        # Sight range is currently unusued - we probably want
        # it to check if monsters can see player
        self.sight_range = sight_range
        self.attack_range = attack_range

class TileEntity(Entity):
    """
    A Tile entity is extra data associated with a block
    """
    def __init__(self, world, position):
        super(TileEntity, self).__init__(position, rotation=(0,0))
        self.world = world

class WheatCropEntity(TileEntity):
    # seconds per stage
    grow_time = 10
    grow_task = None
    
    def __init__(self, world, position):
        super(WheatCropEntity, self).__init__(world, position)
        self.grow_task = G.main_timer.add_task(self.grow_time, self.grow_callback)

    def __del__(self):
        if self.grow_task is not None:
            G.main_timer.remove_task(self.grow_task)
        if self.world is None:
            return
        if self.position in self.world:
            self.world.hide_block(self.position)

    def grow_callback(self):
        if self.position in self.world:
            self.world[self.position].growth_stage = self.world[self.position].growth_stage + 1
            self.world.hide_block(self.position)
            self.world.show_block(self.position)
        else:
            # the block ceased to exist
            return
        if self.world[self.position].growth_stage < 7:
            self.grow_task = G.main_timer.add_task(self.grow_time, self.grow_callback)
        else:
            self.grow_task = None

# TODO: furnace entity
