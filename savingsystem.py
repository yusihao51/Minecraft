# Imports, sorted alphabetically.

# Python packages
import cPickle as pickle
import os
import random
import struct
import time
import sqlite3

# Third-party packages
# Nothing for now...

# Modules from this project
from blocks import BlockID
from debug import performance_info
import globals as G
from player import Player


__all__ = (
    'sector_to_filename', 'region_to_filename', 'sector_to_region',
    'sector_to_offset', 'save_world', 'world_exists', 'remove_world',
    'sector_exists', 'load_region', 'open_world',
)


structvec = struct.Struct("hhh")
structushort = struct.Struct("H")
structuchar2 = struct.Struct("BB")
structvecBB = struct.Struct("hhhBB")

null2 = struct.pack("xx") #Two \0's
null1024 = null2*512      #1024 \0's
air = G.BLOCKS_DIR[(0,0)]

def sector_to_filename(secpos):
    x,y,z = secpos
    return "%i.%i.%i.pyr" % (x/4, y/4, z/4)
def region_to_filename(region):
    return "%i.%i.%i.pyr" % region
def sector_to_region(secpos):
    x,y,z = secpos
    return (x/4, y/4, z/4)
def sector_to_offset(secpos):
    x,y,z = secpos
    return ((x % 4)*16 + (y % 4)*4 + (z % 4)) * 1024
def sector_to_blockpos(secpos):
    x,y,z = secpos
    return x*8, y*8, z*8

def connect_db(world=None):
    if world is None: world = 'world'
    world_dir = os.path.join(G.worlds_dir, world)
    if not os.path.exists(world_dir):
        os.makedirs(world_dir)
    if not os.path.exists(os.path.join(world_dir, G.DB_NAME)):
        db = sqlite3.connect(os.path.join(world_dir, G.DB_NAME))
        db.execute('create table players (id integer primary key autoincrement, version integer, ' + \
            'pos_x real, pos_y real, pos_z real, mom_x real, mom_y real, mom_z real, ' + \
            'inventory varchar(160), name varchar(30) UNIQUE)');
        db.commit()
        return db
    return sqlite3.connect(os.path.join(world_dir, G.DB_NAME)) 

def save_sector_to_string(blocks, secpos):
    cx, cy, cz = sector_to_blockpos(secpos)
    fstr = ""
    for x in xrange(cx, cx+8):
        for y in xrange(cy, cy+8):
            for z in xrange(cz, cz+8):
                blk = blocks.get((x,y,z), air).id
                if blk is not air:
                    #if isinstance(blk, int): # When does this occur? Its expensive and I don't see it triggering
                    #    blk = BlockID(blk)
                    fstr += structuchar2.pack(blk.main, blk.sub)
                else:
                    fstr += null2
    return fstr

def save_world(server, world):
    #Non block related data
    #save = (4,window.player, window.time_of_day, G.SEED)
    #pickle.dump(save, open(os.path.join(game_dir, world, "save.pkl"), "wb"))
    for player in server.players:
        save_player(player, world)

    save_blocks(server.world, world)

def save_blocks(blocks, world):
    #blocks and sectors (window.world and window.world.sectors)
    #Saves individual sectors in region files (4x4x4 sectors)

    for secpos in blocks.sectors: #TODO: only save dirty sectors
        if not blocks.sectors[secpos]:
            continue #Skip writing empty sectors
        file = os.path.join(G.game_dir, world, sector_to_filename(secpos))
        if not os.path.exists(file):
            with open(file, "w") as f:
                f.truncate(64*1024) #Preallocate the file to be 64kb
        with open(file, "rb+") as f: #Load up the region file
            f.seek(sector_to_offset(secpos)) #Seek to the sector offset
            f.write(save_sector_to_string(blocks, secpos))

def save_player(player, world):
    db = connect_db(world)
    cur = db.cursor()
    cur.execute('insert or replace into players(version, pos_x, pos_y, pos_z, mom_x, mom_y, mom_z, inventory, name) ' + \
        "values (?, ?, ?, ?, ?, ?, ?, ?, ?)", (1, 
            player.position[0], player.position[1], player.position[2],
            player.momentum[0], player.momentum[1], player.momentum[2], 
            player.inventory, player.username))
    db.commit()
    cur.close()
    db.close()


def world_exists(game_dir, world=None):
    if world is None: world = "world"
    return os.path.lexists(os.path.join(G.worlds_dir, world))


def remove_world(game_dir, world=None):
    if world is None: world = "world"
    if world_exists(game_dir, world):
        import shutil
        shutil.rmtree(os.path.join(game_dir, world))

def sector_exists(sector, world=None):
    if world is None: world = "world"
    return os.path.lexists(os.path.join(G.game_dir, world, sector_to_filename(sector)))

def load_region(world, world_name=None, region=None, sector=None):
    if world_name is None: world_name = "world"
    sectors = world.sectors
    blocks = world
    SECTOR_SIZE = G.SECTOR_SIZE
    BLOCKS_DIR = G.BLOCKS_DIR
    if sector: region = sector_to_region(sector)
    rx,ry,rz = region
    rx,ry,rz = rx*32, ry*32, rz*32
    with open(os.path.join(G.game_dir, world_name, region_to_filename(region)), "rb") as f:
        #Load every chunk in this region (4x4x4)
        for cx in xrange(rx, rx+32, 8):
            for cy in xrange(ry, ry+32, 8):
                for cz in xrange(rz, rz+32, 8):
                    #Now load every block in this chunk (8x8x8)
                    fstr = f.read(1024)
                    if fstr != null1024:
                        fpos = 0
                        for x in xrange(cx, cx+8):
                            for y in xrange(cy, cy+8):
                                for z in xrange(cz, cz+8):
                                    read = fstr[fpos:fpos+2]
                                    fpos += 2
                                    if read != null2:
                                        position = x,y,z
                                        try: 
                                            full_id = structuchar2.unpack(read)
                                            blocks[position] = BLOCKS_DIR[full_id]
                                            if blocks[position].sub_id_as_metadata:
                                                blocks[position] = type(BLOCKS_DIR[full_id])()
                                                blocks[position].set_metadata(full_id[-1])
                                        except KeyError:
                                            try:
                                                main_blk = BLOCKS_DIR[(full_id[0], 0)]
                                                if main_blk.sub_id_as_metadata: # sub id is metadata
                                                    blocks[position] = type(main_blk)()
                                                    blocks[position].set_metadata(full_id[-1])
                                            except KeyError as e:
                                                print "load_region: Invalid Block", e
                                        sectors[(x/SECTOR_SIZE, y/SECTOR_SIZE, z/SECTOR_SIZE)].append(position)

def load_player(player, world):
    db = connect_db(world)
    cur = db.cursor()
    cur.execute("select * from players where name='%s'" % player.username)
    data = cur.fetchone()
    if data is None:    # no such entry, set initial value
        player.position = None
        player.momentum = (0, 0, 0)
        player.inventory = ''.join((struct.pack("HBB", 0, 0, 0)) * 40)
    else:
        player.position = list(data[i] for i in range(2, 5))
        player.momentum = list(data[i] for i in range(5, 8))
        player.inventory = str(data[8])
    cur.close()
    db.close()

@performance_info
def open_world(gamecontroller, game_dir, world=None):
    if world is None: world = "world"

    #Non block related data
    loaded_save = pickle.load(open(os.path.join(game_dir, world, "save.pkl"), "rb"))
    if loaded_save[0] == 4:
        if isinstance(loaded_save[1], Player): gamecontroller.player = loaded_save[1]
        if isinstance(loaded_save[2], float): gamecontroller.time_of_day = loaded_save[2]
        if isinstance(loaded_save[3], str):
            G.SEED = loaded_save[3]
            random.seed(G.SEED)
            print('Loaded seed from save: ' + G.SEED)
    elif loaded_save[0] == 3: #Version 3
        if isinstance(loaded_save[1], Player): gamecontroller.player = loaded_save[1]
        if isinstance(loaded_save[2], float): gamecontroller.time_of_day = loaded_save[2]
        G.SEED = str(long(time.time() * 256))
        random.seed(G.SEED)
        print('No seed in save, generated random seed: ' + G.SEED)

    #blocks and sectors (window.world and window.world.sectors)
    #Are loaded on the fly
