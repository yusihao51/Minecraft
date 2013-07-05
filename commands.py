# Imports, sorted alphabetically.

# Python packages
import datetime
import os
import re

# Third-party packages
import pyglet

# Modules from this project
from blocks import BlockID
from items import get_item
import globals as G
from savingsystem import save_world


__all__ = (
    'COMMAND_HANDLED', 'COMMAND_NOT_HANDLED', 'COMMAND_INFO_COLOR',
    'COMMAND_ERROR_COLOR', 'set_terrain', 'next_terrain', 'CommandException',
    'UnknownCommandException', 'CommandParser', 'Command', 'HelpCommand',
    'GiveBlockCommand', 'SetTimeCommand', 'GetIDCommand', 'SetSnowCommand',
    'SetPlainsCommand', 'SetDesertCommand', 'SetMountainsCommand',
    'TakeScreencapCommand',
)


COMMAND_HANDLED = True
COMMAND_NOT_HANDLED = None
COMMAND_INFO_COLOR = (41, 125, 255, 255)
COMMAND_ERROR_COLOR = (255, 0, 0, 255)
set_terrain = 0
next_terrain = 'plains'

class CommandException(Exception):
    def __init__(self, command_text, message=None, *args, **kwargs):
        super(CommandException, self).__init__(self, message, *args, **kwargs)
        self.command_text = command_text
        self.message = message

    def __str__(self):
        return self.message


class UnknownCommandException(CommandException):
    def __init__(self, command_text, *args, **kwargs):
        super(UnknownCommandException, self).__init__(command_text, *args, **kwargs)
        self.message = "$$rUnknown command. Try /help for help."


class CommandParser(object):
    """
    Entry point for parsing and executing game commands.
    """
    def parse(self, command_text, user=None, world=None):
        """
        Parse the specified string and find the Command and match
        information that can handle it. Returns None if no known
        commands can handle it.
        """
        if command_text.startswith("/"):
            stripped = command_text[1:].strip()
            # Look for a subclass of Command whose format matches command_text
            for command_type in Command.__subclasses__():
                if not hasattr(command_type, "command"):
                    raise Exception("Subclasses of Command must have a command attribute.")
                cmd_regex = command_type.command
                match = re.match(cmd_regex, stripped)
                if match:
                    instance = command_type(stripped, user, world)
                    return instance, match
        return None

    def execute(self, command_text, user=None, world=None):
        """
        Finds and executes the first command that can handle the specified
        string. If the command has a return value, that value is returned.
        If it does not, then COMMAND_HANDLED is returned. If no commands
        can handle the string, COMMAND_NOT_HANDLED is returned.
        """
        parsed = self.parse(command_text, user=user, world=world)
        if parsed:
            command, match = parsed
            # Pass matched groups to command.execute
            # ...but filter out "None" arguments. If commands
            # want optional arguments, they should use keyword arguments
            # in their execute methods.
            args = filter(lambda a: a is not None, match.groups())
            kwargs = {}
            for key, value in match.groupdict().iteritems():
                if value is not None:
                    kwargs[key] = value
            ret = command.execute(*args, **kwargs)
            if ret is None:
                return COMMAND_HANDLED
            else:
                return ret
        else:
            if command_text.startswith("/"):
                raise UnknownCommandException(command_text)
            return COMMAND_NOT_HANDLED


class Command(object):
    command = None
    help_text = None

    def __init__(self, command_text, user, world):
        self.command_text = command_text
        self.user = user
        self.world = world

    def execute(self, *args, **kwargs):
        pass

    def send_info(self, text):
        self.user.sendchat(text, color=COMMAND_INFO_COLOR)

    def send_error(self, text):
        self.user.sendchat(text, color=COMMAND_ERROR_COLOR)


class HelpCommand(Command):
    command = r"^help$"
    help_text = "$$yhelp: $$DShow this help information"

    def execute(self, *args, **kwargs):
        self.send_info("****** Available Commands ******")
        for command_type in Command.__subclasses__():
            if hasattr(command_type, 'help_text') and command_type.help_text:
                self.send_info(command_type.help_text)


class GiveBlockCommand(Command):
    command = r"^give (\d+(?:[\.,]\d+)?)(?:\s+(\d+))?$"
    help_text = "$$ygive <block_id> [amount]: $$DGive a specified amount (default of 1) of the item to the player"

    def execute(self, block_id, amount=1, *args, **kwargs):
        try:
            bid = BlockID(block_id)
            item_or_block = get_item(float("%s.%s" % (bid.main, bid.sub)))
            self.send_info("Giving %s of '%s'." % (amount, item_or_block.name))
            self.user.inventory.add_item(bid, quantity=int(amount))
            #self.controller.item_list.update_items()
            #self.controller.inventory_list.update_items()
        except KeyError:
            raise CommandException(self.command_text, message="ID %s unknown." % block_id)
        except ValueError:
            raise CommandException(self.command_text, message="ID should be a number. Amount must be an integer.")


class SetTimeCommand(Command):
    command = r"^time set (\d+)$"
    help_text = "$$ytime set <number>: $$DSet the time of day 00-24"

    def execute(self, time, *args, **kwargs):
        try:
            tod = int(time)
            if 0 <= tod <= 24:
                self.send_info("Setting time to %s" % tod)
                #self.controller.time_of_day = tod
            else:
                raise ValueError
        except ValueError:
            raise CommandException(self.command_text, message="Time should be a number between 0 and 24")


class GetIDCommand(Command):
    command = r"^id$"
    help_text = "$$yid: $$DGet the id of the active item"

    def execute(self, *args, **kwargs):
        #current = self.controller.item_list.get_current_block()
        current = None
        if current:
            self.send_info("ID: %s" % current.id)
        else:
            self.send_info("ID: None")

class SeedCommand(Command):
    command = r"^seed$"
    help_text = "$$yseed: $$DGet the seed of the world"

    def execute(self, *args, **kwargs):
        self.send_info("Seed: %s" % G.SEED) 

class MeCommand(Command):
    command = r"^me (\w+)$"
    help_text = "$$yme <actiontext>: $$DTell people what you are doing"

    def execute(self, actiontext, *args, **kwargs):
        self.user.broadcast("* %s %s" % (self.user.username, actiontext))

class TellCommand(Command):
    command = r"^tell (\w+) (.+)$"
    help_text = "$$ytell <playername> <message>: $$DSend a private message to a player on the server"

    def execute(self, playername, message, *args, **kwargs):
        try:
            self.user.lookup_player(playername).sendinfo("%s whispered: %s " % (self.user.username, message))
        except AttributeError:
            raise CommandException(self.command_text, message="Player %s not found." % playername)

class SaveCommand(Command):
    command = r"^save$"
    help_text = "$$ysave: Save the game."

    def execute(self):
        save_world(G.SERVER, "world")