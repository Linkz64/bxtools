import bpy
from bpy.utils import register_class, unregister_class
from mathutils import Vector, Matrix
from math import ceil
import json
import time
import os

from ..panels import SSX2_Panel
from ..external.ex_utils import prop_split
#from ..general.bx_utils import getset_instance_collection, run_without_update
from ..general.blender_set_data import * # set_patch_object
from ..general.blender_get_data import get_images_from_folder, get_uvs, get_uvs_per_verts
from ..general.bx_utils import *

from .ssx2_world_io_in import get_patches_json#*
from .ssx2_world_patches import (
	ssx2_world_patches_register, 
	ssx2_world_patches_unregister,
	create_imported_patches,
	
	SSX2_OP_AddPatch,
	SSX2_OP_AddControlGrid,
	SSX2_OP_AddSplineCage,
	SSX2_OP_AddPatchMaterial,
	SSX2_OP_SendMaterialToModifier,
	SSX2_OP_ToggleControlGrid,
	SSX2_OP_CageToPatch,
	SSX2_OP_FlipSplineOrder,
	SSX2_OP_PatchSplit4x4,

	patch_tex_map_equiv_uvs,
	patch_known_uvs,
	existing_patch_uvs, # function
)
from .ssx2_constants import (
	enum_ssx2_world_project_mode,
	enum_ssx2_world,
	# enum_ssx2_path_mode,
	enum_ssx2_patch_group,
	enum_ssx2_surface_type,
	enum_ssx2_surface_type_spline,
	enum_ssx2_surface_type_extended,
	enum_ssx2_empty_mode,
	enum_ssx2_curve_mode,
)
from .ssx2_world_lightmaps import SSX2_OP_BakeTest




## Operators

class SSX2_OP_SelectSplineCageV(bpy.types.Operator):
	bl_idname = "curve.select_spline_cage_along_v"
	bl_label = "Select Along V"

	@classmethod
	def poll(self, context):
		obj = context.active_object
		if obj is None:
			return False
		elif context.active_object.mode == 'EDIT':
			return True

	def execute(self, context):
		# selected_objs = context.selected_objects
		active_obj = context.active_object

		if active_obj.ssx2_CurveMode != 'CAGE':
			return {'CANCELLED'}
		# if active_obj.mode != 'EDIT':
		# 	return {'CANCELLED'}

		splines = active_obj.data.splines

		select_indices = []
		for spline in splines:
			for j, p in enumerate(spline.bezier_points):
				if p.select_control_point:
					select_indices.append((j, 0))
				if p.select_left_handle:
					select_indices.append((j, 1))
				if p.select_right_handle:
					select_indices.append((j, 2))

		if len(select_indices) == 0:
			self.report({'WARNING'}, "No points selected")
			return {'CANCELLED'}

		for uh in select_indices:
			for spline in splines:
				p = spline.bezier_points[uh[0]]
				if uh[1] == 0:
					p.select_control_point = True
				elif uh[1] == 1:
					p.select_left_handle = True
				elif uh[1] == 2:
					p.select_right_handle = True

		return {'FINISHED'}


class SSX2_OP_AddInstance(bpy.types.Operator): # change this to use collection instead of model object
	bl_idname = 'object.ssx2_add_instance'
	bl_label = "Model Instance"
	bl_description = "Generate an instance"
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	@classmethod
	def poll(self, context):
		return False
	
	def execute(self, context):
		mdl = context.scene.ssx2_ModelForAddInstance
		bpy.ops.object.select_all(action='DESELECT')

		active_obj = context.active_object
		print(active_obj)

		if mdl == None:
			make_new = False
			if active_obj != None:
				if active_obj.type == 'MESH' and active_obj.parent == None:
					mdl = active_obj
				else:
					make_new = True
			else:
				make_new = True
			if make_new == True:
				print("made new")
				empty = bpy.data.objects.new("ins_", None)
				context.scene.collection.objects.link(empty)
				bpy.context.view_layer.objects.active = empty
				empty.select_set(True)
				return {"FINISHED"}

		if mdl.type == 'MESH':
			mdlinst = getset_instance_collection(mdl, f"ins_{mdl.name}")

			bpy.ops.object.collection_instance_add(collection=mdlinst)
			inst = bpy.context.active_object
			#inst.show_instancer_for_viewport = False
			inst.show_in_front = True
			inst.ssx2_ModelForInstance = mdl # custom property
			
			print(inst.instance_collection.objects)
			return {"FINISHED"}
		else:
			print(mdl.name, mdl.type, 'Failed')
			return {'CANCELLED'}

class SSX2_OP_AddSplineBezier(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_spline_bezier'
	bl_label = "Bezier Curve"
	bl_description = 'Generate a bezier curve'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	def execute(self, context):

		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		collection = bpy.data.collections.get("Splines")

		if collection is None:
			self.report({'WARNING'}, "'Splines' Collection not found!")
			collection = bpy.context.collection

		bpy.ops.curve.primitive_bezier_curve_add(
			radius=bpy.context.scene.bx_WorldScale/100, 
			enter_editmode=False, 
			align='CURSOR',
			rotation=(0.0, 0.0, 0.0)) # location=(0, 0, 0), scale=(1, 1, 1)

		curve_obj = bpy.context.object
		collection_it_was_added_to = curve_obj.users_collection[0]

		curve_obj.ssx2_CurveMode = 'SPLINE'
		curve_obj.ssx2_SplineProps.type = '13'

		if collection_it_was_added_to.name != collection.name:
			collection_it_was_added_to.objects.unlink(curve_obj)
			collection.objects.link(curve_obj)

		return {"FINISHED"}

class SSX2_OP_AddSplineNURBS(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_spline_nurbs'
	bl_label = "NURBS Curve"
	bl_description = 'Generate a NURBS curve'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	@classmethod
	def poll(self, context):
		return False

	def execute(self, context):

		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		collection = bpy.data.collections.get("Splines")

		if collection is None:
			self.report({'WARNING'}, "'Splines' Collection not found!")
			collection = bpy.context.collection

		bpy.ops.curve.primitive_nurbs_curve_add(
			radius=bpy.context.scene.bx_WorldScale/100, 
			enter_editmode=False, 
			align='CURSOR',
			rotation=(0.0, 0.0, 0.0))

		curve_obj = bpy.context.object
		collection_it_was_added_to = curve_obj.users_collection[0]

		curve_obj.ssx2_SplineProps.type = '13'
		curve_obj.data.splines[0].use_bezier_u = True
		curve_obj.data.splines[0].use_endpoint_u = True

		if collection_it_was_added_to.name != collection.name:
			collection_it_was_added_to.objects.unlink(curve_obj)
			collection.objects.link(curve_obj)

		return {"FINISHED"}



class SSX2_WorldImportExportPropGroup(bpy.types.PropertyGroup): # ssx2_WorldImportExportProps
	importFolderPath: bpy.props.StringProperty(name="", subtype='DIR_PATH', 
		default="",
		description="Folder that contains the world files")
	worldChoice: bpy.props.EnumProperty(name='World Choice', items=enum_ssx2_world, default='gari')
	worldChoiceCustom: bpy.props.StringProperty(name="", default="gari", subtype='NONE',
		description="Name of input file e.g gari, megaple, pipe")
	importTextures: bpy.props.BoolProperty(name="Import Textures", default=True)
	importNames: bpy.props.BoolProperty(name="Import Names", default=True)

	importSplines: bpy.props.BoolProperty(name="Import Splines", default=True)
	expandImportSplines: bpy.props.BoolProperty(default=False)
	splineImportAsNURBS: bpy.props.BoolProperty(default=False)

	importPatches: bpy.props.BoolProperty(name="Import Patches", default=True)
	expandImportPatches: bpy.props.BoolProperty(default=False)
	patchImportGrouping: bpy.props.EnumProperty(name='Grouping', items=enum_ssx2_patch_group, default='BATCH')
	patchImportAsControlGrid: bpy.props.BoolProperty(default=False)

	importPaths: bpy.props.BoolProperty(name="Import Paths", default=True)
	importPathsAsCurve: bpy.props.BoolProperty(default=True)
	expandImportPaths: bpy.props.BoolProperty(default=False)

	exportFolderPath: bpy.props.StringProperty(name="", subtype='DIR_PATH', default="",
		description="Export folder path")
	exportPatches: bpy.props.BoolProperty(name="Export Patches", default=True)
	exportPatchesCages: bpy.props.BoolProperty(name="Cages", default=True)
	exportPatchesOverride: bpy.props.BoolProperty(name="Override", default=True)

	exportSplines: bpy.props.BoolProperty(name="Export Splines", default=True)
	exportSplinesOverride: bpy.props.BoolProperty(name="Override", default=True)

	exportPathsGeneral: bpy.props.BoolProperty(name="Export Paths General", default=True)
	exportPathsShowoff: bpy.props.BoolProperty(name="Export Paths Showoff", default=True)


class SSX2_WorldPathEventPropGroup(bpy.types.PropertyGroup):
	# name: bpy.props.StringProperty(name="", subtype='NONE',
	# 	description="Name of the event")
	u0: bpy.props.IntProperty(name="u0",
		description="",
		min=-1,
		max=1000)
	u1: bpy.props.IntProperty(name="u1",
		description="",
		min=-1,
		max=1000)
	u2: bpy.props.FloatProperty(name="u2")
	u3: bpy.props.FloatProperty(name="u3")

	checked: bpy.props.BoolProperty(name="", default=False)

class SSX2_WorldPathPropGroup(bpy.types.PropertyGroup):
	# mode: bpy.props.EnumProperty(name='Path Mode', items=enum_ssx2_path_mode)         # Ai / Events
	reset: bpy.props.BoolProperty(name="Reset", default=True, # FOR AIPATHS ONLY?
		description="Can be warped to when reset")
	start: bpy.props.BoolProperty(name="Start Point", default=False, # FOR AIPATHS ONLY?
		description="Start/Spawn Point")

	aipaths_u3: bpy.props.IntProperty(name="AiPaths u1",
		description="",)
		# min=-1,
		# max=1000)

	eventpaths_u2: bpy.props.FloatProperty(name="EventPaths u2",
		description="")


	events: bpy.props.CollectionProperty(type=SSX2_WorldPathEventPropGroup)

	# active_event_index = bpy.props.IntProperty(default=0)



class SSX2_EmptyPanel(SSX2_Panel):
	bl_label = "BX Empty"
	bl_idname = "OBJECT_PT_SSX2_Empty"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"
	bl_options = {"HIDE_HEADER"}

	@classmethod
	def poll(cls, context):
		return \
		context.scene.bx_GameChoice == 'SSX2' and \
		(context.object is not None) and \
		context.object.type == 'EMPTY'

	def draw(self, context):
		obj = context.object
		layout = self.layout#.column()
		prop_split(layout, obj, "ssx2_EmptyMode", "Empty Mode")

		empty_mode = obj.ssx2_EmptyMode

		if empty_mode == "PATH_AI" or empty_mode == "PATH_EVENT":
			path_props = obj.ssx2_PathProps
			events = path_props.events

			if empty_mode == "PATH_AI":
				layout.prop(path_props, "reset", text="Reset Target")
				layout.prop(path_props, "start", text="Start Point")
				prop_split(layout, path_props, "aipaths_u3", "Unknown 3")
			else:
				prop_split(layout, path_props, "eventpaths_u2", "Unknown 2")


			# layout.label(text="Path Mode: [Enum]")

			events_box = layout.box()
			evt_box_header = events_box.row(align=True)

			evt_box_header.label(text="Events")
			evt_box_header.operator(SSX2_WorldPathEventAdd.bl_idname, text="Add", icon="ADD")
			evt_box_header.operator(SSX2_WorldPathEventRemove.bl_idname, text="Remove", icon="REMOVE")

			for event in events:
				row = events_box.row(align=True)
				evt_header_row = row

				evt_header_row.prop(event, "checked") #text=event.name)

				split1 = evt_header_row.split(align=True, factor=0.45)
				split_name_ints = split1.split(align=True, factor=0.42)
				#split_name_ints.prop(event, "name", text="") # event.name

				#evt_ints = split_name_ints.row(align=True)
				split_name_ints.prop(event, "u0", text="")
				split_name_ints.prop(event, "u1", text="")

				evt_floats = split1.row(align=True)
				evt_floats.prop(event, "u2", text="")
				evt_floats.prop(event, "u3", text="")


		elif empty_mode == "INSTANCE":
			col = self.layout.column()
			prop_split(col, context.object, 'ssx2_ModelForInstance', "Model")
			row = col.row()
			row.prop(context.object, 'show_instancer_for_viewport', text='Show Instancer')
			row.prop(context.object, 'show_in_front')#, text='Show in Front')


class SSX2_OP_AddPath(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_path'
	bl_label = "Add Path"
	bl_description = 'Generate a path'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	empties: bpy.props.BoolProperty(name="Use Empties", default=False)

	def execute(self, context):

		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		collection = bpy.data.collections.get("Paths")

		if collection is None:
			self.report({'WARNING'}, "'Paths' Collection not found!")
			collection = bpy.context.collection


		if self.empties:

			name = f"Path"
			empty = bpy.data.objects.new(name, None)
			
			empty.empty_display_size = 100 / 100 # WorldScale
			empty.empty_display_type = 'CUBE'
			empty.location = bpy.context.scene.cursor.location

			empty.ssx2_EmptyMode = 'PATH_AI'
			empty.ssx2_PathProps.reset = True
			# empty.ssx2_PathProps.start = False
			empty.ssx2_PathProps.aipaths_u3 = 50

			collection.objects.link(empty)

			bpy.ops.object.select_all(action='DESELECT')
			empty.select_set(True)
			bpy.context.view_layer.objects.active = empty

			# parent_obj = empty

			# for i in range(2):
			# 	name = f"PathNode{i}"
			# 	empty = bpy.data.objects.new(name, None)
			# 	empty.empty_display_size = 100 / 100 # WorldScale
			# 	# empty.empty_display_type = 'PLAIN'
			# 	empty.location = (0, 3.5, -0.2)
			# 	empty.parent = parent_obj
			# 	collection.objects.link(empty)
			# 	parent_obj = empty

		else: # Poly Curve Path
			append_path = templates_append_path
			
			curve_data_name = "PathAppend"
			node_tree_name = "PathLinesAppend"
			node_tree = bpy.data.node_groups.get(node_tree_name)
			print("Append Node Tree:", node_tree is None)
			print("Append Path Data: True")

			if not os.path.isfile(append_path):
				self.report({'ERROR'}, f"Failed to append. Can't find: {append_path}")
				return {'CANCELLED'}

			with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
				if curve_data_name in data_from.curves:
					data_to.curves = [curve_data_name]
				else:
					self.report({'ERROR'}, f"Failed to append spline cage from {append_path}")
					return {'CANCELLED'}
				if node_tree is None:
					if node_tree_name in data_from.node_groups:
						data_to.node_groups = [node_tree_name]
					else:
						self.report({'ERROR'}, f"Failed to append geonodes from {append_path}")
						return {'CANCELLED'}

			node_tree = bpy.data.node_groups.get(node_tree_name)

			curve_data = bpy.data.curves.get(curve_data_name)
			# if curve_data.users == 0:
			# 	curve_data.use_fake_user = True
			curve_data = curve_data.copy()
			curve_obj = bpy.data.objects.new("Path", curve_data)
			curve_data.name = curve_obj.name

			node_modifier = curve_obj.modifiers.new(name="GeoNodes", type='NODES')
			node_modifier.node_group = node_tree

			collection.objects.link(curve_obj)

			curve_obj.select_set(True)
			bpy.context.view_layer.objects.active = curve_obj

			curve_obj.location = bpy.context.scene.cursor.location
			# bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


		return {"FINISHED"}

class SSX2_OP_AddPathChild(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_path_child'
	bl_label = "Add Path Child"
	bl_description = 'Generate a child node for the active node'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	def execute(self, context):

		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		parent_obj = bpy.context.active_object

		if parent_obj is None:
			self.report({'WARNING'}, "No active object")
			return {"CANCELLED"}
		else:
			if parent_obj.type != "EMPTY":
				self.report({'WARNING'}, "Active object needs to be an Empty")
				return {"CANCELLED"}

		collection = None
		for coll in bpy.data.collections:
			if parent_obj.name in coll.objects:
				collection = coll

		if collection is None:
			collection = bpy.data.collections.get("Paths")
			if collection is None:
				self.report({'WARNING'}, "'Paths' Collection not found!")
				collection = bpy.context.collection

		name = f"PathNode"
		empty = bpy.data.objects.new(name, None)
		empty.empty_display_size = 100 / 100 # WorldScale
		# empty.empty_display_type = 'PLAIN'
		empty.location = (0, 3, -0.2)
		empty.parent = parent_obj

		collection.objects.link(empty)

		bpy.ops.object.select_all(action='DESELECT')
		empty.select_set(True)
		bpy.context.view_layer.objects.active = empty

		return {"FINISHED"}


class SSX2_WorldPathEventAdd(bpy.types.Operator):
	bl_idname = "object.ssx2_add_path_event"
	bl_label = "Add Event"

	def execute(self, context):
		obj = bpy.context.active_object
		events = obj.ssx2_PathProps.events
		new_event = events.add()
		#new_event.name = f"Event {len(events)}"#{len(events):03}"
		return {'FINISHED'}

class SSX2_WorldPathEventRemove(bpy.types.Operator):
	bl_idname = "object.ssx2_remove_path_event"
	bl_label = "Remove Event"

	def execute(self, context):
		obj = bpy.context.active_object 
		events = obj.ssx2_PathProps.events

		new_list = []

		for i, event in enumerate(events):
			if event.checked == False:
				new_list.append((
					#event.name, 
					event.u0, 
					event.u1, 
					event.u2, 
					event.u3,
					event.checked))

		events.clear()

		for new in new_list:
			new_event = events.add()
			#new_event.name = new[0]
			new_event.u0 = new[1]
			new_event.u1 = new[2]
			new_event.u2 = new[3]
			new_event.u3 = new[4]
			new_event.checked = new[5]

		return {'FINISHED'}


class SSX2_WorldSplinePropGroup(bpy.types.PropertyGroup): # ssx2_SplineProps
	type: bpy.props.EnumProperty(name='Spline Type', items=enum_ssx2_surface_type_spline)

	# change these to enum? spline_hide_mode = (NONE, SHOWOFF, RACE)
	#	assuming showoff and race set to True hides it in every mode
	#
	# hideShowoff: bpy.props.BoolProperty(name="Hide Showoff", default=False,
	# 	description="Hide in showoff modes.")
	# hideRace: bpy.props.BoolProperty(name="Hide Race", default=False,
	# 	description="Hide in race modes.")

class SSX2_CurvePanel(SSX2_Panel):
	bl_label = "BX Spline Curve"
	bl_idname = "OBJECT_PT_SSX2_Spline_Curve"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"
	bl_options = {"HIDE_HEADER"}

	@classmethod
	def poll(cls, context):
		return context.scene.bx_GameChoice == 'SSX2' and \
		(context.object is not None) # and context.object.type == 'SURFACE')
		# context.ssx2_SplineProps.isControlGrid # this doesn't work

	def draw(self, context):
		layout = self.layout
		obj = context.object

		if obj.type == 'CURVE':
			prop_split(layout, obj, "ssx2_CurveMode", "Curve Mode")

			if obj.ssx2_CurveMode == 'SPLINE':
				prop_split(layout, obj.ssx2_SplineProps, 'type', "Spline Type")

			elif obj.ssx2_CurveMode == 'PATH_AI' or obj.ssx2_CurveMode == 'PATH_EVENT':
				path_props = obj.ssx2_PathProps
				events = path_props.events

				if obj.ssx2_CurveMode == 'PATH_AI':
					layout.prop(path_props, "reset", text="Reset Target")
					layout.prop(path_props, "start", text="Start Point")
					prop_split(layout, path_props, "aipaths_u3", "Unknown 3")
				else:
					prop_split(layout, path_props, "eventpaths_u2", "Unknown 2")


				# layout.label(text="Path Mode: [Enum]")

				events_box = layout.box()
				evt_box_header = events_box.row(align=True)

				evt_box_header.label(text="Events")
				evt_box_header.operator(SSX2_WorldPathEventAdd.bl_idname, text="Add", icon="ADD")
				evt_box_header.operator(SSX2_WorldPathEventRemove.bl_idname, text="Remove", icon="REMOVE")

				for event in events:
					row = events_box.row(align=True)
					evt_header_row = row

					evt_header_row.prop(event, "checked") #text=event.name)

					split1 = evt_header_row.split(align=True, factor=0.45)
					split_name_ints = split1.split(align=True, factor=0.42)

					#split_name_ints.prop(event, "name", text="") # event.name

					#evt_ints = split_name_ints.row(align=True)
					split_name_ints.prop(event, "u0", text="")
					split_name_ints.prop(event, "u1", text="")

					evt_floats = split1.row(align=True)
					evt_floats.prop(event, "u2", text="")
					evt_floats.prop(event, "u3", text="")







def update_select_by_surface_type(self, context):
	# select surface patches by surface type
	# note context only works on `set=`
	if bpy.context.mode != "OBJECT":
		bpy.ops.object.mode_set(mode="OBJECT")

	#bpy.context.view_layer.layer_collection
	#bpy.context.view_layer.objects
	#bpy.data.objects
	all_objects = bpy.context.view_layer.objects
	
	#selected_type = enum_ssx2_surface_type[context] # check enum_ssx2_surface_type
	selected_type = self.patchSelectByType # string
	selected_int = int(selected_type)
	found = False
	if selected_int < 50: #selected_type not in ('50', '51'):
		for obj in all_objects:
			if obj.type == 'SURFACE' or obj.ssx2_PatchProps.isControlGrid or obj.ssx2_CurveMode == 'CAGE':
				#if 'ssx2_PatchType' in dir(obj):if obj.ssx2_PatchType == selected_type:
				if obj.ssx2_PatchProps.type == selected_type:#selected_type[0]:
					obj.select_set(True)
					found = True
	elif selected_int == 50: # NURBS/Bezier Surface
		for obj in all_objects:
			if obj.type == 'SURFACE':
				obj.select_set(True)
				found = True
	elif selected_int == 51: # Control Grid
		for obj in all_objects:
			if obj.ssx2_PatchProps.isControlGrid:
				obj.select_set(True)
				found = True
	elif selected_int == 52:  # All Spline Cage
		for obj in all_objects:
			if obj.type == 'CURVE' and obj.ssx2_CurveMode == 'CAGE':
				obj.select_set(True)
				found = True
	elif selected_int == 53:  # Dual Spline Cage
		for obj in all_objects:
			if obj.type == 'CURVE' and obj.ssx2_CurveMode == 'CAGE':
				if len(obj.data.splines) == 2:
					obj.select_set(True)
					found = True
	elif selected_int == 54:  # Quad Spline Cage
		for obj in all_objects:
			if obj.type == 'CURVE' and obj.ssx2_CurveMode == 'CAGE':
				if len(obj.data.splines) == 4:
					obj.select_set(True)
					found = True
	elif selected_int == 55:  # Hexa Spline Cage
		for obj in all_objects:
			if obj.type == 'CURVE' and obj.ssx2_CurveMode == 'CAGE':
				if len(obj.data.splines) == 6:
					obj.select_set(True)
					found = True

	# else: # select all surf/grid

	if found == False:
		pass
		#bx_report("None found", title="Info", icon='INFO')

def poll_mat_for_add_patch(self, context):
	return context.use_nodes
	#return context.name.startswith('surf') or context.name.startswith('patch')

class SSX2_WorldUIPropGroup(bpy.types.PropertyGroup): # ssx2_WorldUIProps class definition
	type: bpy.props.EnumProperty(name='Surface Type', items=enum_ssx2_surface_type)
	patchSelectByType: bpy.props.EnumProperty(name='Select by Surface Type', items=enum_ssx2_surface_type_extended, update=update_select_by_surface_type,
		description="Test")
	patchMaterialChoice: bpy.props.PointerProperty(type=bpy.types.Material, poll=poll_mat_for_add_patch)
	patchTypeChoice: bpy.props.EnumProperty(name='Select by Surface Type', items=enum_ssx2_surface_type, default='1')

	# expandImportSplines: bpy.props.BoolProperty(default=False)
	# expandImportPatches: bpy.props.BoolProperty(default=False)
	# expandImportPaths: bpy.props.BoolProperty(default=False)

	expandToolsPatches: bpy.props.BoolProperty(default=False)



class SSX2_OP_WorldInitiateProject(bpy.types.Operator):
	bl_idname = "scene.ssx2_world_initiate_project"
	bl_label = "Initiate Project"
	bl_description = "Create project collections and set recommended view settings"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):

		scene = bpy.context.scene
		scene_collection = scene.collection
		# view = context.space_data

		# print(dir(bpy.data))

		layout = bpy.data.screens.get("Layout")
		outliner = None
		if layout is not None:
			for area in layout.areas:
				if area.type == "OUTLINER":
					outliner = area.spaces[0]
					outliner.show_restrict_column_render = False
					outliner.show_restrict_column_select = True

				if area.type == "VIEW_3D":
					view = area.spaces[0]
					view.clip_start = 0.5#0.1
					view.clip_end = 2000
					view.overlay.display_handle = 'ALL'

		#world = getset_collection_to_target("World", scene_collection)
		getset_collection_to_target("Patches", scene_collection)
		getset_collection_to_target("Splines", scene_collection)

		# view.clip_start = 0.5#0.1
		# view.clip_end = 2000
		# view.overlay.display_handle = 'ALL'

		return {'FINISHED'}

class SSX2_OP_WorldExpandUIBoxes(bpy.types.Operator): # turn this into a general thing not just world
	bl_idname = "object.ssx2_expand_ui_boxes"
	bl_label = ""
	bl_description = "Expand box"
	#bl_options = {'REGISTER'}#, 'UNDO'}

	prop: bpy.props.StringProperty()

	def execute(self, context):
		#print(self.prop)
		props_split = self.prop.split('.')
		#if type(props_split) == list:
		props = getattr(bpy.context.scene, props_split[0])
		setattr(props, props_split[1], not getattr(props, props_split[1]))
		return {'FINISHED'}



class SSX2_OP_WorldExport(bpy.types.Operator):
	bl_idname = "object.ssx2_export_world"
	bl_label = "Export"
	bl_description = "Export world"

	@classmethod
	def poll(self, context):
		io = context.scene.ssx2_WorldImportExportProps
		return io.exportPatches or io.exportSplines or io.exportPathsGeneral or io.exportPathsShowoff

	def execute(self, context):
		time_export_star = time.time()

		io = bpy.context.scene.ssx2_WorldImportExportProps
		scale = bpy.context.scene.bx_WorldScale

		if len(bpy.path.abspath(io.exportFolderPath)) == 0:
			self.report({'ERROR'}, "'Project Folder' property is empty")
			return {"CANCELLED"}


		if io.exportPathsGeneral or io.exportPathsShowoff: # <------------------------- Export Paths
			print("Exporting Paths")

			export_names = False

			things = []
			if io.exportPathsGeneral:
				things.append('General')
			if io.exportPathsShowoff:
				things.append('Showoff')

			for i, thingy in enumerate(things):
				col_main_name = "Paths " + thingy
				extension = 'AIP' if thingy == 'General' else 'SOP'

				print(thingy, col_main_name, extension)

				col_main = bpy.data.collections.get(col_main_name)
				if col_main is None:
					self.report({'ERROR'}, f"'{col_main_name}' collection not found")
					return {'CANCELLED'}

				all_objects = col_main.all_objects

				if len(all_objects) == 0:
					self.report({'ERROR'}, f"No objects found in '{col_main_name}' collection")
					return {'CANCELLED'}

				json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath)) + '/' + extension + '.json'

				# if not os.path.isfile(json_export_path):
				# 	self.report({'ERROR'}, f"'               .json' not found.\n{json_export_path}")
				# 	return {'CANCELLED'}

				roots_ai = []
				roots_events = []

				for obj in all_objects:
					if obj.ssx2_EmptyMode == 'PATH_AI' or obj.ssx2_CurveMode == 'PATH_AI':
						roots_ai.append(obj)
					elif obj.ssx2_EmptyMode == 'PATH_EVENT' or obj.ssx2_CurveMode == 'PATH_EVENT':
						roots_events.append(obj)

				if len(roots_ai) == 0 and len(roots_events) == 0:
					self.report({'ERROR'}, f"No paths found in '{col_main_name}' collection")
					return {'CANCELLED'}

				temp_json = {
					"StartPosList": [],
					"AIPaths": [],
					"RaceLines": []
				}
				for j, root in enumerate(roots_ai):      #  <--- AI PATHS
					path_props = root.ssx2_PathProps
					m = root.matrix_world
					spline_points = root.data.splines[0].points
					origin = Vector((m[0][3], m[1][3], m[2][3]))
					root_loc = Vector(spline_points[0].co[:3])

					new_data = {
						"Name": root.name if export_names else None,
						"Type":  2,
						"U1": 100,
						"U2": 4,
						"U3": path_props.aipaths_u3,
						"U4": 101,
						"U5": 4,
						"Respawnable": int(path_props.reset),
						"PathPos": (),
						"PathPoints": [],
						"PathEvents": []
					}

					if root.type == "EMPTY":
						new_data["PathPos"] = tuple(root.location * 100), # WorldScale
						new_data["PathPoints"] = [tuple(child.location * 100) for child in root.children_recursive], # WorldScale
					else:
						new_data["PathPos"] = tuple((origin + root_loc) * 100) # WorldScale
						spline_points = root.data.splines[0].points
						adjusted_points = adjust_path_points(spline_points)
						for pt in adjusted_points:
							new_data["PathPoints"].append(tuple(pt * 100))

					for event in path_props.events:
						temp_event = {
							"EventType":event.u0,
							"EventValue":event.u1,
							"EventStart":event.u2 * 100, # WorldScale
							"EventEnd":event.u3 * 100, # WorldScale
						}
						new_data["PathEvents"].append(temp_event)

					if path_props.start:
						temp_json["StartPosList"].append(j)

					temp_json["AIPaths"].append(new_data)

				for j, root in enumerate(roots_events):      #  <--- EVENT PATHS
					path_props = root.ssx2_PathProps
					m = root.matrix_world
					spline_points = root.data.splines[0].points
					origin = Vector((m[0][3], m[1][3], m[2][3]))
					root_loc = Vector(spline_points[0].co[:3])

					new_data = {
						"Name": root.name if export_names else None,
						"Type":  1,
						"U0": 0,
						"U1": 4,
						"U2": path_props.eventpaths_u2 * 100, # WorldScale
						"PathPos": None,
						"PathPoints": [],
						"PathEvents": [],
					}

					if root.type == "EMPTY":
						new_data["PathPos"] = tuple(root.location * 100)
						new_data["PathPoints"] = [tuple(child.location * 100) for child in root.children_recursive], # WorldScale
					else:
						new_data["PathPos"] = tuple((origin + root_loc) * 100)
						adjusted_points = adjust_path_points(spline_points)

						for pt in adjusted_points:
							new_data["PathPoints"].append(tuple(pt * 100))

					for event in path_props.events:
						temp_event = {
							"EventType":event.u0,
							"EventValue":event.u1,
							"EventStart":event.u2 * 100, # WorldScale
							"EventEnd":event.u3 * 100, # WorldScale
						}
						new_data["PathEvents"].append(temp_event)

					temp_json["RaceLines"].append(new_data)

				with open(json_export_path, 'w') as f:
					json.dump(temp_json, f, separators=(',', ':'))
					# json.dump(temp_json, f, indent=2)



		if io.exportSplines: # <------------------------------------------------------ Export Splines
			print("Exporting Splines")

			spline_collection = bpy.data.collections.get("Splines")
			if spline_collection is None:
				self.report({'ERROR'}, "'Splines' collection not found")#spline_collection = bpy.context.collection
				return {'CANCELLED'}

			spline_objects = spline_collection.all_objects

			if len(spline_objects) == 0:
				self.report({'ERROR'}, "No splines found in 'Splines' collection")
				return {'CANCELLED'}

			json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath))+'/Splines.json'

			if not os.path.isfile(json_export_path):
				self.report({'ERROR'}, f"'Splines.json' not found.\n{json_export_path}")
				return {'CANCELLED'}

			final_splines = []
			names = []

			print()
			for obj in spline_objects:
				props = obj.ssx2_SplineProps
				m = obj.matrix_world

				print("    ", obj.name)

				all_points = []
				segments = [] # from all_points to segments of 4
				#segments_unknowns = []

				get_name = False
				for i, s in enumerate(obj.data.splines):
					current_points = []

					if s.type == 'BEZIER':

						if len(s.bezier_points) == 1:
							print(f"Not enough points in {obj.name} spline {i}")
							continue

						for j, p in enumerate(s.bezier_points):
							if j == 0: # first
								current_points.append( (m @ p.co) * scale)
								current_points.append( (m @ p.handle_right) * scale)
							elif j == len(s.bezier_points)-1: # last
								current_points.append( (m @ p.handle_left) * scale)
								current_points.append( (m @ p.co) * scale)
							elif (j != 0) and (j != len(s.bezier_points)-1): # mids
								current_points.append( (m @ p.handle_left) * scale)
								current_points.append( (m @ p.co) * scale)
								current_points.append( (m @ p.handle_right) * scale)

					elif s.type == 'NURBS':
						continue
						# if len(s.points) % 4 != 0:
						# 	self.report({'ERROR'}, f"NURBS Spline in object {obj.name} is invalid\nPoint count must be divisible by 4")
						# 	return {'CANCELLED'}
						# for j, p in enumerate(s.points):
						# 	current_points.append( (m @ p.co) * scale)

						# check if points divide by 4
						# if not cancel and error
						pass
					else:
						continue

					# for pt in current_points:
					# 	print(pt)

					# if 'unknowns' in obj.keys(): [0.0, 0.0, 0.0, 0.0]
					# 	pass


					if len(current_points) != 0:
						all_points += current_points
						get_name = True
					else:
						print(f"No points in {obj.name} spline {i}")

				if get_name:
					names.append(obj.name)

				for i in range(0, len(all_points), 3):
					segment_points = all_points[i:i + 4]

					if i == len(all_points)-1:
						break

					#print(segment_points, segment_points, segment_points, segment_points)

					#print()

					#print(segment_points)

					spline_segments_json_obj = {
						"Points": [pt.to_tuple() for pt in segment_points],
						"U0": 0.0001,
						"U1": 0.0001,
						"U2": 0.0001,
						"U3": 0.0001,
					}

					segments.append(spline_segments_json_obj)

				spline_json_obj = {
					"SplineName": obj.name,
					"U0": 1,
					"U1": 1,
					"SplineStyle": int(obj.ssx2_SplineProps.type),
					"Segments": segments
				}

				final_splines.append(spline_json_obj)


			new_json = {}
			if io.exportSplinesOverride:
				
				overriden_indices = []
				with open(json_export_path, 'r') as f:
					new_json = json.load(f)

					for i, spline in enumerate(new_json['Splines']):
						try:
							index = names.index(spline['SplineName'])

							# final_splines[index]['U0'] = spline['U0']
							# final_splines[index]['U1'] = spline['U1']

							#spline['Segments'] = final_splines[index]['Segments']

							# i shouldve just gone through json.load(f), changed points then appended extra points and splines

							for j, seg in enumerate(spline['Segments']):
								final_splines[index]['Segments'][j]['U0'] = seg['U0']
								final_splines[index]['Segments'][j]['U1'] = seg['U1']
								final_splines[index]['Segments'][j]['U2'] = seg['U2']
								final_splines[index]['Segments'][j]['U3'] = seg['U3']
							
							spline['Segments'] = final_splines[index]['Segments']

							overriden_indices.append(index)
						except Exception:
							#print(f"{spline['SplineName']} is missing in Blender. Skipping.")
							print(Exception)
							print("BXT Error occurred. Skipping.")

					for i, spline in enumerate(final_splines):
						if i not in overriden_indices:
							print(i, final_splines[i]['SplineName'])
							new_json['Splines'].append(final_splines[i])

			else:
				with open(json_export_path, 'w') as f:
					new_json = {}
					new_json['Splines'] = []

					for spline in final_splines:
						new_json['Splines'].append(spline)

					# json.dump(new_json, f, indent=2)
			
			with open(json_export_path, 'w') as f:
				#json.dump(new_json, f, indent=2)
				#json.dump(new_json, f)
				json.dump(new_json, f, separators=(',', ':'))


		if io.exportPatches: #                                        <--- Export Patches
			print("Exporting Patches")
			patch_collection = bpy.data.collections.get("Patches")

			if patch_collection is None:
				self.report({'ERROR'}, "'Patches' collection not found")#patch_collection = bpy.context.collection
				return {'CANCELLED'}

			#patch_objects = patch_collection.all_objects
			patch_objects = []

			for obj in patch_collection.all_objects:
				#inst_col = None
				if obj.instance_type == 'COLLECTION': # already an EMPTY only property
					inst_col = obj.instance_collection
					if inst_col is not None:
						for sub_obj in inst_col.all_objects:
							if sub_obj.ssx2_CurveMode == 'CAGE': # make it work on all patch types
								patch_objects.append((3, sub_obj, obj))
							# with parent (0/1/2 sub_obj, obj)
							# no parent (0/1/2, sub_obj, None) and do an is None check instead of == 3
				elif obj.ssx2_CurveMode == 'CAGE':
					patch_objects.append((2, obj))
				elif obj.type == 'SURFACE':
					patch_objects.append((0, obj))
				elif obj.ssx2_PatchProps.isControlGrid:
					patch_objects.append((1, obj))

			if len(patch_objects) == 0:
				self.report({'ERROR'}, "No patches found in 'Patches' collection")
				return {'CANCELLED'}

			json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath))+'/Patches.json'

			print(json_export_path)

			if not os.path.isfile(json_export_path):
				self.report({'ERROR'}, f"'Patches.json' not found.\n{json_export_path}")
				return {'CANCELLED'}

			temp_json = {}
			temp_json['Patches'] = []


			for obj in patch_objects:
				obj_type = obj[0]
				
				if obj_type == 3: # blender asset
					inst_obj = obj[2]
					obj = obj[1]
					obj_name = inst_obj.name + '_' + obj.name

					# m = inst_obj.matrix_world # works alone but sub objects have to be applied
					col_off = inst_obj.instance_collection.instance_offset

					m_a = obj.matrix_world
					loc_a, rot_a, sca_a = m_a.decompose()
					loc_a = loc_a - col_off
					m_a = Matrix.LocRotScale(loc_a, rot_a, sca_a)

					m = inst_obj.matrix_world @ m_a
				else:
					obj = obj[1]
					obj_name = obj.name
					m = obj.matrix_world

				props = obj.ssx2_PatchProps
				print(obj_name)

				if obj_type == 2 or obj_type == 3: # export spline cage
					cage_nodes = None
					for mod in obj.modifiers:
						if mod.type == 'NODES' and mod.node_group:
							if "CageLoftAppend" in mod.node_group.name:
								cage_nodes = mod.node_group
								break
					if cage_nodes is None:
						continue

					double_v = mod["Input_6"]
					mat = mod["Input_7"]

					data_splines = obj.data.splines
					num_splines = len(data_splines)
					new_patches = []

					if num_splines == 2: # Dual Spline Cage
						# print("	2 splines")

						spline_strip = []

						raw = [bezier_to_raw(spline.bezier_points, m, scale) for spline in data_splines\
							if spline.type == 'BEZIER']

						length = len(raw[0])
						
						if length != len(raw[1]):
							self.report({'ERROR'}, f"Number of points must match on both splines {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}
						elif length < 4:
							# continue
							self.report({'ERROR'}, f"Not enough bezier points in {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}
						elif len(raw) == 0:
							# continue
							self.report({'ERROR'}, f"No bezier points in {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}

						u2 = []
						u3 = []
						for i in range(len(raw[0])):
							p1 = raw[0][i]
							p2 = raw[1][i]
							u2.append(p1 + ((p2 - p1) / 3))
							u3.append(p2 - ((p2 - p1) / 3))

						spline_strip.append(raw[0])
						spline_strip.append(u2)
						spline_strip.append(u3)
						spline_strip.append(raw[1])

						if double_v:
							doubled = double_quad_cage(spline_strip)
							new_patches.extend(segment_spline(next(doubled)))
							new_patches.extend(segment_spline(next(doubled)))
						else:
							new_patches.extend(segment_spline(spline_strip))

					elif num_splines == 4: # Quad Spline Cage
						# print("	4 splines")

						# empty = bpy.data.objects["Empty"]

						raw = [bezier_to_raw(spline.bezier_points, m, scale) for spline in data_splines\
							if spline.type == 'BEZIER']

						#length = len(raw[0])
						lengths = [len(raw[0]), len(raw[1]), len(raw[2]), len(raw[3])]
						
						if len(raw[0]) < 4:
							# continue
							self.report({'ERROR'}, f"Not enough bezier points in {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}
						elif len(raw) == 0:
							# continue
							self.report({'ERROR'}, f"No bezier points in {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}
						elif sum(lengths) / 4 != lengths[0]:
							self.report({'ERROR'}, f"Number of points must match on all splines {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}

						if double_v:
							doubled = double_quad_cage(raw)
							new_patches.extend(segment_spline(next(doubled)))
							new_patches.extend(segment_spline(next(doubled)))
						else:
							new_patches.extend(segment_spline(raw))

					elif num_splines == 6: # Hexa Spline Cage
						# print(" 6 splines")

						raw = [bezier_to_raw(spline.bezier_points, m, scale) for spline in data_splines\
							if spline.type == 'BEZIER']

						#length = len(raw[0])
						lengths = [len(raw[0]), len(raw[1]), len(raw[2]), len(raw[3]), len(raw[4]), len(raw[5])]
						
						if len(raw[0]) < 4:
							# continue
							self.report({'ERROR'}, f"Not enough bezier points in {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}
						elif len(raw) == 0:
							# continue
							self.report({'ERROR'}, f"No bezier points in {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}
						elif sum(lengths) / 6 != lengths[0]:
							self.report({'ERROR'}, f"Number of points must match on all splines {obj_name}")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}

						temp_strip1 = raw[0:3]
						temp_strip2 = raw[3:6]

						inbetween_spline = []

						for i in range(len(temp_strip1[0])):
							p1 = temp_strip1[2][i]
							p2 = temp_strip2[0][i]
							inbetween_spline.append((p1 + p2) / 2)

						temp_strip1.append(inbetween_spline)
						temp_strip2 = [inbetween_spline] + temp_strip2

						if double_v:
							doubled = double_quad_cage(temp_strip1)
							new_patches.extend(segment_spline(next(doubled)))
							new_patches.extend(segment_spline(next(doubled)))
							doubled = double_quad_cage(temp_strip2)
							new_patches.extend(segment_spline(next(doubled)))
							new_patches.extend(segment_spline(next(doubled)))
						else:
							new_patches.extend(segment_spline(temp_strip1) + segment_spline(temp_strip2))
						
					else:
						# print(obj_name, "must have 2, 4 or 6 splines. Skipping.")
						self.report({'WARNING'}, f"{obj_name} must have 2, 4 or 6 splines. Skipping.")
						continue

					tex = "0022.png"

					if mat is not None:
						tex_node = mat.node_tree.nodes.get("Image Texture")
						if tex_node is not None:
							tex = mat.node_tree.nodes["Image Texture"].image.name
							if not tex.endswith(".png") or len(tex) < 5:
								tex = "0022.png"

					#patch_uvs = patch_known_uvs[patch_tex_map_equiv_uvs[int(props.texMapPreset)]].copy()
					if not props.useManualUV:
						patch_uvs = patch_known_uvs[patch_tex_map_equiv_uvs[int(props.texMapPreset)]].copy()
					else:
						patch_uvs = [
							(props.manualUV0[0], -props.manualUV0[1]),
							(props.manualUV2[0], -props.manualUV2[1]), # these
							(props.manualUV1[0], -props.manualUV1[1]), # are swapped
							(props.manualUV3[0], -props.manualUV3[1]),
						]
					
					if props.fixU:
						fix_uvs_u(patch_uvs)
					if props.fixV:
						fix_uvs_v(patch_uvs)

					lightmap_uvs = [0.0, 0.0, 0.0625, 0.0625]
					lightmap_id = 0

					for i, patch in enumerate(new_patches):

						#print(patch_uvs[0])

						name = f"{obj_name}_{i}"

						patch_points = []
						for uh in patch:
							for p in uh:
								x, y, z = p
								patch_points.append((x, y, z))

						# tex = "0022.png"
						# patch_uvs = patch_known_uvs[0]
						# lightmap_uvs = [0.0, 0.0, 0.0625, 0.0625]
						# lightmap_id = 0

						patch_json_obj = {
							"PatchName": name,
							"LightMapPoint": lightmap_uvs,
							"UVPoints": patch_uvs,
							"Points": patch_points,
							"PatchStyle": props.type,
							"TrickOnlyPatch": props.showoffOnly,
							"TexturePath": tex,
							"LightmapID": lightmap_id
						}
						temp_json['Patches'].append(patch_json_obj)

				elif obj_type == 0: # export surface patch

					patch_points = []
					for spline in obj.data.splines:
						for p in spline.points:
							x, y, z, w = (m @ p.co) * scale
							patch_points.append((x, y, z))

					if not props.useManualUV:
						patch_uvs = patch_known_uvs[patch_tex_map_equiv_uvs[int(props.texMapPreset)]].copy()
					else:
						patch_uvs = [
							# props.manualUV0.to_tuple(),
							# props.manualUV1.to_tuple(),
							# props.manualUV2.to_tuple(),
							# props.manualUV3.to_tuple(),
							(props.manualUV0[0], -props.manualUV0[1]),
							(props.manualUV2[0], -props.manualUV2[1]), # these
							(props.manualUV1[0], -props.manualUV1[1]), # are swapped
							(props.manualUV3[0], -props.manualUV3[1]),
						]

					if len(obj.material_slots) != 0:
						mat = bpy.data.materials.get(obj.material_slots[0].name)

						if mat is not None:
							# tex_node = mat.node_tree.get("Image texture")
							tex_node = mat.node_tree.nodes.get("Image Texture")
							if tex_node is not None:
								tex = mat.node_tree.nodes["Image Texture"].image.name
								if not tex.endswith(".png") or len(tex) < 5:
									tex = "0022.png"
							else:
								tex = "0024.png"
					else:
						tex = "0024.png"

					if 'lightmap_uvs' in obj.keys():
						lightmap_uvs = get_custom_prop_vec4(obj, 'lightmap_uvs')
						lightmap_id = obj['lightmap_id']
					else: # scaling down to 0.0 doesn't work
						lightmap_uvs = [0.0, 0.0, 0.0625, 0.0625] #[0.0, 0.6, 0.0625, 0.0625] #
						lightmap_id = 0

					if props.fixU:
						fix_uvs_u(patch_uvs)
					if props.fixV:
						fix_uvs_v(patch_uvs)

					patch_json_obj = {
						"PatchName": obj.name,
						"LightMapPoint": lightmap_uvs,
						"UVPoints": patch_uvs,
						"Points": patch_points,
						"PatchStyle": int(props.type),
						"TrickOnlyPatch": props.showoffOnly,
						"TexturePath": tex,
						"LightmapID": lightmap_id
					}
					temp_json['Patches'].append(patch_json_obj)

				else: # export control grid
					grid_points = []

					for vtx in obj.data.vertices:
						x, y, z = (m @ vtx.co) * scale
						grid_points.append((x, y, z, 1.0))

					# grid_uvs = [(uv[0], -uv[1]) for uv in get_uvs_per_verts(obj)]
					# patch_uvs = [grid_uvs[12], grid_uvs[0], grid_uvs[15], grid_uvs[3]] # uv corners from mesh

					if props.useManualUV:
						patch_uvs = [(props.manualUV0[0], -props.manualUV0[1]),
									 (props.manualUV2[0], -props.manualUV2[1]), # dont forget these
									 (props.manualUV1[0], -props.manualUV1[1]), # are swapped
									 (props.manualUV3[0], -props.manualUV3[1])]
					else:
						patch_uvs = patch_known_uvs[patch_tex_map_equiv_uvs[int(props.texMapPreset)]].copy()
						
					if len(obj.material_slots) != 0:
						mat = bpy.data.materials.get(obj.material_slots[0].name)
						if mat is not None:
							tex_node = mat.node_tree.nodes.get("Image Texture")
							# tex_node = mat.node_tree.get("Image texture")
							if tex_node is not None:
								tex = mat.node_tree.nodes["Image Texture"].image.name
								if not tex.endswith(".png") or len(tex) < 5:
									tex = "0022.png"
					else:
						tex = "0000.png"

					if 'lightmap_uvs' in obj.keys(): # and ('lightmap_id' in obj.keys())
						lightmap_uvs = get_custom_prop_vec4(obj, 'lightmap_uvs')
						lightmap_id = obj['lightmap_id']
					else:
						lightmap_uvs = [0.0, 0.0, 0.0625, 0.0625]
						lightmap_id = 0

					if props.fixU:
						fix_uvs_u(patch_uvs)
					if props.fixV:
						fix_uvs_v(patch_uvs)

					patch_json_obj = {
						"PatchName": obj.name,
						"LightMapPoint": lightmap_uvs,
						"UVPoints": patch_uvs,
						"Points": grid_points,
						"PatchStyle": int(props.type),
						"TrickOnlyPatch": props.showoffOnly,
						"TexturePath": tex,
						"LightmapID": lightmap_id
					}

					# print(patch_json_obj)

					temp_json['Patches'].append(patch_json_obj)


			with open(json_export_path, 'w') as f:
				json.dump(temp_json, f)
				#json.dumps(separators=(',', ':'))
				#json.dump(temp_json, f, indent=2)



		print("Time taken:", time.time() - time_export_star, "seconds")
		self.report({'INFO'}, "Exported")
		return {'FINISHED'}


class SSX2_OP_WorldImport(bpy.types.Operator):
	bl_idname = "object.ssx2_import_world"
	bl_label = "Import"
	bl_description = "Import world"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		s = context.scene
		io = s.ssx2_WorldImportExportProps
		return (\
			io.importPatches or \
			io.importSplines or \
			io.importPaths\
			) and \
			(s.bx_PlatformChoice == 'XBX' or s.bx_PlatformChoice == 'NGC' or\
			s.bx_PlatformChoice == 'PS2' or s.bx_PlatformChoice == 'ICE')

	def __init__(self, json_patches=[]):
		self.json_patches = json_patches
		self.images = []

		append_path = templates_append_path
		material_name = "PatchMaterialAppend"
		material = bpy.data.materials.get(material_name)

		if not os.path.isfile(append_path):
			self.report({'ERROR'}, f"Failed to append {append_path}")
			return {'CANCELLED'}

		if material is None:
			print("BXT Append Material:", material_name)
			with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
				if material_name in data_from.materials:
					data_to.materials = [material_name]
				else:
					self.report({'ERROR'}, f"BXT Failed to append material from {append_path}")
					return {'CANCELLED'}

		self.appended_material = bpy.data.materials.get(material_name)

		node_tree_name = "GridTesselateAppend"
		node_tree = bpy.data.node_groups.get(node_tree_name)

		if node_tree is None:
			with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
				if node_tree_name in data_from.node_groups:
					data_to.node_groups = [node_tree_name]
				else:
					self.report({'ERROR'}, f"Failed to append geonodes from {append_path}")
					return {'CANCELLED'}
				
		self.appended_geonodes = bpy.data.node_groups.get(node_tree_name)

	def create_patches_json(self):
		active_collection = bpy.context.collection
		io = bpy.context.scene.ssx2_WorldImportExportProps
		patch_grouping = io.patchImportGrouping
		patches_collection = bpy.data.collections['Patches']
		to_group = []

		if io.patchImportAsControlGrid:
			for i, json_patch in enumerate(self.json_patches): # IMPORT CONTROL GRID
				name = json_patch.name

				# patch = bpy.data.objects.get(name)
				# if patch is None or patch.type != 'MESH':
				mesh = bpy.data.meshes.new(name)
				patch = bpy.data.objects.new(name, mesh)

				uvs = [(uv[0], -uv[1]) for uv in json_patch.uvs]
				set_patch_control_grid(mesh, json_patch.points, uvs)#json_patch.uvs)
				
				short_texture_name = os.path.splitext(os.path.basename(json_patch.texture_path))[0] # no path no ext

				pch_mat_name = f"pch.{short_texture_name}"
				pch_mat = bpy.data.materials.get(pch_mat_name)
				if pch_mat is None:
					#pch_mat = set_patch_material(pch_mat_name)
					pch_mat = self.appended_material.copy()
					pch_mat.name = pch_mat_name

				pch_mat.node_tree.nodes["Image Texture"].image = bpy.data.images.get(json_patch.texture_path)
				patch.data.materials.append(pch_mat)

				existing_patch_uv_idx = existing_patch_uvs(json_patch.uvs)
				if existing_patch_uv_idx is None:
					patch.ssx2_PatchProps.useManualUV = True
					patch.ssx2_PatchProps.texMapPreset = '3'
					patch.color = (0.76, 0.258, 0.96, 1.0) # to see which ones are manual
				else:
					patch.ssx2_PatchProps.useManualUV = False
					patch.ssx2_PatchProps.texMapPreset = str(existing_patch_uv_idx)

				patch.ssx2_PatchProps.type = str(json_patch.type)
				patch.ssx2_PatchProps.showoffOnly = json_patch.showoff_only
				patch.ssx2_PatchProps.isControlGrid = True
				patch.ssx2_PatchProps.manualUV0 = (json_patch.uvs[0][0], -json_patch.uvs[0][1])
				patch.ssx2_PatchProps.manualUV1 = (json_patch.uvs[2][0], -json_patch.uvs[2][1])
				patch.ssx2_PatchProps.manualUV2 = (json_patch.uvs[1][0], -json_patch.uvs[1][1])
				patch.ssx2_PatchProps.manualUV3 = (json_patch.uvs[3][0], -json_patch.uvs[3][1])
				patch['index'] = i
				patch["offset"] = int(i * 720 + 160)
				patch['lightmap_uvs'] = json_patch.lightmap_uvs
				patch['lightmap_id']  = json_patch.lightmap_id

				node_modifier = patch.modifiers.new(name="GeoNodes", type='NODES')
				node_modifier.node_group = self.appended_geonodes
				node_modifier["Input_3"] = 1

				patches_collection.objects.link(patch)

				if patch_grouping != 'NONE':
					to_group.append(patch)
		else:
			for i, json_patch in enumerate(self.json_patches): # IMPORT PATCH NURBS TYPE
				
				patch = bpy.data.objects.get(json_patch.name)
				if patch is None or patch.type != 'SURFACE':
					patch = set_patch_object(json_patch.points, json_patch.name)

				existing_patch_uv_idx = existing_patch_uvs(json_patch.uvs)
				if existing_patch_uv_idx is None:
					patch.ssx2_PatchProps.useManualUV = True
					patch.ssx2_PatchProps.texMapPreset = '3'
					patch.color = (0.76, 0.258, 0.96, 1.0) # to see which ones are manual
				else:
					patch.ssx2_PatchProps.useManualUV = False
					patch.ssx2_PatchProps.texMapPreset = str(existing_patch_uv_idx)
					# patch.ssx2_PatchProps.texMap = patch_tex_maps[existing_patch_uv_idx] # already set by preset

				short_texture_name = os.path.splitext(os.path.basename(json_patch.texture_path))[0] # no path no ext

				pch_mat_name = f"pch.{short_texture_name}"
				pch_mat = bpy.data.materials.get(pch_mat_name)
				if pch_mat is None:
					#pch_mat = set_patch_material(pch_mat_name)
					pch_mat = self.appended_material.copy()
					pch_mat.name = pch_mat_name

				pch_mat.node_tree.nodes["Image Texture"].image = bpy.data.images.get(json_patch.texture_path)
				patch.data.materials.append(pch_mat)

				patch.ssx2_PatchProps.type = str(json_patch.type)
				patch.ssx2_PatchProps.showoffOnly = json_patch.showoff_only
				# patch.ssx2_PatchProps.manualUV0 = (json_patch.uvs[0][0], -json_patch.uvs[0][1])
				# patch.ssx2_PatchProps.manualUV1 = (json_patch.uvs[1][0], -json_patch.uvs[1][1])
				# patch.ssx2_PatchProps.manualUV2 = (json_patch.uvs[2][0], -json_patch.uvs[2][1])
				# patch.ssx2_PatchProps.manualUV3 = (json_patch.uvs[3][0], -json_patch.uvs[3][1])

				patch.ssx2_PatchProps.manualUV0 = (json_patch.uvs[0][0], -json_patch.uvs[0][1])
				patch.ssx2_PatchProps.manualUV1 = (json_patch.uvs[2][0], -json_patch.uvs[2][1])
				patch.ssx2_PatchProps.manualUV2 = (json_patch.uvs[1][0], -json_patch.uvs[1][1])
				patch.ssx2_PatchProps.manualUV3 = (json_patch.uvs[3][0], -json_patch.uvs[3][1])
				patch['index'] = i
				patch["offset"] = int(i * 720 + 160)
				patch['lightmap_uvs'] = json_patch.lightmap_uvs
				patch['lightmap_id']  = json_patch.lightmap_id
				patch['uvs0'] = json_patch.uvs[0]
				patch['uvs1'] = json_patch.uvs[1]
				patch['uvs2'] = json_patch.uvs[2]
				patch['uvs3'] = json_patch.uvs[3]

				if patch_grouping != 'NONE':
					to_group.append(patch)

		layer_collection = bpy.context.view_layer.layer_collection
		if patch_grouping == 'BATCH':
			group_size = 700 # make it a scene prop?

			for i, patch in enumerate(to_group):
				new_col = collection_grouping(f"Patch_Group", patches_collection, group_size, i)
				new_col.objects.link(patch)
				patches_collection.objects.unlink(patch)

			for collection in patches_collection.children:
				layer_col = get_layer_collection(layer_collection, collection.name)
				layer_col.exclude = True
		elif patch_grouping == 'TYPE':
			type_collections = []
			for enum in enum_ssx2_surface_type:
				new_col = getset_collection_to_target(f"Pch_{enum[1].replace(' ', '_')}", patches_collection)
				type_collections.append(new_col)

			for i, patch in enumerate(to_group):
				new_col = type_collections[int(patch.ssx2_PatchProps.type)]
				new_col.objects.link(patch)
				patches_collection.objects.unlink(patch)

			for collection in patches_collection.children:
				layer_col = get_layer_collection(layer_collection, collection.name)
				layer_col.exclude = True
		else: # 'NONE'
			get_layer_collection(layer_collection, patches_collection.name).exclude = True
		# else: # 'NONE'
		#	# need to comment out every `if patch_grouping != 'NONE':`
		# 	if active_collection.name in patches_collection.children:
		# 		new_col = active_collection
		# 		for i, patch in enumerate(to_group):
		# 			new_col.objects.link(patch)
		# 			patches_collection.objects.unlink(patch)
			
	def import_json(self):
		scene = bpy.context.scene
		scene_collection = scene.collection

		io = scene.ssx2_WorldImportExportProps
		#io.importNames
		#io.importTextures
		#io.patchImportGrouping

		folder_path = scene.ssx2_WorldImportExportProps.importFolderPath
		folder_path = os.path.abspath(bpy.path.abspath(folder_path))
		if not os.path.exists(folder_path): #.isdir
			self.report({'ERROR'}, f"Import Folder does not exist")
			return {'CANCELLED'}

		if io.importPatches: # PATCHES
			getset_collection_to_target('Patches', scene_collection)

			self.json_patches = get_patches_json(folder_path+'/Patches.json')
			self.images = get_images_from_folder(folder_path+'/Textures/')

			run_without_update(self.create_patches_json)


		if io.importPaths: # <------------------------------- Import Paths
			print("Importing Paths")

			aip_file_path = folder_path + '/AIP.json'
			sop_file_path = folder_path + '/SOP.json'
			if not os.path.isfile(aip_file_path):
				self.report({'ERROR'}, f"File 'AIP.json' does not exist in 'Import Folder'")
				return {'CANCELLED'}
			if not os.path.isfile(aip_file_path):
				self.report({'ERROR'}, f"File 'SOP.json' does not exist in 'Import Folder'")
				return {'CANCELLED'}

			collection_paths = bpy.data.collections.get('Paths')
			if collection_paths is None:
				collection_paths = bpy.data.collections.new('Paths')
				scene_collection.children.link(collection_paths)


			# APPEND PATH GEOMETRY NODES

			if io.importPathsAsCurve:
				append_path = templates_append_path
				node_tree_name = "PathLinesAppend"
				node_tree = bpy.data.node_groups.get(node_tree_name)
				print("BXT Append Node Tree:", node_tree is None)

				if not os.path.isfile(append_path):
					self.report({'ERROR'}, f"BXT Failed to append {append_path}")
					return {'CANCELLED'}

				with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
					if node_tree is None:
						if node_tree_name in data_from.node_groups:
							data_to.node_groups = [node_tree_name]
						else:
							self.report({'ERROR'}, f"BXT Failed to append geonodes from {append_path}")
							return {'CANCELLED'}

				node_tree = bpy.data.node_groups.get(node_tree_name)


			for i, file_path in enumerate((aip_file_path, sop_file_path)):
				with open(file_path, 'r') as f:
					data = json.load(f)

				# col_main_name = "Paths General" if i == 0 else "Paths Showoff"
				# col_main_name = "Paths AIP" if i == 0 else "Paths SOP"
				if i == 0:
					col_main_name = "Paths General"
					obj_main_name = "AIP"
				else:
					col_main_name = "Paths Showoff"
					obj_main_name = "SOP"

				col_main = bpy.data.collections.get(col_main_name)
				if col_main is None:
					col_main = bpy.data.collections.new(col_main_name)
					collection_paths.children.link(col_main)

				col_sub_name = f"{col_main_name} Ai"
				col_sub = bpy.data.collections.get(col_sub_name)
				if col_sub is None:
					col_sub = bpy.data.collections.new(col_sub_name)
					col_main.children.link(col_sub)


				start_paths = data["StartPosList"]
				for j, path in enumerate(data["AIPaths"]): #                         <- AI PATH
					#                            checked trick, snow, gari, alaska 
					name = path["Name"] if path["Name"] is not None else f"{obj_main_name}_Ai.{j}"
					# path_type = path["Type"] # multitool property. not needed
					# path_unk1 = path["U1"]   # always 100?
					# path_unk2 = path["U2"]   # always 4?
					path_unk3 = path["U3"]     # 0, 20, 25, 50, 80, 100
					# path_unk4 = path["U4"]   # always 101?
					# path_unk5 = path["U5"]   # always 4?
					path_respawn = path["Respawnable"]
					path_pos = Vector(path["PathPos"]) / 100 # WorldScale
					path_points = path["PathPoints"]
					path_events = path["PathEvents"]

					if io.importPathsAsCurve:
						curve = bpy.data.curves.new(name, 'CURVE')
						curve.dimensions = '3D'

						spline = curve.splines.new(type='NURBS')
						points_to_add = len(path_points)
						spline_points = spline.points
						spline_points.add(points_to_add)

						spline_points[0].co = (path_pos[0], path_pos[1], path_pos[2], 1.0)

						for k in range(1, len(spline_points)):
							pp = Vector(path_points[k - 1]) / 100 # current path point
							psp = Vector(spline_points[k - 1].co[:3])  # previous spline point
							new_point = psp + pp
							new_point = (new_point[0], new_point[1], new_point[2], 1.0)
							spline_points[k].co = new_point

						spline.type = 'POLY'

						curve_obj = bpy.data.objects.new(name, curve)
						col_sub.objects.link(curve_obj)

						curve_obj.ssx2_CurveMode = 'PATH_AI'
						curve_obj.ssx2_PathProps.reset = path_respawn
						curve_obj.ssx2_PathProps.start = True if j in start_paths else False
						curve_obj.ssx2_PathProps.aipaths_u3 = path_unk3

						events = curve_obj.ssx2_PathProps.events
						for k, event in enumerate(path_events):
							new_event = events.add()
							#new_event.name = f"Event {k + 1}"#{len(events):03}"
							new_event.u0 = event["EventType"]
							new_event.u1 = event["EventValue"]
							new_event.u2 = event["EventStart"] / 100
							new_event.u3 = event["EventEnd"] / 100

						# curve_obj.location = path_pos

						node_modifier = curve_obj.modifiers.new(name="GeoNodes", type='NODES')
						node_modifier.node_group = node_tree

					else:
						empty = bpy.data.objects.new(name, None)
						#collec_main.objects.link(empty)
						empty.empty_display_size = 100 / 100 # WorldScale
						empty.empty_display_type = 'CUBE'
						empty.location = path_pos

						empty.ssx2_EmptyMode = 'PATH_AI'
						# empty.ssx2_PathProps.mode = 'AI'
						empty.ssx2_PathProps.reset = path_respawn
						empty.ssx2_PathProps.start = True if j in start_paths else False
						empty.ssx2_PathProps.aipaths_u3 = path_unk3

						events = empty.ssx2_PathProps.events
						for k, event in enumerate(path_events):
							new_event = events.add()
							#new_event.name = f"Event {k + 1}"#{len(events):03}"
							new_event.u0 = event["EventType"]
							new_event.u1 = event["EventValue"]
							new_event.u2 = event["EventStart"] / 100
							new_event.u3 = event["EventEnd"] / 100
									
						col_sub.objects.link(empty)

						parent_obj = empty

						for k, point in enumerate(path_points):
							name = f"{obj_main_name}_Ai{j}.{k}"
							empty = bpy.data.objects.new(name, None)
							#collec_main.objects.link(empty)
							empty.empty_display_size = 100 / 100 # WorldScale
							# empty.empty_display_type = 'CUBE'
							empty.parent = parent_obj
							empty.location = Vector(point) / 100

							col_sub.objects.link(empty)

							parent_obj = empty

				col_sub_name = f"{col_main_name} Events"
				col_sub = bpy.data.collections.get(col_sub_name)
				if col_sub is None:
					col_sub = bpy.data.collections.new(col_sub_name)
					col_main.children.link(col_sub)

				for j, path in enumerate(data["RaceLines"]): #                         <- EVENT PATH / RACE LINES
					name = path["Name"] if path["Name"] is not None else f"{obj_main_name}_Events.{j}"
					# path_type = path["Type"]
					# path_unk0 = path["U0"] # always 0?
					# path_unk1 = path["U1"] # always 4?
					path_unk2 = path["U2"] / 100 # WorldScale
					# path_respawn = path["Respawnable"] # doesn't have it?
					path_pos = Vector(path["PathPos"]) / 100 # WorldScale
					path_points = path["PathPoints"]
					path_events = path["PathEvents"]


					if io.importPathsAsCurve:
						curve = bpy.data.curves.new(name, 'CURVE')
						curve.dimensions = '3D'

						spline = curve.splines.new(type='NURBS')
						points_to_add = len(path_points)
						spline_points = spline.points
						spline_points.add(points_to_add)

						spline_points[0].co = (path_pos[0], path_pos[1], path_pos[2], 1.0)

						for k in range(1, len(spline_points)):
							pp = Vector(path_points[k - 1]) / 100 # current path point
							psp = Vector(spline_points[k - 1].co[:3])  # previous spline point
							new_point = psp + pp
							new_point = (new_point[0], new_point[1], new_point[2], 1.0)
							spline_points[k].co = new_point

						spline.type = 'POLY'

						curve_obj = bpy.data.objects.new(name, curve)
						col_sub.objects.link(curve_obj)

						curve_obj.ssx2_CurveMode = 'PATH_EVENT'
						# curve_obj.ssx2_PathProps.reset = path_respawn
						# curve_obj.ssx2_PathProps.start = True if j in start_paths else False
						curve_obj.ssx2_PathProps.eventpaths_u2 = path_unk2

						events = curve_obj.ssx2_PathProps.events
						for k, event in enumerate(path_events):
							new_event = events.add()
							#new_event.name = f"Event {k + 1}"#{len(events):03}"
							new_event.u0 = event["EventType"]
							new_event.u1 = event["EventValue"]
							new_event.u2 = event["EventStart"] / 100
							new_event.u3 = event["EventEnd"] / 100

						node_modifier = curve_obj.modifiers.new(name="GeoNodes", type='NODES')
						node_modifier.node_group = node_tree


					else:
						empty = bpy.data.objects.new(name, None) #collec_main.objects.link(empty)
						empty.empty_display_size = 100 / 100 # WorldScale
						empty.empty_display_type = 'CUBE'
						empty.location = path_pos

						empty.ssx2_EmptyMode = 'PATH_EVENT'
						# empty.ssx2_PathProps.mode = 'EVENT'
						# empty.ssx2_PathProps.reset = path_respawn
						# empty.ssx2_PathProps.start = True if j in start_paths else False
						empty.ssx2_PathProps.eventpaths_u2 = path_unk2

						events = empty.ssx2_PathProps.events
						for k, event in enumerate(path_events):
							new_event = events.add()
							#new_event.name = f"Event {k + 1}"#{len(events):03}"
							new_event.u0 = event["EventType"]
							new_event.u1 = event["EventValue"]
							new_event.u2 = event["EventStart"] / 100
							new_event.u3 = event["EventEnd"] / 100

						col_sub.objects.link(empty)

						parent_obj = empty

						for k, point in enumerate(path_points):
							name = f"{obj_main_name}_Events.{j}.{k}"
							empty = bpy.data.objects.new(name, None)
							empty.empty_display_size = 100 / 100 # WorldScale
							# empty.empty_display_type = 'CUBE'
							empty.location = Vector(point) / 100 # WorldScale
							empty.parent = parent_obj

							col_sub.objects.link(empty)

							parent_obj = empty

				#break # only general

		if io.importSplines: # <------------------------------- Import Splines
			print("Importing Splines")

			def opposite_point_co(middle, second):
				# mx,my,mz = middle
				# sx,sy,sz = second

				# subtracted = Vector((sx - mx, .......))

				return middle + (-(second - middle)) # current point + vector to second

			collection = bpy.data.collections.get('Splines')
			if collection is None:
				collection = bpy.data.collections.new('Splines')
				scene_collection.children.link(collection)


			file_path = folder_path + '/Splines.json'
			if not os.path.isfile(file_path):
				self.report({'ERROR'}, f"File 'Splines.json' does not exist in 'Import Folder'")
				return {'CANCELLED'}

			with open(file_path, 'r') as f:
				data = json.load(f)

				for i, json_spline in enumerate(data["Splines"]):

					print("\nSpline", i, json_spline["SplineName"])
					
					merged_points = []
					for j, segment in enumerate(json_spline["Segments"]):
						print("seg")

						for k in range(3):
							x,y,z = segment["Points"][k]
							merged_points.append((x/100, y/100, z/100))
							print((x/100, y/100, z/100))

						# 	x,y,z = segment["Points"][k]
						# 	if io.splineImportAsNURBS:
						# 		merged_points.append((x/100, y/100, z/100, 1.0))
						# 	else:
						# 		merged_points.append((x/100, y/100, z/100))

					last = json_spline["Segments"][-1]["Points"][3]
					merged_points.append((last[0] / 100, last[1] / 100, last[2] / 100))

					len_merged_points = len(merged_points)

					name = json_spline["SplineName"]
					# curve = bpy.data.curves.get(name)
					# if curve is None:
					# 	curve = bpy.data.curves.new(name, 'CURVE')

					curve = bpy.data.curves.new(name, 'CURVE')
					curve.dimensions = '3D'

					if io.splineImportAsNURBS: 			# NURBS Spline Curve

						spline = curve.splines.new(type='NURBS')
						points_to_add = len_merged_points-1

						if len(spline.points)-1 == points_to_add:
							self.report({'WARN'}, "AHHHHHHHHHHHHHHHHH")
							pass
						else:
							spline.points.add(points_to_add)

						for j, point in enumerate(spline.points):
							point.co = merged_points[j]

						spline.use_endpoint_u = True
						spline.use_bezier_u = True
						spline.order_u = 4
						spline.resolution_u = 12

						curve_obj = bpy.data.objects.new(name, curve)
						curve_obj.ssx2_CurveMode = "SPLINE"
						curve_obj.ssx2_SplineProps.type = json_spline["SplineStyle"]
						collection.objects.link(curve_obj)

					else:										# Bézier Spline Curve
						new_bezier_points = []
						for j in range(0, len_merged_points, 3):
							point_curr = Vector(merged_points[j]) # Current Point

							pt = {'co': point_curr,
								   'left_co': None,
								   'right_co': None,
								   'left_type': 'FREE',
								   'right_type': 'FREE'}

							if j != 0:									# Previous Point
								point_prev = Vector(merged_points[j-1])

							if j+1 != len_merged_points:					# Next Point
								point_next = Vector(merged_points[j+1])
								pt['right_co'] = point_next

							if j+1 == len_merged_points:					# Final Point
								pt['right_co'] = opposite_point_co(point_curr, point_prev)
								pt['left_co'] = point_prev

								if point_prev == point_curr:
									pass # type = 'FREE'
								else:
									pt['right_type'] = 'ALIGNED'
									pt['left_type'] = 'ALIGNED'

							if j == 0:											# First Point
								pt['left_co'] = opposite_point_co(point_curr, point_next)
								pt['right_type'] = 'ALIGNED'
								pt['left_type'] = 'ALIGNED'

							if (j != 0) and (j+1 != len_merged_points): # Middle Points
								point_prev = Vector(merged_points[j-1])
								point_next = Vector(merged_points[j+1])

								# pt['right_type'] = 'ALIGNED'
								# pt['left_type'] = 'ALIGNED'
								pt['right_type'] = 'FREE'
								pt['left_type'] = 'FREE'
								
								pt['right_co'] = point_next
								pt['left_co'] = point_prev

							# print("	left", pt['left_co'])
							# print("	curr", pt['co'])
							# print("	right", pt['right_co'])

							new_bezier_points.append(pt)
							
						spline = curve.splines.new(type='BEZIER')
						spline.bezier_points.add(len(new_bezier_points)-1)
						
						for j, bez_point in enumerate(new_bezier_points):
							point = spline.bezier_points[j]

							point.co = bez_point['co']
							point.handle_left = bez_point['left_co']
							point.handle_right = bez_point['right_co']
							point.handle_left_type  = bez_point['left_type']	#'FREE'
							point.handle_right_type = bez_point['right_type']	#'FREE'

						curve_obj = bpy.data.objects.new(name, curve)
						curve_obj.ssx2_CurveMode = "SPLINE"
						curve_obj.ssx2_SplineProps.type = str(json_spline["SplineStyle"])

						collection.objects.link(curve_obj)

			# SELECT ALL AT THE END AND SET ORIGIN
			#bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

	def execute(self, context):
		
		WORLD_IMPORT_TIME_START = time.time()
		if bpy.context.mode != 'OBJECT':
			bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

		s = context.scene

		if s.bx_PlatformChoice != 'ICE':
			project_mode = "BINARY"
			if s.bx_PlatformChoice == 'PS2':
				main_ext = '.pbd'
			elif s.bx_PlatformChoice == 'XBX':
				main_ext = '.xbd'
			elif s.bx_PlatformChoice == 'NGC':
				main_ext = '.nbd'
		else:
			project_mode = "JSON"

			test = self.import_json()

			self.report({'INFO'}, "Imported")

		
		bpy.data.materials.remove(self.appended_material)

		return {'FINISHED'}




		#project_mode = s.ssx2_WorldProjectMode
		io = s.ssx2_WorldImportExportProps
		use_names = io.importNames
		import_textures = io.importTextures

		path = s.ssx2_WorldImportExportProps.importFolderPath
		path = os.path.abspath(bpy.path.abspath(path))
		if not os.path.exists(path): #.isdir
			self.report({'ERROR'}, f"Import Folder does not exist")
			return {'CANCELLED'}

		if s.ssx2_WorldImportExportProps.worldChoice == 'CUSTOM':
			file = s.ssx2_WorldImportExportProps.worldChoiceCustom
		else:
			file = s.ssx2_WorldImportExportProps.worldChoice

		if use_names and project_mode == 'BINARY':
			if not os.path.isfile(path+'/'+file+'.map'):
				self.report({'ERROR'}, f"Cannot find .map info file for 'Import Names'")
				return {'CANCELLED'}
			map_info = ssx2_get_map_info(path+'/'+file+'.map')
		elif use_names and project_mode == 'JSON':
			use_names = False
		else:
			map_info = {}

		if import_textures:
			print("Importing Textures")
			images = []

			tmp_tex_path = None
			if os.path.isdir(path+f"/{file}_xsh/"):
				tmp_tex_path = path+f"/{file}_xsh/"
			elif os.path.isdir(path+f"/{file}_textures/"):
				tmp_tex_path = path+f"/{file}_textures/"
			elif os.path.isdir(path+"/textures/"):
				tmp_tex_path = path+"/textures/"

			if tmp_tex_path is not None:
				print("Textures found")
				tex_folder_contents = []
				tex_names_sorting = []

				contents = os.listdir(tmp_tex_path)
				tmp_tex_path = tmp_tex_path+"/"
				if project_mode == 'BINARY':
					for i, item in enumerate(contents):
						if os.path.isfile(tmp_tex_path+item):
							if item[-4:len(item)] == '.png':
								tex_folder_contents.append(item)
								sort_name = item[0:-4].lstrip('.')
								sort_name = '0' * (3 - len(sort_name)) + sort_name
								tex_names_sorting.append(sort_name)
						if i == 400:
							print("too many textures?")
							break

					tex_folder_contents = [x for _, x in sorted(zip(tex_names_sorting, tex_folder_contents))]

					if len(tex_folder_contents) == 0:
						print("NO TEXTURES FOUND")#try_sh = True
						pass
					else:
						for i, img_file in enumerate(tex_folder_contents):
							new_name = str(i)
							new_name = '0' * (3 - len(new_name)) + new_name
							new_name = file + '.' + new_name

							img = bpy.data.images.get(new_name)
							if img is None:
								img = bpy.data.images.load(tmp_tex_path+img_file, check_existing=False)
								img.name = new_name
							images.append(img)

				elif project_mode == 'JSON':
					for i, item in enumerate(contents):
						if item[-4:len(item)] == '.png':
							#tex_folder_contents.append(item)
							img = bpy.data.images.get(item)
							if img is None:
								img = bpy.data.images.load(tmp_tex_path+item, check_existing=False)
							images.append(img)

			elif tmp_tex_path is None and import_textures and s.bx_PlatformChoice == 'XBX': # TRY SH
				print("'textures' folder not found. Attempting to import from sh file.")
				sh_path = f"{path}/{file}.xsh"
				tex_short_names, textures_pixels, tex_widths_heights = ssx2_get_xsh_texture(sh_path)#path+'/'+file+'.xsh')
				for i in range(len(tex_short_names)):
					if i == 1:
						pass#return {'CANCELLED'}
					new_name = str(i)
					new_name = '0' * (3 - len(new_name)) + new_name
					new_name = file + '.' + new_name
					width, height = tex_widths_heights[i]
					img = bpy.data.images.get(new_name)
					if img is None:
						img = bpy.data.images.new(new_name, width, height)
						img.name = new_name
						img.pixels = textures_pixels[i]
					images.append(img)
			else:
				print("Error when importing SSX textures")
				pass

			texture_names_found = False
			if use_names:
				if map_info.get('TEXTURES') is not None:
					if len(map_info['TEXTURES']) != 0:
						texture_names = [entry[0] for entry in map_info['TEXTURES']]
						texture_names_found = True
				if texture_names_found == False:
					print("Names for textures not found. Using numbered format.")
		else:
			images = []
		
		if io.importPatches:
			if project_mode == 'BINARY':
				pbd_file_path = path+'/'+file+main_ext
				if not os.path.isfile(pbd_file_path):
					self.report({'ERROR'}, f"Failed to find patch file '{file}{main_ext}'")
					return {'CANCELLED'}
				create_imported_patches(self, context, pbd_file_path, images, map_info)
			elif project_mode == 'JSON':
				patches_json_path = path+'/Patches.json'
				if not os.path.isfile(patches_json_path):
					self.report({'ERROR'}, "Failed to find patch file 'Patches.json'")
					return {'CANCELLED'}
				create_imported_patches(self, context, patches_json_path, images)

		print("Time taken:", time.time() - WORLD_IMPORT_TIME_START, "seconds")
		self.report({'INFO'}, "Finished!")
		return {'FINISHED'}



## Panels

class SSX2_WorldPanel(SSX2_Panel):
	bl_idname = 'SSX2_PT_world'
	bl_label = 'Worlds'
	#bl_category =  'SSX Tricky'
	#bl_space_type = 'VIEW_3D'
	#bl_region_type = 'UI'

	@classmethod
	def poll(self, context):
		return context.scene.bx_GameChoice == 'SSX2'

	def draw(self, context):
		col = self.layout.column()
		col.scale_y = 1.0
		prop_split(col, context.scene, "bx_WorldScale", "World Scale")
		#prop_enum_horizontal(col, context.scene, "ssx2_WorldProjectMode", "Project Mode")

		io = context.scene.ssx2_WorldImportExportProps
		# if context.scene.ssx2_WorldProjectMode == 'BINARY':
		if context.scene.bx_PlatformChoice != 'ICE':
			prop_split(col, io, 'worldChoice', "World Choice")
			if io.worldChoice == 'CUSTOM':
				prop_split(col, io, 'worldChoiceCustom', 'Custom Choice')

class SSX2_WorldToolsPanel(SSX2_Panel): # (SSX2_WorldPanel)
	bl_idname = 'SSX2_PT_world_tools'
	bl_label = 'World Tools'
	#bl_category =  'SSX Tricky'
	#bl_space_type = 'VIEW_3D'
	#bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}
	bl_parent_id = 'SSX2_PT_world'

	@classmethod
	def poll(self, context):
		return True

	def draw(self, context):
		col = self.layout.column()
		ui_props = bpy.context.scene.ssx2_WorldUIProps


		# inst_row = col.row() # INSTANCES
		# inst_row.prop(context.scene, 'ssx2_ModelForAddInstance', text='')
		# inst_row.operator(SSX2_OP_AddInstance.bl_idname, icon='ADD')
		
		# if bpy.data.collections.get('Patches') is None:
		# 	col.operator(SSX2_OP_WorldInitiateProject.bl_idname, icon='ADD')
		col.operator(SSX2_OP_WorldInitiateProject.bl_idname, icon='ADD')

		spline_box = col.box()    # SPLINES
		spline_box.label(text="Splines")
		spl_box_row = spline_box.row()
		#spl_box_row.operator(SSX2_OP_AddSplineNURBS.bl_idname, icon='ADD')
		spl_box_row.operator(SSX2_OP_AddSplineBezier.bl_idname, icon='ADD')


		patch_box = col.box()    # PATCHES
		#patch_box.scale_y = 0.8
		pch_box_col = patch_box.column()
		pch_header_row = pch_box_col.row(align=True)
		a = pch_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if ui_props.expandToolsPatches\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="Patches").prop = 'ssx2_WorldUIProps.expandToolsPatches'

		if ui_props.expandToolsPatches:
			patch_box_row = patch_box.row()
			# patch_box_row.prop(context.scene.ssx2_WorldUIProps, 'patchMaterialChoice', text='')
			# patch_box_row.prop(context.scene.ssx2_WorldUIProps, 'patchTypeChoice', text='')
			patch_box_row.operator(SSX2_OP_AddPatch.bl_idname, icon='ADD')
			patch_box_row.operator(SSX2_OP_AddControlGrid.bl_idname, icon='ADD')
			
			obj = bpy.context.active_object
			if obj is not None:
				if obj.type == 'SURFACE':
					patch_box.operator(SSX2_OP_ToggleControlGrid.bl_idname, text="To Control Grid")
				elif obj.ssx2_PatchProps.isControlGrid:
					patch_box.operator(SSX2_OP_ToggleControlGrid.bl_idname, text="To Patch")
				else:
					patch_box.operator(SSX2_OP_ToggleControlGrid.bl_idname)
			else:
				patch_box.operator(SSX2_OP_ToggleControlGrid.bl_idname)

			patch_box.operator(SSX2_OP_PatchSplit4x4.bl_idname, text="Split to 4x4")

			#patch_box.label(text="Spline Cage")
			patch_box_row2 = patch_box.row()
			patch_box_row2.operator(SSX2_OP_AddSplineCage.bl_idname, icon='ADD')
			patch_box_row2.operator(SSX2_OP_CageToPatch.bl_idname, text="Patch from Cage")
			patch_box_row3 = patch_box.row()
			patch_box_row3.operator(SSX2_OP_FlipSplineOrder.bl_idname, text="Flip Spline Order")
			patch_box_row3.operator("curve.switch_direction", text="Switch Direction")
			patch_box.operator(SSX2_OP_SelectSplineCageV.bl_idname, text="Select Along V")
			
			prop_split(patch_box, context.scene.ssx2_WorldUIProps, 'patchSelectByType', "Select by Type")

		path_box = col.box()
		path_box.label(text="Paths")
		path_box_row = path_box.row()
		path_box_row.operator(SSX2_OP_AddPath.bl_idname, text="Path", icon='ADD')
		path_box_row.operator(SSX2_OP_AddPathChild.bl_idname, text="Child Node", icon='ADD')
		


class SSX2_WorldImportPanel(SSX2_Panel):
	bl_idname = 'SSX2_PT_world_import'
	bl_label = 'World Import'
	bl_options = {'DEFAULT_CLOSED'}
	bl_parent_id = 'SSX2_PT_world'

	# @classmethod
	# def poll(self, context):
	# 	return True

	def draw(self, context):
		io = context.scene.ssx2_WorldImportExportProps
		col = self.layout.column()
		prop_split(col, io, 'importFolderPath', "Import Folder", spacing=0.4)

		# if context.scene.ssx2_WorldProjectMode == 'BINARY':
		if context.scene.bx_PlatformChoice != 'ICE':
			col_row = col.row()
			col_row.prop(io, "importNames")
			col_row.prop(io, "importTextures")

		# SPLINES
		splines_box = col.box()
		spl_box_col = splines_box.column()
		spl_header_row = spl_box_col.row(align=True)
		spl_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if io.expandImportSplines\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportSplines'
		spl_header_row.prop(io, "importSplines", text="Splines")
		# if io.expandImportSplines:
		# 	spl_box_col.prop(io, "splineImportAsNURBS", text="As NURBS")
			#prop_enum_horizontal(spl_box_col, io, 'patchImportGrouping', "Grouping", spacing=0.3)

		# PATCHES
		patches_box = col.box()
		pch_col_box = patches_box.column()
		pch_header_row = pch_col_box.row(align=True)
		pch_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if io.expandImportPatches\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportPatches'
		pch_header_row.prop(io, "importPatches", text="Patches")
		#pch_header_row.prop(io, "patchImportAsControlGrid", text="As Control Grid")
		if io.expandImportPatches:
			pch_col_box.prop(io, "patchImportAsControlGrid", text="As Control Grid")
			prop_enum_horizontal(pch_col_box, io, 'patchImportGrouping', "Grouping", spacing=0.3)
		
		# PATHS
		paths_box = col.box()
		pth_col_box = paths_box.column()
		pth_header_row = pth_col_box.row(align=True)
		pth_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if io.expandImportPaths\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportPaths'
		pth_header_row.prop(io, "importPaths", text="Paths")
		if io.expandImportPaths:
			pth_col_box.prop(io, "importPathsAsCurve", text="As Poly Curve")

		# IMPORT BUTTON
		col.operator(SSX2_OP_WorldImport.bl_idname)


class SSX2_WorldExportPanel(SSX2_Panel):
	bl_idname = 'SSX2_PT_world_export'
	bl_label = 'World Export'
	bl_options = {'DEFAULT_CLOSED'}
	bl_parent_id = 'SSX2_PT_world'

	# @classmethod
	# def poll(self, context): # entire panel, not button
	# 	return True

	def draw(self, context):
		io = context.scene.ssx2_WorldImportExportProps
		col = self.layout.column()
		prop_split(col, io, 'exportFolderPath', 'Export Folder', spacing=0.4)
		patches_row = col.row()
		patches_row.prop(io, "exportPatches", text="Patches")
		patches_row.prop(io, "exportPatchesCages", text="Cages") #exportPatchesOverride

		splines_row = col.row()
		splines_row.prop(io, "exportSplines", text="Splines")
		splines_row.prop(io, "exportSplinesOverride", text="Override")
		paths_row = col.row(align=True)

		paths_row_split = paths_row.split(factor=0.2)

		paths_row_split.label(text="Paths")
		paths_row_split.prop(io, "exportPathsGeneral", text="General")
		paths_row_split.prop(io, "exportPathsShowoff", text="Showoff")

		col.operator(SSX2_OP_WorldExport.bl_idname)



class SSX2_WorldMaterialPanel(bpy.types.Panel):
	bl_label = "Test"
	bl_idname = "MATERIAL_PT_SSX2_material"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = "material"
	bl_options = {"HIDE_HEADER"}
	
	def draw(self, context):
		obj = context.object

		layout = self.layout
		row = layout.row()
		row.operator(SSX2_OP_AddPatchMaterial.bl_idname, text="New Patch Material", icon='ADD')

		if obj.ssx2_CurveMode == 'CAGE':
			row.operator(SSX2_OP_SendMaterialToModifier.bl_idname, text="Send to Modifier")



def poll_wmodel_for_inst(self, context):
	if context.type == 'MESH' and context.parent == None:# or just context.type == 'MESH':
		return True
	else:
		return False

def update_wmodel_for_inst(self, context):
	mdl = self.ssx2_ModelForInstance

	if mdl == None:
		print("No model specified.")
		self.instance_collection = None
		self.show_instancer_for_viewport = True
	else:
		mdlinst = getset_instance_collection(mdl, f"ins_{mdl.name}")
		self.instance_type = 'COLLECTION' # the context.object.ssx2_wModel method will take care of this
		self.instance_collection = bpy.data.collections.get(mdlinst)
		#self.show_instancer_for_viewport = False
		#print(self.ssx2_ModelForInstance)
				

classes = (
	SSX2_WorldImportExportPropGroup,
	SSX2_WorldUIPropGroup,
	SSX2_WorldSplinePropGroup,
	SSX2_WorldPathEventPropGroup,
	SSX2_WorldPathPropGroup,

	SSX2_OP_BakeTest,
	SSX2_OP_SelectSplineCageV,

	SSX2_OP_AddSplineBezier,
	SSX2_OP_AddSplineNURBS,
	SSX2_OP_AddInstance,
	SSX2_OP_AddPath,
	SSX2_OP_AddPathChild,
	#SSX2_OP_BakeTest,
	SSX2_OP_WorldImport,
	SSX2_OP_WorldExport,
	SSX2_OP_WorldExpandUIBoxes,
	SSX2_OP_WorldInitiateProject,
	SSX2_WorldPathEventAdd,
	SSX2_WorldPathEventRemove,

	SSX2_WorldPanel,
	SSX2_WorldToolsPanel,
	SSX2_WorldImportPanel,
	SSX2_WorldExportPanel,
	# SSX2_WorldInstancePanel, # properties panel
	SSX2_EmptyPanel,
	# SSX2_PathPanel,
	SSX2_CurvePanel,
	SSX2_WorldMaterialPanel,

)

def ssx2_world_register():
	for c in classes:
		register_class(c)

	ssx2_world_patches_register()

	bpy.types.Scene.ssx2_WorldProjectMode = bpy.props.EnumProperty(name='Project Mode', items=enum_ssx2_world_project_mode, default='JSON')

	bpy.types.Scene.ssx2_WorldImportExportProps = bpy.props.PointerProperty(type=SSX2_WorldImportExportPropGroup)
	bpy.types.Scene.ssx2_WorldUIProps = bpy.props.PointerProperty(type=SSX2_WorldUIPropGroup)
	bpy.types.Object.ssx2_SplineProps = bpy.props.PointerProperty(type=SSX2_WorldSplinePropGroup)
	bpy.types.Object.ssx2_PathProps = bpy.props.PointerProperty(type=SSX2_WorldPathPropGroup)
	bpy.types.Object.ssx2_EmptyMode = bpy.props.EnumProperty(name='Empty Mode', items=enum_ssx2_empty_mode)
	bpy.types.Object.ssx2_CurveMode = bpy.props.EnumProperty(name='Curve Mode', items=enum_ssx2_curve_mode)

	bpy.types.Object.ssx2_ModelForInstance   = bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_wmodel_for_inst, update=update_wmodel_for_inst)
	bpy.types.Scene.ssx2_ModelForAddInstance = bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_wmodel_for_inst)


def ssx2_world_unregister():
	ssx2_world_patches_unregister()

	del bpy.types.Object.ssx2_ModelForInstance
	del bpy.types.Scene.ssx2_ModelForAddInstance

	del bpy.types.Scene.ssx2_WorldImportExportProps
	del bpy.types.Scene.ssx2_WorldUIProps
	del bpy.types.Object.ssx2_SplineProps
	del bpy.types.Object.ssx2_PathProps

	del bpy.types.Scene.ssx2_WorldProjectMode

	for c in classes:
		unregister_class(c)