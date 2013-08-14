import cython

cdef class Recipe:
	cdef public:
		bint shapeless
		list ingre
		object output

cdef class Recipes:
	cdef public:
		list recipes
		int nr_recipes

	cpdef object remove_empty_line_col(self, list ingre_list)

	@cython.locals(ingre_list=list, sub_ingre=list)
	cpdef object parse_recipe(self, object shape, object ingre)

	cpdef object add_recipe(self, shape, ingre, output)

	@cython.locals(ingre_list=list)
	cpdef object add_shapeless_recipe(self, ingre, output)

	@cython.locals(id_list=list, shapeless_id_list=list)
	cpdef object craft(self, input_blocks)

	cpdef object dump(self)

cdef class SmeltingRecipes:
	cdef public:
		list recipes
		int nr_recipes

	cpdef object add_recipe(self, ingre, output)

	cpdef object smelt(self, ingre)
