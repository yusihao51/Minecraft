# Imports, sorted alphabetically.

# Third-party packages
from noise import SimplexNoiseGen

# Modules from this project
import globals as G

__all__ = ("BiomeGenerator")

class BiomeGenerator(object):
    def __init__(self, seed):
         self.temperature_gen = SimplexNoiseGen(seed + "97", zoom_level=0.01)
         self.humidity_gen = SimplexNoiseGen(seed + "147", zoom_level=0.01)
        #temp_seed = int(G.SEED)
        #temp_gen = temp_seed + 97
        #temp_humid = temp_seed + 147
        #self.temperature_gen = SimplexNoiseGen(temp_gen, zoom_level=0.01)
        #self.humidity_gen = SimplexNoiseGen(temp_humid, zoom_level=0.01)

    def _clamp(self, a):
        if a > 1:
            return 1.0
        elif a < 0:
            return 0.0
        else:
            return a

    def get_humidity(self, x, z):
        return self._clamp((self.humidity_gen.fBm(x, z) + 1.0) / 2.0)

    def get_temperature(self,x, z):
        return self._clamp((self.temperature_gen.fBm(x, z) + 1.0) / 2.0)

    def get_biome_type(self, x, z):
        temp = self.get_temperature(x, z)
        humidity = self.get_humidity(x, z) * temp

        if temp >= 0.5:
            if humidity < 0.3:
                return G.DESERT
            elif humidity <= 0.6:
                return G.PLAINS
        else:
            if temp <= 0.3 and humidity > 0.5:
                return G.SNOW
            elif 0.2 <= humidity <= 0.6:
                return G.MOUNTAINS
        return G.FOREST
