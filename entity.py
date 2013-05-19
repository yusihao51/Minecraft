# Imports, sorted alphabetically.

# Python packages
# Nothing for now...
import struct

# Third-party packages
# Nothing for now...

# Modules from this project
# Nothing for now...
import globals as G
from physics import physics_manager
from utils import make_nbt_from_dict


__all__ = (
    'Entity', 'TileEntity', 'CropEntity', 'FurnaceEntity',
)


class Entity(object):
    """
    Base class for players, mobs, TNT and so on.
    """
    def __init__(self, position, rotation, velocity=0, health=0, max_health=0,
                 attack_power=0, sight_range=0, attack_range=0):
        self.position = position
        self.momentum_previous = ()
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
        self.entity_id = None

    def can_handle(self, msg_type):
        return False

    def handle_message(self, msg_type, *args, **kwargs):
        pass

#
# Message type
#
MSG_PICKUP, \
MSG_REDSTONE_ACTIVATE, MSG_REDSTONE_DEACTIVATE, \
    = range(3)

class EntityManager(object):
    def __init__(self):
        self.last_id = 0
        self.entities = {}

    def add_entity(self, entity):
        self.last_id = self.last_id + 1
        self.entities[self.last_id] = entity
        self.entities[self.last_id].entity_id = self.last_id

    def remove_entity(self, entity_id):
        del self.entities[entity_id]

    def broadcast(self, msg_type, *args, **kwargs):
        for entity in self.entities:
            if entity.can_handle(msg_type):
                entity.handle_message(msg_type, *args, **kwargs)

    def send_message(self, receiver, msg_type, *args, **kwargs):
        if self.entities[receiver].can_handle(msg_type):
                self.entities[receiver].handle_message(msg_type, *args, **kwargs)

entity_manager = EntityManager()

class TileEntity(Entity):
    """
    A Tile entity is extra data associated with a block
    """
    def __init__(self, world, position):
        super(TileEntity, self).__init__(position, rotation=(0,0))
        self.world = world

# server-side only
class CropEntity(TileEntity):
    # seconds per stage
    grow_time = 10
    grow_task = None
    
    def __init__(self, world, position):
        super(CropEntity, self).__init__(world, position)
        self.grow_task = G.main_timer.add_task(self.grow_time, self.grow_callback)

    def __del__(self):
        if self.grow_task is not None:
            G.main_timer.remove_task(self.grow_task)
        if self.world is None:
            return
        if self.position in self.world:
            G.SERVER.hide_block(self.position)

    def grow_callback(self):
        if self.position in self.world:
            self.world[self.position].growth_stage = self.world[self.position].growth_stage + 1
            G.SERVER.update_tile_entity(self.position, make_nbt_from_dict({'growth_stage': self.world[self.position].growth_stage}))
        else:
            # the block ceased to exist
            return
        if self.world[self.position].growth_stage < self.world[self.position].max_growth_stage:
            self.grow_task = G.main_timer.add_task(self.grow_time, self.grow_callback)
        else:
            self.grow_task = None

    # called on server side
    def fertilize(self):
        if self.grow_task is not None:
            G.main_timer.remove_task(self.grow_task)
        if self.position in self.world:
            self.world[self.position].growth_stage = self.world[self.position].max_growth_stage
            G.SERVER.update_tile_entity(self.position, make_nbt_from_dict({'growth_stage': self.world[self.position].growth_stage}))
        else:
            # the block ceased to exist
            return

class FurnaceEntity(TileEntity):
    fuel = None
    smelt_stack = None
    outcome_item = None
    smelt_outcome = None # output slot

    fuel_task = None
    smelt_task = None

    outcome_callback = None
    fuel_callback = None

    def __del__(self):
        if self.fuel_task is not None:
            G.main_timer.remove_task(self.fuel_task)
        if self.smelt_task is not None:
            G.main_timer.remove_task(self.smelt_task)

    def full(self, reserve=0):
        if self.smelt_outcome is None:
            return False

        return self.smelt_outcome.get_object().max_stack_size < self.smelt_outcome.amount + reserve

    def full(self, reserve=0):
        if self.smelt_outcome is None:
            return False

        return self.smelt_outcome.get_object().max_stack_size < self.smelt_outcome.amount + reserve


    def smelt_done(self):
        self.smelt_task = None
        # outcome
        if self.smelt_outcome is None:
            self.smelt_outcome = self.outcome_item
        else:
            self.smelt_outcome.change_amount(self.outcome_item.amount)
        # cost
        self.smelt_stack.change_amount(-1)
        # input slot has been empty
        if self.smelt_stack.amount <= 0:
            self.smelt_stack = None
            self.outcome_item = None
        if self.outcome_callback is not None:
            if callable(self.outcome_callback):
                self.outcome_callback()
        # stop
        if self.smelt_stack is None:
            return
        if self.full(self.outcome_item.amount):
            return
        if self.fuel is None or self.fuel_task is None:
            return
        # smelting task
        self.smelt_task = G.main_timer.add_task(self.smelt_stack.get_object().smelting_time, self.smelt_done)

    def remove_fuel(self):
        if self.fuel_callback is not None:
            if callable(self.fuel_callback):
                self.fuel_callback()
        self.fuel_task = None
        self.fuel.change_amount(-1)
        if self.fuel.amount <= 0:
            self.fuel = None
            # stop smelting task
            if self.smelt_task is not None:
                G.main_timer.remove_task(self.smelt_task)
            self.smelt_task = None
            return

        # continue
        if self.smelt_task is not None:
            self.fuel_task = G.main_timer.add_task(self.fuel.get_object().burning_time, self.remove_fuel)

    def smelt(self):
        if self.fuel is None or self.smelt_stack is None:
            return
        # smelting
        if self.fuel_task is not None or self.smelt_task is not None:
            return
        if self.full():
            return

        burning_time = self.fuel.get_object().burning_time
        smelting_time = self.smelt_stack.get_object().smelting_time
        # fuel task: remove fuel
        self.fuel_task = G.main_timer.add_task(burning_time, self.remove_fuel)
        # smelting task
        self.smelt_task = G.main_timer.add_task(smelting_time, self.smelt_done)

class RedstoneTorchEntity(TileEntity):
    def __init__(self, world, position):
        super(RedstoneTorchEntity, self).__init__(world, position)
        self.activated = True

        entity_manager.broadcast(MSG_REDSTONE_ACTIVATE, position=self.position)

    def can_handle(self, msg_type):
        return msg_type == MSG_REDSTONE_ACTIVATE or msg_type == MSG_REDSTONE_DEACTIVATE

    def handle_message(self, msg_type, *args, **kwargs):
        pass

class DroppedBlockEntity(Entity):
    def __init__(self, world, position, item):
        super(DroppedBlockEntity, self).__init__(position, rotation=(0,0))
        self.world = world
        self.item_stack = item

    def can_handle(self, msg_type):
        return msg_type == MSG_PICKUP

    # argument: player
    def handle_message(self, msg_type, *args, **kwargs):
        if msg_type == MSG_PICKUP:
            pass
            # entity_manager.remove_entity(self.entity_id)

class FallingBlockEntity(Entity):
    def __init__(self, world, position):
        super(FallingBlockEntity, self).__init__(position, rotation=(0,0))
        self.world = world
        self.falling_block = world[position]

        physics_manager.do_physics(position, (0, -9.8, 0), self)

    def update_position(self, position):
        self.world.remove_block(None, self.position, sync=False)
        self.position = tuple(position)
        self.world.add_block(self.position, self.falling_block, sync=False)