# Imports, sorted alphabetically.

# Python packages
# Nothing for now...

# Third-party packages
import pyglet.media

# Modules from this project
import globals as G


__all__ = (
    'wood_break', 'water_break', 'leaves_break', 'glass_break', 'dirt_break',
    'gravel_break', 'stone_break', 'melon_break', 'sand_break', 'play_sound',
)

pyglet.options['audio'] = ('openal', 'directsound', 'alsa', 'silent')

# Note: Pyglet uses /'s regardless of OS
pyglet.resource.path = [".", "resources/sounds"]
pyglet.resource.reindex()

wood_break = pyglet.resource.media("wood_break.wav", streaming=False)
water_break = pyglet.resource.media("water_break.wav", streaming=False)
leaves_break = pyglet.resource.media("leaves_break.wav", streaming=False)
glass_break = pyglet.resource.media("glass_break.wav", streaming=False)
dirt_break = pyglet.resource.media("dirt_break.wav", streaming=False)
gravel_break = pyglet.resource.media("gravel_break.wav", streaming=False)
stone_break = pyglet.resource.media("stone_break.wav", streaming=False)
melon_break = pyglet.resource.media("melon_break.wav", streaming=False)
sand_break = pyglet.resource.media("sand_break.wav", streaming=False)


def play_sound(sound, player=None, position=None): 
    sound_player = pyglet.media.ManagedSoundPlayer()

    #Makes sure we don't set properties for objects that aren't instantiated
    try:
        #Try and load the silent driver
        driver = pyglet.media.drivers.silent.SilentAudioDriver
    except:
        try:
            #If the silent driver cannot be loaded, then sound is available
            pyglet.media.listener.volume = G.EFFECT_VOLUME
            pyglet.media.listener.forward_orientation = player.get_sight_vector()
            if position:
                sound_player.position = position
            if sound_player:
                pyglet.media.listener.position = player.position
            sound_player.queue(sound)
            sound_player.play()
        except:
            return sound_player

    return sound_player
