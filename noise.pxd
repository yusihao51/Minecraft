import cython
cimport perlin

#cython: boundscheck=False
#cython: wraparound=False
#cython: cdivision=True

cdef class SimplexNoiseGen(object):
    cdef public:
        list perm
        object noise
        double PERSISTENCE, H
        int OCTAVES
        list weights
        double zoom_level

    @cython.locals(y=double, weight=double)
    cpdef double fBm(self, double x, double z)

cdef class PerlinNoise(object):
    cdef public:
        list perm, weights
        double PERSISTENCE, H
        int OCTAVES
        bint regen_weight

    cdef double fade(self, double t)

    cdef double lerp(self, double t, double a, double b)

    @cython.locals(h=int, u=double, v=double)
    cdef double grad(self, int hash, double x, double y, double z)

    @cython.locals(X=int, Y=int, Z=int, u=double, v=double, w=double,
                   A=int, AA=int, AB=int, B=int, BA=int, BB=int)
    cdef double noise(self, double x, double y, double z)

    @cython.locals(total=double, n=int)
    cpdef double fBm(self, double x, double y, double z)
