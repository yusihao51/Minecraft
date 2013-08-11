import cython

cdef extern from "math.h":  
    float cosf(float theta)
    float sinf(float theta)

cdef class Camera3D(object):
    cdef public:
        object target
        double x
        double y
        double z
        double x_rotation
        double y_rotation
        bint has_sinf

    cpdef object rotate(self, double x, iny)

    cpdef object update(self, double dt)

    @cython.locals(x_r=double)
    cpdef object transform(self)

    @cython.locals(x_r=double)
    cpdef object look(self)
