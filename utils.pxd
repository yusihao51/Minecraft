import cython

#cython: boundscheck=False
#cython: wraparound=False
#cython: cdivision=True


cdef class FastRandom(object):
    cdef public seed

    cpdef int randint(self)


@cython.locals(int_f=int)
cpdef int normalize_float(float f)


@cython.locals(x=float, y=float, z=float)
cpdef tuple normalize(tuple position)


@cython.locals(x=int, y=int, z=int)
cpdef tuple sectorize(tuple position)
