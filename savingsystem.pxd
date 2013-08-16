import cython

@cython.locals(x=int, y=int, z=int)
cpdef str sector_to_filename(tuple secpos)

cpdef str region_to_filename(tuple region)

@cython.locals(x=int, y=int, z=int)
cpdef tuple sector_to_region(tuple secpos)

@cython.locals(x=int, y=int, z=int)
cpdef int sector_to_offset(tuple secpos)

@cython.locals(x=int, y=int, z=int)
cpdef tuple sector_to_blockpos(tuple secpos)

@cython.locals(cx=int, cy=int, cz=int, fstr=str, x=int, y=int, z=int, blk=object)
cpdef str save_sector_to_string(object blocks, tuple secpos)

cpdef object save_world(object server, str world)

@cython.locals(secpos=tuple, f=object)
cpdef object save_blocks(object blocks, str world)

cpdef object save_player(object player, str world)

cpdef bint world_exists(str game_dir, world=?)

cpdef object remove_world(str game_dir, world=?)

cpdef bint sector_exists(tuple sector, world=?)

@cython.locals(rx=int, ry=int, rz=int, cx=int, cy=int, cz=int, x=int, y=int, z=int, fstr=str,
				fpos=int, read=str, position=tuple)
cpdef object load_region(object world, world_name=?, region=?, sector=?)

@cython.locals(version=int)
cpdef object load_player(object player, str world)

cpdef object open_world(object gamecontroller, str game_dir, world=?)
