import cython

#cython: boundscheck=False
#cython: wraparound=False
#cython: cdivision=True

@cython.locals(spreading_mutations=dict)
cdef class WorldServer(dict):
    cdef public:
        sectors
        savingsystem
        dict exposed_cache

        urgent_queue
        lazy_queue
        sector_queue
        generation_queue
        spreading_mutable_blocks

        server_lock
        server

        terraingen

    cpdef object add_block(self, tuple position, object block,
                           bint sync=?, bint force=?, bint check_spread=?)

    cpdef object init_block(self, tuple position, object block)

    cpdef object remove_block(self, tuple position,
                              bint sync=?, bint check_spread=?)

    @cython.locals(x=int, y=int, z=int, fx=int, fy=int, fz=int,
    					other_position=tuple)
    cpdef bint is_exposed(self, tuple position)

    @cython.locals(x=int, y=int, z=int, cx=int, cy=int, cz=int)
    cpdef object get_exposed_sector_cached(self, tuple sector)

    cpdef object get_exposed_sector(self, tuple sector)

    @cython.locals(other_position=tuple)
    cpdef object check_neighbors(self, tuple position)

    @cython.locals(x=int, y=int, z=int, above_position=tuple)
    cpdef object check_spreading_mutable(self, tuple position, object block)

    cpdef bint has_neighbors(self, tuple position, object is_in=?, object diagonals=?,
                      object faces=?)

    cpdef object generate_seed(self)

    cpdef object open_sector(self, tuple sector)

    cpdef object hide_sector(self, tuple sector)

    cpdef object content_update(self)

    cpdef object generate_vegetation(self, tuple position, vegetation_class)