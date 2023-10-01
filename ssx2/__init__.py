import bpy
from bpy.utils import register_class, unregister_class

from .ssx2_model import ssx2_model_register, ssx2_model_unregister
from .ssx2_world import ssx2_world_register, ssx2_world_unregister
from .ssx2_model_pack import ssx2_set_mxf_data

from ..external.ex_utils import prop_split
from ..general.bx_utils import getset_instance_collection


classes = (
)

def ssx2_register():
	for c in classes:
		register_class(c)

	ssx2_world_register()
	ssx2_model_register()

def ssx2_unregister():

	ssx2_model_unregister()
	ssx2_world_unregister()

	for c in classes:
		unregister_class(c)