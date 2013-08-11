import cython
cimport client
#cython: boundscheck=False
#cython: wraparound=False
#cython: cdivision=True


@cython.locals(spreading_mutations=dict)
cdef class World(dict):
    cdef public:
        batch
        transparency_batch
        group
        savingsystem
        dict shown
        dict _shown
        sectors
        urgent_queue, lazy_queue
        sector_queue
        generation_queue
        terraingen
        set before_set
        spreading_mutable_blocks
        double spreading_time
        object packetreceiver
        object sector_packets
        object biome_generator

    cpdef object add_block(self, tuple position, object block,
                           bint sync=?, bint force=?)

    cpdef object _add_block(self, tuple position, object block)

    cpdef object remove_block(self, object player, tuple position,
                              bint sync=?, bint sound=?)

    @cython.locals(sector_position=tuple)
    cpdef object _remove_block(self, tuple position, bint sync=?)

    # Generators are not handled by Cython for the moment.
    # @cython.locals(x=float, y=float, z=float,
    #                dx=float, dy=float, dz=float)
    # cpdef object neighbors_iterator(self, tuple position,
    #                                 tuple relative_neighbors_positions=?)

    @cython.locals(other_position=tuple, faces=tuple)
    cpdef object check_neighbors(self, tuple position)

    @cython.locals(other_position=tuple)
    cpdef bint has_neighbors(self, tuple position,
                             set is_in=?,bint diagonals=?, tuple faces=?)

    @cython.locals(other_position=tuple, x=double, y=double, z=double, fx=int, fy=int, fz=int)
    cpdef bint is_exposed(self, tuple position)

    @cython.locals(m=int, _=int,
                   x=float, y=float, z=float,
                   dx=float, dy=float, dz=float,
                   previous=tuple, key=tuple)
    cpdef tuple hit_test(self, tuple position, tuple vector,
                         int max_distance=?, bint hitwater=?)

    cpdef object hide_block(self, tuple position, bint immediate=?)

    cpdef object _hide_block(self, tuple position)

    @cython.locals(block=object)
    cpdef object show_block(self, tuple position, bint immediate=?)

    @cython.locals(vertex_data=list, texture_data=list,
                   count=int, batch=object)
    cpdef object _show_block(self, tuple position, object block)

    @cython.locals(position=tuple)
    cpdef object _show_sector(self, tuple sector)

    @cython.locals(position=tuple)
    cpdef object _hide_sector(self, tuple sector)

    cpdef object enqueue_sector(self, bint state, tuple sector)

    @cython.locals(state=bint, sector=tuple)
    cpdef object dequeue_sector(self)

    @cython.locals(before_set=set, after_set=set, pad=int,
                   dx=int, dy=int, dz=int,
                   x=int, y=int, z=int,
                   show=set, hide=set, sector=tuple)
    cpdef object change_sectors(self, tuple after)

    @cython.locals(queue=object)
    cpdef object dequeue(self)

    @cython.locals(stoptime=double)
    cpdef object process_queue(self, double dt)

    cpdef object process_entire_queue(self)

    @cython.locals(deload=int, plysector=tuple, px=double, py=double, pz=double, x=int, y=int, z=int)
    cpdef object hide_sectors(self, double dt, object player)