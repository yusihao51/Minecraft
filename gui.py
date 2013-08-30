# Imports, sorted alphabetically.

# Python packages
import random
from math import floor, ceil
from functools import partial

# Third-party packages
import pyglet
from pyglet.gl import *
from pyglet.text import Label
from pyglet.window import key
from pyglet.image.atlas import TextureAtlas

# Modules from this project
from blocks import air_block
# FIXME: Initialize crafting in a proper way, other than by importing.
import crafting
import globals as G
from inventory import Inventory
from items import ItemStack
from utils import load_image, image_sprite, hidden_image_sprite, get_block_icon


__all__ = (
    'Rectangle', 'Button', 'ToggleButton', 'Control', 'AbstractInventory',
    'ItemSelector', 'InventorySelector', 'TextWidget', 'ProgressBarWidget',
    'frame_image', 'button_image', 'button_highlighted', 'button_disabled',
    'background_image', 'backdrop_images', 'rnd_backdrops', 'backdrop', 'ScrollbarWidget',
    'resize_button_image'
)


class Rectangle(object):
    def __init__(self, x, y, width, height):
        self.position = x, y
        self.size = width, height

    def hit_test(self, x, y):
        return (x >= self.min[0] and x <= self.max[0]) and (y >= self.min[1] and y <= self.max[1])

    def vertex_list(self):
        return [self.x, self.y,
                self.x + self.width, self.y,
                self.x + self.width, self.y + self.height,
                self.x, self.y + self.height]

    @property
    def position(self):
        return self.x, self.y

    @position.setter
    def position(self, position):
        self.x, self.y = position

    @property
    def size(self):
        return self.width, self.height

    @size.setter
    def size(self, size):
        self.width, self.height = size

    @property
    def center(self):
        return self.x + self.width / 2, self.y + self.height / 2

    @property
    def min(self):
        return (self.x, self.y)

    @property
    def max(self):
        return (self.x + self.width, self.y + self.height)

class Button(pyglet.event.EventDispatcher, Rectangle):
    def __init__(self, parent, x, y, width, height, image=None, image_highlighted=None, caption=None, batch=None, group=None, label_group=None, font_name=G.DEFAULT_FONT, enabled=True):
        super(Button, self).__init__(x, y, width, height)
        parent.push_handlers(self)
        self.batch, self.group, self.label_group = batch, group, label_group
        self.sprite = image_sprite(image, self.batch, self.group)
        self.sprite.scale = max(float(self.width) / float(image.width), float(self.height) / float(image.height))
        self.sprite_highlighted = hidden_image_sprite(image_highlighted, self.batch, self.group)
        self.sprite_highlighted.scale = max(float(self.width) / float(image_highlighted.width), float(self.height) / float(image_highlighted.height))
        self.highlighted = False
        self.label = Label(str(caption), font_name, 12, anchor_x='center', anchor_y='center',
            color=(255, 255, 255, 255), batch=self.batch, group=self.label_group) if caption else None
        self.position = x, y
        self.enable(enabled)

    def enable(self, enabled=True):
        self.enabled = enabled
        opacity = 255 if self.enabled else 100
        if self.sprite:
            self.sprite.opacity = opacity
        if self.sprite_highlighted:    
            self.sprite_highlighted.opacity = opacity
        if self.label:
            self.label.color = (255, 255, 255, opacity)    

    def disable(self, enabled=False):
        self.enable(enabled)

    @property
    def position(self):
        return self.x, self.y

    @position.setter
    def position(self, position):
        self.x, self.y = position
        if hasattr(self, 'sprite') and self.sprite:
            self.sprite.x, self.sprite.y = position
        if hasattr(self, 'sprite_highlighted') and self.sprite_highlighted:
            self.sprite_highlighted.x, self.sprite_highlighted.y = position
        if hasattr(self, 'label') and self.label:
            self.label.x, self.label.y = self.center
            
    @property
    def caption(self):
        return self.label.text

    @caption.setter
    def caption(self, text):
        self.label.text = text

    def draw(self):
        self.draw_sprite()
        self.draw_label()

    def draw_sprite(self):
        if self.sprite and not (self.sprite_highlighted and self.highlighted):
            self.sprite_highlighted.visible, self.sprite.visible = False, True
            self.sprite.draw()
        elif self.sprite_highlighted and self.highlighted:
            self.sprite_highlighted.visible, self.sprite.visible = True, False
            self.sprite_highlighted.draw()

    def draw_label(self):
        if self.label:
            self.label.draw()

    def on_mouse_click(self, x, y, button, modifiers):
        if self.enabled and self.hit_test(x, y):
            self.dispatch_event('on_click')

Button.register_event_type('on_click')


class ToggleButton(Button):

    _toggled = False

    @property
    def toggled(self):
        return self._toggled

    @toggled.setter
    def toggled(self, value):
        self._toggled = value
        if self.label:
            if self._toggled:
                color = (100, 0, 100, 255)
            else:
                color = (255, 255, 255, 255)
            self.label.color = color

    def __init__(self, parent, x, y, width, height, image=None, image_highlighted=None, caption=None, batch=None, group=None, label_group=None, font_name=G.DEFAULT_FONT, enabled=True):
        super(ToggleButton, self).__init__(parent, x, y, width, height, image=image, image_highlighted=image_highlighted, caption=caption, batch=batch, group=group, label_group=label_group, font_name=font_name, enabled=enabled)

    def on_mouse_click(self, x, y, button, modifiers):
        if self.enabled and self.hit_test(x, y):
            self.toggled = not self._toggled
            self.dispatch_event('on_toggle')
        super(ToggleButton, self).on_mouse_click( x, y, button, modifiers)

ToggleButton.register_event_type('on_toggle')

class Slot(pyglet.event.EventDispatcher, Rectangle):

    _item = None
    _hightlight = None

    def __init__(self, parent, x, y, width, height, inventory=None, index=0, is_quickslot=False, world=None, batch=None, group=None, label_group=None):
        super(Slot, self).__init__(x, y, width, height)
        parent.push_handlers(self)
        self.batch, self.group = batch, group
        self.label_group = label_group
        self.position = x, y
        self.world = world
        self.amount_label = None
        self.is_quickslot = is_quickslot
        self.icon = None
        self.inventory = inventory
        self.index = index
        self.vertex_list = None

    def __repr__(self):
        return "Slot #" + str(self.index) + " in " + repr(self.inventory)

    @property
    def item(self):
        return self._item

    @item.setter
    def item(self, value):
        self._item = value
        if self.amount_label:
            self.amount_label.delete()
        self.amount_label = None
        if not value:
            self.icon = None
            return
        img = get_block_icon(self._item.get_object(), self.width, self.world)
        self.icon = image_sprite(img, self.batch, self.group)
        image_scale = 1.0 / (img.width / self.width)
        self.icon.scale = image_scale
        self.icon.x = self.x
        self.icon.y = self.y
        if self.is_quickslot:
            self._item.quickslots_x = self.icon.x
            self._item.quickslots_y = self.icon.y
        if self._item.max_durability != -1 and self._item.durability != -1:
            self.icon.opacity = min(self._item.max_durability, self._item.durability + 1) * 255 / self._item.max_durability

        if self._item.amount > 1:
            self.amount_label = pyglet.text.Label(
                str(self._item.amount), font_name=G.DEFAULT_FONT, font_size=9,
                x=self.icon.x + 8, y=self.icon.y, anchor_x='left', anchor_y='bottom',
                color=self._item.get_object().amount_label_color, batch=self.batch,
                group=self.label_group)

    @property
    def highlighted(self):
        return self._hightlight

    @highlighted.setter
    def highlighted(self, value):
        if self.vertex_list:
            self.vertex_list.delete()
            self.vertex_list = None

        if value:
            self.vertex_list = self.batch.add(4, GL_QUADS, self.group,
                                     ('v2f', [self.x, self.y, self.x + self.width, self.y, self.x + self.width, self.y + self.height, self.x, self.y + self.height]),
                                     ('c4B', (255, 255, 255, 100) * 4))

    def on_mouse_click(self, x, y, button, modifiers):
        if self.hit_test(x, y):
            self.dispatch_event('on_click')

Slot.register_event_type('on_click')

class Control(pyglet.event.EventDispatcher):
    def __init__(self, parent, visible=True, *args, **kwargs):
        self.parent = parent
        self.visible = visible
        self.focused = False
        self.x, self.y, self.width, self.height = 0, 0, 0, 0

    def toggle(self, state=None):
        self.visible = not self.visible if state is None else state
        self.focused = not self.focused if state is None else state
        self._on_toggled()
        self.dispatch_event('on_toggled')

    def draw(self):
        if self.visible:
            self._on_draw()

    def focus(self):
        self.focused = True

    def _on_toggled(self):
        pass

    def _on_draw(self):
        pass

Control.register_event_type('on_toggled')
Control.register_event_type('key_released')

class AbstractInventory(Control):
    def __init__(self, parent, *args, **kwargs):
        super(AbstractInventory, self).__init__(parent, *args, **kwargs)
        self._current_index = 0
        self.batch = pyglet.graphics.Batch()
        self.group = pyglet.graphics.OrderedGroup(1)
        self.labels_group = pyglet.graphics.OrderedGroup(2)

    @property
    def current_index(self):
        return int(self._current_index)

    @current_index.setter
    def current_index(self, value):
        self._current_index = value % self.max_items
        self.update_current()

    def update_current(self):
        pass

class ItemSelector(AbstractInventory):
    def __init__(self, parent, player, world, *args, **kwargs):
        super(ItemSelector, self).__init__(parent, *args, **kwargs)
        self.world = world
        self.player = player
        self.max_items = 9
        self.icon_size = 32
        self.visible = True
        self.num_keys = [getattr(G, 'INVENTORY_%d_KEY' % i)
                         for i in range(1, 10)]

        image = G.texture_pack_list.selected_texture_pack.load_texture(['gui', 'gui.png'])
        image_scale = image.height / 256
        x_size = 182 * image_scale
        y_size = 22 * image_scale
        self.frame = image_sprite(image, self.batch, 0, y=image.height - y_size, height=y_size, x=0, width=x_size)
        self.frame.scale = (1.0 / image_scale) * 2
        self.frame.x = (self.parent.window.width - self.frame.width) / 2

        heart_image = load_image('resources', 'gui', 'heart.png')
        frame_size = image.height / 2

        x_size = 24 * image_scale
        y_size = 22 * image_scale

        self.active = image_sprite(image, self.batch, 0, y=(image.height - (y_size + (22 * image_scale))), height=y_size, x=0, width=x_size)
        self.active.scale = (1.0 / image_scale) * 2
        self.slots = []
        
        slot_x = self.frame.x + 8
        slot_y = self.frame.y + 8
        for i in range(1, self.max_items + 1):
            self.slots.append(Slot(self, slot_x, slot_y, self.icon_size, self.icon_size, inventory=self.player.quick_slots, index=i-1, is_quickslot=True, world=self.world, batch=self.batch, group=self.group, label_group=self.labels_group))
            slot_x += self.icon_size + 8

        self.hearts = []

        for i in range(0, 10):
            heart = image_sprite(heart_image, self.batch, 0)
            self.hearts.append(heart)
        self.current_block_label = None

    def update_items(self):
        self.player.quick_slots.remove_unnecessary_stacks()
        items = self.player.quick_slots.get_items()
        items = items[:self.max_items]
        i = 0
        for item in items:
            self.slots[i].item = item
            i += 1
        self.update_current()

    def update_current(self):
        if self.current_block_label:
            self.current_block_label.delete()
        if hasattr(self.get_current_block_item(False), 'quickslots_x') and hasattr(self.get_current_block_item(False), 'quickslots_y'):
            self.current_block_label = pyglet.text.Label(
                self.get_current_block_item(False).name, font_name=G.DEFAULT_FONT, font_size=9,
                x=self.get_current_block_item(False).quickslots_x + 0.25 * self.icon_size, y=self.get_current_block_item(False).quickslots_y - 20,
                anchor_x='center', anchor_y='bottom',
                color=(255, 255, 255, 255), batch=self.batch,
                group=self.labels_group)
        self.active.x = self.frame.x + (self.current_index * 40) - 2

    def update_health(self):
        hearts_to_show = self.player.health
        showed_hearts = 0
        for i, heart in enumerate(self.hearts):
            heart.x = self.frame.x + i * (20 + 2) + (self.frame.width - hearts_to_show * (20 + 2)) / 2
            heart.y = self.icon_size * 1.0 + 12
            heart.visible = True
            if showed_hearts >= hearts_to_show:
                heart.visible = False
            showed_hearts += 1

    def get_current_block(self):
        item = self.player.quick_slots.at(self.current_index)
        if not item:
            return
        return item.get_object()

    def get_current_block_item(self, remove=False):
        item = self.player.quick_slots.at(self.current_index)
        if remove:
            self.player.quick_slots.remove_by_index(self.current_index,
                                                        quantity=item.amount)
        return item

    def get_current_block_item_and_amount(self, remove=True):
        item = self.player.quick_slots.at(self.current_index)
        if item:
            amount = item.amount
            if remove:
                self.player.quick_slots.remove_by_index(self.current_index,
                                                        quantity=item.amount)
            return item, amount
        return False

    def remove_current_block(self, quantity=1):
        self.player.quick_slots.remove_by_index(self.current_index, quantity=quantity)
        self.update_items()

    def _on_toggled(self):
        if self.visible:
            self.update_items()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.visible and self.parent.window.exclusive:
            self.current_index -= scroll_y
            return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        if self.visible:
            if symbol in self.num_keys:
                index = (symbol - self.num_keys[0])
                self.current_index = index
                return pyglet.event.EVENT_HANDLED
            elif symbol == G.VALIDATE_KEY:
                current_block = self.get_current_block_item_and_amount()
                if current_block:
                    if not self.player.inventory.add_item(
                            current_block[0].id, quantity=current_block[1], durability=current_block[0].durability):
                        self.player.quick_slots.add_item(
                            current_block[0].id, quantity=current_block[1], durability=current_block[0].durability)
                    self.update_items()
                    return pyglet.event.EVENT_HANDLED

    def on_resize(self, width, height):
        self.frame.x = (width - self.frame.width) / 2
        self.frame.y = 0
        self.active.y = self.frame.y + 2
        slot_x = self.frame.x + 8
        slot_y = self.frame.y + 8
        for slot in self.slots:
            slot.x = slot_x
            slot_x += self.icon_size + 8

        if self.visible:
            self.update_health()
            self.update_current()
            self.update_items()

    def _on_draw(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.batch.draw()
        glDisable(GL_BLEND)


class InventorySelector(AbstractInventory):
    def __init__(self, parent, player, world, *args, **kwargs):
        super(InventorySelector, self).__init__(parent, *args, **kwargs)
        # inv, crafting, furnace and common slots
        self.batch = [ pyglet.graphics.Batch() ] * 4
        self.group = [ pyglet.graphics.OrderedGroup(x) for x in range(1, 5) ]
        self.parent = parent
        self.world = world
        self.player = player
        self.max_items = self.player.inventory.slot_count
        self.current_index = 1
        self.icon_size = 32
        self.selected_item = None
        self.selected_item_icon = None
        self.mode = 0 # 0 - Normal inventory, 1 - Crafting Table, 2 - Furnace
        self.change_image()
        self.crafting_panel = Inventory(4)
        self.crafting_outcome = None  # should be an item stack
        self.crafting_table_panel = Inventory(9)
        self.furnace_panel = None   # should be a FurnaceBlock
        self.visible = False
        self.slots = None
        # slots for inventory and crafting table
        self.inv_slots = []
        self.crafting_slots = []
        self.furnace_slots = []

        # inventory slots - common
        # 9 items per row
        rows = floor(self.max_items / 9)
        inventory_y = 0
        inventory_height = (rows * (self.icon_size + 8)) + ((rows+1) * 3)
        slot_x = self.frame.x + 16
        slot_y = self.frame.y + inventory_y + inventory_height
        for i in range(1, self.max_items + 1):
            slot = Slot(self, slot_x, slot_y, self.icon_size, self.icon_size, inventory=self.player.inventory, index=i-1, is_quickslot=False, world=self.world, batch=self.batch[3], group=self.group[3], label_group=self.labels_group)
            slot_x += self.icon_size + 4
            if slot_x >= (self.frame.x + self.frame.width) - 16:
                slot_x = self.frame.x + 16
                slot_y -= self.icon_size + 4
            self.inv_slots.append(slot)
            self.crafting_slots.append(slot)
            self.furnace_slots.append(slot)


        # quick slots - common
        slot_x = self.frame.x + 16
        slot_y = self.frame.y + 16
        for i in range(1, self.player.quick_slots.slot_count + 1):
            slot = Slot(self, slot_x, slot_y, self.icon_size, self.icon_size, inventory=self.player.quick_slots, index=i-1, is_quickslot=True, world=self.world, batch=self.batch[3], group=self.group[3], label_group=self.labels_group)
            slot_x += self.icon_size + 4
            self.inv_slots.append(slot)
            self.crafting_slots.append(slot)
            self.furnace_slots.append(slot)

        # armor slots - inventory only
        slot_x = self.frame.x + 16
        slot_y = inventory_y + inventory_height + (4 * self.icon_size) - 10
        for i in range(1, 4 + 1):
            slot = Slot(self, slot_x, slot_y, self.icon_size, self.icon_size, inventory=self.player.armor, index=i-1, is_quickslot=False, world=self.world, batch=self.batch[0], group=self.group[0], label_group=self.labels_group)
            slot_y += self.icon_size + 4
            self.inv_slots.append(slot)

        # crafting slots
        # only for inventory and crafting table, furnace slots initialization is in self.set_furnace
        for mode, panel, slots in [(0, self.crafting_panel, self.inv_slots),
                                   (1, self.crafting_table_panel, self.crafting_slots)]:
            crafting_rows = (2 if mode == 0 else 3 if mode == 1 else 2)
            slot_x = self.frame.x + (176 if mode == 0 else 56 if mode == 1 else 63)
            slot_y = self.frame.y + (inventory_y + inventory_height + (46 if mode == 0 else 25 if mode == 1 else 32)) + ((crafting_rows * self.icon_size) + (crafting_rows * 3))
            self.current_panel = panel

            for i in range(1, self.current_panel.slot_count + 1):
                slot = Slot(self, slot_x, slot_y, self.icon_size, self.icon_size, inventory=self.current_panel, index=i-1, is_quickslot=False, world=self.world, batch=self.batch[mode], group=self.group[mode], label_group=self.labels_group)
                slots.append(slot)
                slot_x += self.icon_size + 4
                if i%(2 if mode == 0 else 3 if mode == 1 else 1) == 0:
                    slot_x = self.frame.x + (176 if mode == 0 else 56 if mode == 1 else 63)
                    slot_y -= self.icon_size + 4

        # crafting outcome slot
        for mode, slots in [(0, self.inv_slots),
                            (1, self.crafting_slots),
                            (2, self.furnace_slots)]:
            slot_x, slot_y = 0, 0
            if mode == 0:
                slot_x, slot_y = 288, 96
            elif mode == 1:
                slot_x, slot_y = 246, 64
            elif mode == 2:
                slot_x, slot_y = 222, 67

            slot = Slot(self, self.frame.x + slot_x, self.frame.y + inventory_y + inventory_height + slot_y, self.icon_size, self.icon_size, inventory=0, index=256, is_quickslot=False, world=self.world, batch=self.batch[mode], group=self.group[mode], label_group=self.labels_group)
            slots.append(slot)
        self.switch_mode(0)

    def switch_mode(self, mode=0, reset_mode=True):
        self.mode = mode
        self.change_image()
        if mode == 0:
            self.slots = self.inv_slots
            self.current_panel = self.crafting_panel
            if reset_mode: self.reset_furnace()
        elif mode == 1:
            self.current_panel = self.crafting_table_panel
            self.slots = self.crafting_slots
        elif mode == 2:
            self.slots = self.furnace_slots
            self.current_panel = self.furnace_panel

    def change_image(self):
        image = G.texture_pack_list.selected_texture_pack.load_texture(['gui', 'inventory.png' if self.mode == 0 else 'crafting.png' if self.mode == 1 else 'furnace.png'])
        image_scale = image.height / 256
        x_size = 176 * image_scale
        y_size = 166 * image_scale
        self.frame = image_sprite(image, self.batch[self.mode], 0, y=image.height - y_size, height=y_size, x=0, width=x_size)
        self.frame.scale = (1.0 / image_scale) * 2
        self.frame.x = (self.parent.window.width - self.frame.width) / 2
        self.frame.y = 74

    def update_items(self):
        # only inventory has armor slots
        items = self.player.inventory.get_items()[:self.max_items] + self.player.quick_slots.get_items()[:self.player.quick_slots.slot_count] + \
                (self.player.armor.get_items()[:4] if self.mode == 0 else [])
        i = 0
        for item in items:
            self.slots[i].item = item
            i += 1

        # NOTE: each line in the crafting panel should be a sub-list in the crafting ingredient list
        crafting_ingredients = [[], [], []] if self.mode == 1 else [[], []]
        items = self.current_panel.get_items()[:self.current_panel.slot_count]
        for j, item in enumerate(items):
            self.slots[i].item = item
            if not item or item.get_object().id > 0:
                crafting_ingredients[int(floor(j / (2 if self.mode == 0 else 3 if self.mode == 1 else 1)))].append(air_block if not item else item.get_object())
            i += 1

        if len(crafting_ingredients) > 0:
            if self.mode < 2:
                outcome = G.recipes.craft(crafting_ingredients)
                self.set_crafting_outcome(outcome)
            elif self.mode == 2:
                outcome = self.furnace_panel.get_smelt_outcome()
                self.set_crafting_outcome(outcome)

        self.world.packetreceiver.send_player_inventory()  # Tell the server.

    def get_current_block_item_and_amount(self):
        item = self.player.inventory.at(self.current_index)
        if item:
            amount = item.amount
            self.player.inventory.remove_by_index(self.current_index, quantity=item.amount)
            return item, amount
        return False

    def toggle(self, reset_mode=True):
        if not self.visible:
            self.update_items()
        if reset_mode:
            self.mode = 0
        self.switch_mode(self.mode, reset_mode)
        self.parent.item_list.toggle()
        self.parent.window.set_exclusive_mouse(self.visible)
        self.visible = not self.visible

    def set_furnace(self, furnace):
        self.furnace_panel = furnace
        crafting_rows = 2
        rows = floor(self.max_items / 9)
        inventory_y = 0
        inventory_height = (rows * (self.icon_size + 8)) + ((rows+1) * 3)
        slot_x = self.frame.x + 63
        slot_y = self.frame.y + (inventory_y + inventory_height + 32) + ((crafting_rows * self.icon_size) + (crafting_rows * 3))

        for i in range(1, self.furnace_panel.slot_count + 1):
            slot = Slot(self, slot_x, slot_y, self.icon_size, self.icon_size, inventory=self.furnace_panel, index=i-1, is_quickslot=False, world=self.world, batch=self.batch[2], group=self.group[2], label_group=self.labels_group)
            self.furnace_slots.append(slot)
            slot_x += self.icon_size + 4
            if i == 0:
                slot_x = self.frame.x + 63
                slot_y -= self.icon_size + 4

        # install callback
        self.furnace_panel.set_outcome_callback(self.update_items)
        self.furnace_panel.set_fuel_callback(self.update_items)

    def reset_furnace(self):
        # remove callback
        if self.furnace_panel is None:
            return
        self.furnace_panel.set_outcome_callback(None)
        self.furnace_panel.set_fuel_callback(None)
        self.furnace_panel = None

    def set_crafting_outcome(self, item):
        self.crafting_outcome = item
        self.slots[-1].item = item

    def set_selected_item(self, item, x=0, y=0):
        if not item:
            self.remove_selected_item()
            return

        self.selected_item = item
        img = get_block_icon(item.get_object(), self.icon_size, self.world)
        self.selected_item_icon = image_sprite(img, self.batch[self.mode], self.group[self.mode])
        image_scale = 0.8 / (img.width / self.icon_size)
        self.selected_item_icon.scale = image_scale
        self.selected_item_icon.x = x - (self.selected_item_icon.width / 2)
        self.selected_item_icon.y = y - (self.selected_item_icon.height / 2)

    def remove_selected_item(self):
        self.selected_item = None
        self.selected_item_icon = None

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.visible:
            return pyglet.event.EVENT_HANDLED

    def on_mouse_press(self, x, y, button, modifiers):
        if not self.visible:
            return False
        if x < 0.0 or y < 0.0:
            return pyglet.event.EVENT_HANDLED
        inventory = None
        index = -1
        for slot in self.slots:
            if slot.hit_test(x, y):
                inventory = slot.inventory
                index = slot.index
                break

        if index == 256:    # 256 for crafting outcome
            if self.crafting_outcome:
                self.remove_selected_item()
                # set selected_item to the crafting outcome so that users can put it in inventory
                self.set_selected_item(self.crafting_outcome, x, y)
                # cost
                for ingre in self.current_panel.slots:
                    if ingre :
                        ingre.change_amount(-1)
                        # ingredient has been used up
                        if ingre.amount <= 0:
                            self.set_crafting_outcome(None)
                self.current_panel.remove_unnecessary_stacks()
                self.update_items()
            return pyglet.event.EVENT_HANDLED
        if self.selected_item:
            if index == -1:
                # throw it
                if not (self.frame.x <= x <= self.frame.x + self.frame.width and self.frame.y <= y <= self.frame.y + self.frame.height):
                    self.remove_selected_item()
                self.update_items()
                return pyglet.event.EVENT_HANDLED
            item = inventory.at(index)
            if (item and item.type == self.selected_item.type) or not item:
                amount_to_change = 1
                if button != pyglet.window.mouse.RIGHT:
                    amount_to_change = self.selected_item.amount
                if item:
                    remaining = item.change_amount(amount_to_change)
                else:
                    if hasattr(inventory, 'set_slot'):
                        inventory.set_slot(index, ItemStack(type=self.selected_item.type, durability=self.selected_item.durability, amount=amount_to_change))
                    else:
                        inventory.slots[index] = ItemStack(type=self.selected_item.type, durability=self.selected_item.durability, amount=amount_to_change)
                    remaining = self.selected_item.amount - amount_to_change
                if remaining > 0:
                    self.selected_item.change_amount((self.selected_item.amount - remaining) * -1)
                else:
                    self.set_selected_item(None)
                self.update_items()
                return pyglet.event.EVENT_HANDLED
            if hasattr(inventory, 'set_slot'):
                inventory.set_slot(index, self.selected_item)
            else:
                inventory.slots[index] = self.selected_item
            self.set_selected_item(item, x, y)
        else:
            if index == -1:
                return pyglet.event.EVENT_HANDLED
            item = inventory.at(index)
            if not item:
                return pyglet.event.EVENT_HANDLED

            if modifiers & pyglet.window.key.MOD_SHIFT:
                add_to = self.player.quick_slots if inventory == self.player.inventory else self.player.inventory
                add_to.add_item(item.type, item.amount, durability=item.durability)
                inventory.remove_all_by_index(index)
                self.update_items()
                return pyglet.event.EVENT_HANDLED

            new_stack = False
            if button == pyglet.window.mouse.RIGHT:
                if item.amount > 1:
                    split_amount = int(ceil(item.amount / 2))
                    item.change_amount(split_amount * -1)
                    new_item = ItemStack(item.type, split_amount, item.durability)
                    self.set_selected_item(new_item, x, y)
                    new_stack = True

            if not new_stack:
                self.set_selected_item(item, x, y)
                inventory.remove_all_by_index(index)

        self.update_items()
        return pyglet.event.EVENT_HANDLED

    def on_mouse_motion(self, x, y, dx, dy):
        if self.visible:
            for slot in self.slots:
                slot.highlighted = slot.hit_test(x, y)

            if self.selected_item_icon:
                self.selected_item_icon.x = x - (self.selected_item_icon.width / 2)
                self.selected_item_icon.y = y - (self.selected_item_icon.height / 2)
            return pyglet.event.EVENT_HANDLED

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        if self.visible:
            if button == pyglet.window.mouse.LEFT:
                self.on_mouse_motion(x, y, dx, dy)
            return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        if self.visible:
            if symbol == G.ESCAPE_KEY:
                self.toggle()
                return pyglet.event.EVENT_HANDLED
            elif symbol == G.VALIDATE_KEY:
                return pyglet.event.EVENT_HANDLED

    def on_resize(self, width, height):
        self.frame.x = (width - self.frame.width) / 2
        self.frame.y = 74
        if self.visible:
            self.update_items()

    def _on_draw(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.batch[self.mode].draw()
        self.batch[3].draw()
        if self.selected_item_icon:
            self.selected_item_icon.draw()
        glDisable(GL_BLEND)


# TODO: This is a total hack. The issue seen here: https://code.google.com/p/pyglet/issues/detail?id=471
# Makes it impossible to set styles to a FormattedDocument (font family, font size, color, etc) because if the document
# text ever becomes empty, exceptions are thrown. There is a fix below from 2012 but it apparently does not exist
# in 1.1.4? So I apply it by rewriting the RunIterator.__getitem__ method.
# https://code.google.com/p/pyglet/source/diff?spec=svn64e3a450c83bd2245f047bb96fdacd79208d8b6a&r=64e3a450c83bd2245f047bb96fdacd79208d8b6a&format=side&path=/pyglet/text/runlist.py
def __run_iterator_fix(self, index):
    while index >= self.end and index > self.start:
        # condition has special case for 0-length run (fixes issue 471)
        self.start, self.end, self.value = self.next()
    return self.value
from pyglet.text.runlist import RunIterator
RunIterator.__getitem__ = __run_iterator_fix


class TextWidget(Control):
    """
    Variation of this example: http://www.pyglet.org/doc/programming_guide/text_input.py
    """
    def __init__(self, parent, text, x, y, width, height=None, multi_line=False,
                 font_size=12,
                 font_name=G.DEFAULT_FONT,
                 text_color=(0, 0, 0, 255),
                 background_color=(200, 200, 200, 128),
                 readonly=False,
                 batch = None,
                 enable_escape = False,
                 *args, **kwargs):
        super(TextWidget, self).__init__(parent, *args, **kwargs)
        self.batch = pyglet.graphics.Batch() if not batch else batch
        self.vertex_list = None
        blank_text = not bool(text)
        self.document = pyglet.text.document.FormattedDocument(text if not blank_text else ' ')
        self.default_style = dict(color=text_color,
                                     font_size=font_size,
                                     font_name=font_name)

        # parse escape sequences
        self.enable_escape = enable_escape
        self.document.set_style(0, len(self.document.text), self.default_style)
        font = self.document.get_font(0)
        if blank_text:
            self.clear()
        self.padding = 10
        self.height = height or (font.ascent - font.descent) + self.padding
        self.x, self.y, self.width = x, y, width
        self.multi_line = multi_line
        self.background_color = background_color

        self.layout = pyglet.text.layout.IncrementalTextLayout(
            self.document, self.width, self.height, multiline=self.multi_line, batch=self.batch)
        self.caret = pyglet.text.caret.Caret(self.layout)
        self.caret.visible = not readonly
        self.readonly = readonly

        self.layout.x = x
        self.layout.y = y
        self.resize()

    def focus(self):
        super(TextWidget, self).focus()
        self.caret.visible = True
        self.caret.mark = 0
        self.caret.position = len(self.document.text)

    def hit_test(self, x, y):
        return (0 < x - self.layout.x < self.layout.width and
                0 < y - self.layout.y < self.layout.height)

    @property
    def text(self):
        return self.document.text

    @text.setter
    def text(self, text):
        self.document.text = text

    def clear(self):
        self.text = ''

    def write(self, text, **kwargs):
        """
        Write the text to the widget.
        """
        start = len(self.text)
        end = start + len(text)
        self.document.insert_text(start, text)
        self.document.set_style(start, end, kwargs)
        if self.multi_line:
            self.layout.view_y = -self.layout.content_height # Scroll to the bottom

    def write_escape(self, text):
        # parse escape sequences
        # a escape sequence is a sub-sequence in the text which starts with '$$'
        # currently available escape sequences:
        # $$r: set text color to red
        # $$g: set text color to green
        # $$b: set text color to blue
        # $$y: set text color to yellow
        # $$m: set text color to magenta
        # $$c: set text color to cyan
        # $$D: set text style to default
        style = self.default_style.copy()
        cooked_text = ''
        escape = 0
        for c in text:
            # command
            if escape == 1:
                if c == 'r':
                    style['color'] = [255, 0, 0, 255]
                if c == 'g':
                    style['color'] = [0, 255, 0, 255]
                if c == 'b':
                    style['color'] = [0, 0, 255, 255]
                if c == 'y':
                    style['color'] = [255, 255, 0, 255]
                if c == 'm':
                    style['color'] = [255, 0, 255, 255]
                if c == 'c':
                    style['color'] = [0, 255, 255, 255]
                if c == 'D':
                    style = self.default_style.copy()
                escape = 0 # end sequence
                continue

            if c == '$':
                # first '$' char
                if escape == 0:
                    escape = -1
                    continue
                # second '$' char
                if escape == -1:
                    # output the text
                    self.write(cooked_text, **style)
                    cooked_text = ''
                    escape = 1

            else:
                cooked_text += c

        if cooked_text != '':
            self.write(cooked_text, **style)

    def write_line(self, text, **kwargs):
        """
        Write the text followed by a newline. Only effective if multi_line is True.
        """
        if self.enable_escape:
            self.write_escape("%s\n" % text)
        else:
            self.write("%s\n" % text, **kwargs)

    def resize(self, x=None, y=None, width=None, height=None):
        self.x = x or self.x
        self.y = y or self.y
        self.width = width or self.width
        self.height = height or self.height
        # Recreate the bounding box
        self.rectangle = Rectangle(self.x - self.padding, self.y - self.padding,
                                   self.width + self.padding, self.height + self.padding)
        # And reposition the text layout
        self.layout.x = self.x + self.padding
        self.layout.y = (self.rectangle.y + (self.rectangle.height/2) - (self.height/2))
        self.layout.width = self.rectangle.width - self.padding
        self.layout.height = self.rectangle.height - self.padding
        if self.vertex_list:
            self.vertex_list.delete()
        self.vertex_list = self.batch.add(4, pyglet.gl.GL_QUADS, None,
                                          ('v2i', self.rectangle.vertex_list()),
                                          ('c4B', self.background_color * 4)
        )

    def _on_draw(self):
        self.batch.draw()

    def _on_toggled(self):
        self.parent.set_exclusive_mouse(not self.visible)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.visible:
            self.caret.on_mouse_drag(x, y, dx, dy, buttons, modifiers)
            return pyglet.event.EVENT_HANDLED

    def on_text(self, text):
        if self.visible:
            if not self.multi_line:
                text = text.replace('\r', '')  # Remove carriage returns
            self.caret.on_text(text)
            return pyglet.event.EVENT_HANDLED

    def on_text_motion(self, motion):
        if self.visible:
            self.caret.on_text_motion(motion)
            return pyglet.event.EVENT_HANDLED

    def on_text_motion_select(self, motion):
        if self.visible:
            self.caret.on_text_motion_select(motion)
            return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifier):
        if self.visible:
            return pyglet.event.EVENT_HANDLED

    def on_key_release(self, symbol, modifier):
        if self.visible and not self.readonly:
            if symbol == G.ESCAPE_KEY:
                self.toggle()
                self.parent.pop_handlers()
            dispatched = self.dispatch_event('key_released', symbol, modifier)
            if dispatched is not None:
                return dispatched
            return pyglet.event.EVENT_HANDLED

    def on_mouse_release(self, x, y, button, modifiers):
        if self.visible:
            return pyglet.event.EVENT_HANDLED

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.visible and self.focused and self.multi_line:
            self.layout.view_y += scroll_y * 15
            return pyglet.event.EVENT_HANDLED


class ProgressBarWidget(Control):
    def __init__(self, parent, background_pic, foreground_pic,
                x, y, width, height, progress_updater = None, progress = 0, text_color = (0, 0, 0, 255), 
                *args, **kwargs):
        super(ProgressBarWidget, self).__init__(parent, *args, **kwargs)
        self.batch = pyglet.graphics.Batch()
        self.group = pyglet.graphics.OrderedGroup(1)
        self.background_pic = image_sprite(background_pic, self.batch, self.group)
        self.foreground_pic = foreground_pic
        self.progress_pic = None
        self.progress_pic.x = x
        self.progress_pic.y = y
        self.text_color = text_color
        self.x = x
        self.y = y
        self.height = height
        self.width = width
        self.progress_updater = progress_updater
        self.progress = progress

    def set_progress(self, progress):
        self.progress = progress
        self.update_progress()

    def update_progress(self):
        if self.progress_updater is not None:
            self.progress = self.progress_updater()

        self.progress_pic = image_sprite(self.foreground_pic, self.batch, self.group, x=0, y=0,
                width=floor(self.width * self.progress), height=self.height)

    def _on_draw(self):
        self.update_progress()
        self.batch.draw()


class ScrollbarWidget(Control):
    # style: 0 - vertical, 1 - horizontal
    def __init__(self, parent, x, y, width, height,
                 sb_width, sb_height,
                 style=0, 
                 background_image=None,
                 scrollbar_image=None, 
                 caption=None, font_size=12, font_name=G.DEFAULT_FONT,
                 batch=None, group=None, label_group=None,
                 pos=0, on_pos_change=None,
                 *args, **kwargs):
        super(ScrollbarWidget, self).__init__(parent, *args, **kwargs)
        parent.push_handlers(self)
        self.batch = pyglet.graphics.Batch() if not batch else batch
        self.group = group
        self.label_group = label_group
        self.x, self.y, self.width, self.height = x, y, width, height
        self.sb_width, self.sb_height = sb_width, sb_height

        self.style = style
        if self.style == 0:
            self.sb_width = self.width
        else:
            self.sb_height = self.height

        self.background = image_sprite(background_image, self.batch, self.group)
        self.background.scale = max(float(self.width) / float(background_image.width), float(self.height) / float(background_image.height))
        self.scrollbar = image_sprite(scrollbar_image, self.batch, self.group)
        self.scrollbar.scale = max(float(self.sb_width) / float(scrollbar_image.width), float(self.sb_height) / float(scrollbar_image.height))

        self.pos = pos
        self.on_pos_change = on_pos_change
        self.caption = caption
        self.label = Label(str(caption) + ":" + str(pos) + "%", font_name, 12, anchor_x='center', anchor_y='center',
            color=(255, 255, 255, 255), batch=self.batch, group=self.label_group) if caption else None
        
        self.move_to(x, y)

    @property
    def position(self):
        return self.x, self.y

    @position.setter
    def position(self, value):
        self.move_to(*value)

    def move_to(self, x, y):
        self.x, self.y = x, y

        if hasattr(self, 'background') and self.background:
            self.background.x, self.background.y = x, y
            #self.background.scale = max(float(self.width) / float(self.background.width), float(self.height) / float(self.background.height))
        if hasattr(self, 'scrollbar') and self.scrollbar:
            self.scrollbar.x, self.scrollbar.y = x, y
            #self.scrollbar.scale = max(float(self.sb_width) / float(self.scrollbar.width), float(self.sb_height) / float(self.scrollbar.height))
        if hasattr(self, 'label') and self.label:
            self.label.x, self.label.y = self.center

        # Recreate the bounding box
        self.rectangle = Rectangle(self.x, self.y, self.width, self.height)

        self.update_pos(self.pos)

    @property
    def center(self):
        return self.x + self.width / 2, self.y + self.height / 2

    def _on_draw(self):
        self.background.draw()
        self.scrollbar.draw()
        if self.label is not None:
            self.label.draw()

    def update_pos(self, new_pos):
        sb_space = self.width - self.sb_width if self.style == 1 else self.height - self.sb_height
        offset = sb_space * new_pos / 100

        # vertical
        if self.style == 0:
            self.scrollbar.y = self.y + self.height
            self.scrollbar.y -= offset
        elif self.style == 1:     # horizontal
            self.scrollbar.x = self.x + offset

        if self.label is not None:
            self.label.text = self.caption + ':' + str(new_pos) + '%'

        if self.on_pos_change is not None:
            self.on_pos_change(new_pos)

        self.pos = new_pos

    def coord_to_pos(self, x, y):
        offset = (self.y + self.height - y) if self.style == 0 else (x - self.x)
        return int(offset * 100 / (self.height if self.style == 0 else self.width))

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.visible:
            x += dx
            y += dy
            if self.rectangle.hit_test(x, y):
                self.update_pos(self.coord_to_pos(x, y))
            return pyglet.event.EVENT_HANDLED

    def on_mouse_release(self, x, y, button, modifiers):
        if self.visible:
            if self.rectangle.hit_test(x, y):
                self.update_pos(self.coord_to_pos(x, y))
            return pyglet.event.EVENT_HANDLED


frame_image = load_image('resources', 'textures', 'frame.png')

def init_button_image():
    gui_image = G.texture_pack_list.selected_texture_pack.load_texture(['gui', 'gui.png'])
    image_scale = gui_image.height / 256
    x_size = 200 * image_scale
    y_offset = 66 * image_scale
    y_size = 20 * image_scale
    batch = pyglet.graphics.Batch()
    button_disabled = image_sprite(gui_image, batch, 0, y=gui_image.height - y_offset, height=y_size, x=0, width=x_size)

    y_offset += y_size
    button = image_sprite(gui_image, batch, 0, y=gui_image.height - y_offset, height=y_size, x=0, width=x_size)

    y_offset += y_size
    highlighted_button = image_sprite(gui_image, batch, 0, y=gui_image.height - y_offset, height=y_size, x=0, width=x_size)
    
    button.scale = 1.0
    highlighted_button.scale = 1.0
    button_disabled.scale = 1.0
    button.scale = 1.0 / float(image_scale)
    highlighted_button.scale = 1.0 / float(image_scale)
    button_disabled.scale = 1.0 / float(image_scale)
    button = button.image
    highlighted_button = highlighted_button.image
    button_disabled = button_disabled.image
    return button, highlighted_button, button_disabled

def resize_button_image(image, old_width, new_width):
    if new_width == old_width:
        return image
    new_width = int(image.width * new_width / old_width)
    atlas = TextureAtlas(new_width, image.height)
    atlas.add(image.get_region(0, 0, new_width // 2, image.height).image_data)
    atlas.add(image.get_region(image.width - new_width // 2, 0, new_width // 2, image.height).image_data)
    return atlas.texture.image_data

button_image, button_highlighted, button_disabled = init_button_image()
background_image = load_image('resources', 'textures', 'main_menu_background.png')
backdrop_images = []
rnd_backdrops = ('main_menu_background.png', 'main_menu_background_2.png', 'main_menu_background_3.png',
'main_menu_background_4.png', 'main_menu_background_5.png', 'main_menu_background_6.png')

for backdrop in rnd_backdrops:
    backdrop_images.append(load_image('resources', 'textures', backdrop))
    
backdrop = random.choice(backdrop_images)
