import cython
cimport perlin

#cython: boundscheck=False
#cython: wraparound=False
#cython: cdivision=True

cdef class BiomeGenerator(object):
    cdef public:
        object temperature_gen, humidity_gen

    cpdef double _clamp(self, double a)

    cpdef double get_humidity(self, double x, double z)

    cpdef double get_temperature(self, double x, double z)

    @cython.locals(temp=double, humidity=double)
    cpdef int get_biome_type(self, double x, double z)
