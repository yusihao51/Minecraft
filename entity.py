# Imports, sorted alphabetically.

# Python packages
# Nothing for now...

# Third-party packages
from sqlalchemy import Column, Integer, Float
from sqlalchemy.ext.declarative import AbstractConcreteBase

# Modules from this project
import globals as G


class Entity(AbstractConcreteBase, G.SQLBase):
    """
    Base class for players, mobs, TNT and so on.
    """

    pk = Column(Integer, primary_key=True)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)

    rotation_x = Column(Float)
    rotation_y = Column(Float)
    velocity = Column(Float)
    health = Column(Float)

    max_health = 0
    # Attack power in hardness per second.  We will probably need to change
    # that later to include equiped weapon etc.
    attack_power = 0
    # Sight range is currently unusued - we probably want
    # it to check if monsters can see player
    sight_range = 0
    attack_range = 0

    def __init__(self, position, rotation, velocity=0, health=0):
        super(Entity, self).__init__()
        self.position = position
        self.rotation = rotation
        self.velocity = velocity
        self.health = health

    @property
    def position(self):
        return self.x, self.y, self.z

    @position.setter
    def position(self, value):
        self.x, self.y, self.z = value

    @property
    def rotation(self):
        return self.rotation_x, self.rotation_y

    @rotation.setter
    def rotation(self, value):
        self.rotation_x, self.rotation_y = value
