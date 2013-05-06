from msvcrt import getch
import os
from terrain import BiomeGenerator
import globals as G

with open(os.path.join(G.game_dir, "world", "seed"), "rb") as f:
    SEED = f.read()

b = BiomeGenerator(SEED)
curx = 0
cury = 0

xsize = 79
ysize = 28

DESERT, PLAINS, MOUNTAINS, SNOW, FOREST = range(5)
letters = ["D","P","M","S","F"]

print "Okay, click on the console window again, then use the arrow keys."

while True:
    base = getch()
    if base == '\xe0':
        key = getch()
        if key == 'H':   #Up Arrow
            cury -= 5
        elif key == 'M': #Right Arrow
            curx += 5
        elif key == 'P': #Down Arrow
            cury += 5
        elif key == 'K': #Left Arrow
            curx -= 5
        elif key == 'S': #Del
            exit()
        else: continue
        string = ""
        for y in range(cury,cury+ysize):
            for x in range(curx,curx+xsize):
                string += letters[b.get_biome_type(x,y)]
            string += "\n"
        print string + "Current position: (%s-%s %s-%s)" % (curx*8, (curx+xsize)*8, cury*8, (cury+ysize)*8)
