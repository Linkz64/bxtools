import bpy
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Matrix
from math import ceil
from subprocess import Popen
import json
import time
import os

from ..general.blender_set_data import * # set_patch_object
from ..general.blender_get_data import get_images_from_folder, get_uvs, get_uvs_per_verts
from ..general.bx_utils import *

from .ssx2_world_io_in import get_patches_json#*
from .ssx2_world_patches import (
	patch_tex_map_equiv_uvs,
	patch_known_uvs,
	existing_patch_uvs,
)
from .ssx2_constants import (
	enum_ssx2_world_project_mode,
	enum_ssx2_world,
	enum_ssx2_patch_group,
	enum_ssx2_surface_type,
	enum_ssx2_surface_type_spline,
	enum_ssx2_surface_type_extended,
	enum_ssx2_empty_mode,
	enum_ssx2_curve_mode,
	enum_ssx2_instance_group,
)
from .ssx2_world_lightmaps import SSX2_OP_BakeTest


import re
def natural_key(s):
	return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]



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


def poll_prefab_for_inst(self, context):
	# if collection.ssx2 collection type/mode == 'PREFAB':
	return True

def update_prefab_for_inst(self, context):
	fab = self.ssx2_PrefabForInstance
	if fab:
		self.instance_type = 'COLLECTION'
		self.instance_collection = fab
	else:
		print("No prefab specified.")
		self.instance_collection = None
		self.show_instancer_for_viewport = True

def update_event_start_end(self, context):
	for mod in context.active_object.modifiers:
		if mod.type == 'NODES' and mod.node_group:
			if mod.node_group.name.startswith("PathLinesAppend"):
				if self.u3 < self.u2:
					self.u3 = self.u2

				mod["Input_4"] = self.u2
				mod["Input_5"] = self.u3
			break

### Operators

class SSX2_OP_AddInstance(bpy.types.Operator): # change this to use collection instead of model object
	bl_idname = 'object.ssx2_add_instance'
	bl_label = "Model Instance"
	bl_description = "Generate an instance"
	bl_options = {'REGISTER', 'UNDO'}

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
	bl_options = {'REGISTER', 'UNDO'}

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
			align='CURSOR')

		curve_obj = bpy.context.object
		collection_it_was_added_to = curve_obj.users_collection[0]

		curve_obj.ssx2_CurveMode = 'SPLINE'
		curve_obj.ssx2_SplineProps.type = '13'

		curve_points = curve_obj.data.splines[0].bezier_points
		curve_points[0].co = (0, 0, 0)
		curve_points[0].handle_left = (-0.5, 0, 0)
		curve_points[0].handle_right = (0.5, 0, 0)
		curve_points[1].co = (2, 0, 0)
		curve_points[1].handle_left = (1.5, 0, 0)
		curve_points[1].handle_right = (2.5, 0, 0)

		if collection_it_was_added_to.name != collection.name:
			collection_it_was_added_to.objects.unlink(curve_obj)
			collection.objects.link(curve_obj)

		return {"FINISHED"}

class SSX2_OP_AddSplineNURBS(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_spline_nurbs'
	bl_label = "NURBS Curve"
	bl_description = 'Generate a NURBS curve'
	bl_options = {'REGISTER', 'UNDO'}

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

class SSX2_OP_AddPath(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_path'
	bl_label = "Add Path"
	bl_description = 'Generate a path'
	bl_options = {'REGISTER', 'UNDO'}

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

			curve_obj.ssx2_CurveMode = 'PATH_AI'


		return {"FINISHED"}

class SSX2_OP_AddPathChild(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_path_child'
	bl_label = "Add Path Child"
	bl_description = 'Generate a child node for the active node'
	bl_options = {'REGISTER', 'UNDO'}

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

class SSX2_OP_PathEventAdd(bpy.types.Operator):
	bl_idname = "object.ssx2_add_path_event"
	bl_label = "Add Event"

	def execute(self, context):
		obj = bpy.context.active_object
		events = obj.ssx2_PathProps.events
		new_event = events.add()
		#new_event.name = f"Event {len(events)}"#{len(events):03}"
		return {'FINISHED'}

class SSX2_OP_PathEventRemove(bpy.types.Operator):
	bl_idname = "object.ssx2_remove_path_event"
	bl_label = "Remove Event"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		obj = bpy.context.active_object 
		events = obj.ssx2_PathProps.events
		at_least_one_checked = False

		new_list = []

		for event in events:
			if event.checked == False:
				new_list.append((
					event.u0, 
					event.u1, 
					event.u2, 
					event.u3,
					event.checked))
			else:
				at_least_one_checked = True

		if not at_least_one_checked:
			return {'CANCELLED'}

		events.clear()

		for val in new_list:
			new_event = events.add()
			new_event.u0 = val[0]
			new_event.u1 = val[1]
			new_event.u2 = val[2]
			new_event.u3 = val[3]
			new_event.checked = val[4]

		return {'FINISHED'}

class SSX2_OP_WorldInitiateProject(bpy.types.Operator):
	bl_idname = "scene.ssx2_world_initiate_project"
	bl_label = "Initiate Project"
	bl_description = "Create project collections and set recommended view settings"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		scene = bpy.context.scene
		scene_collection = scene.collection

		for screen in bpy.data.screens:
			for area in screen.areas:
				if area.type == "OUTLINER":
					for space in area.spaces:
						if space.type == 'OUTLINER':
							space.show_restrict_column_render = False
							space.show_restrict_column_select = True

				elif area.type == "VIEW_3D":
					for space in area.spaces:
						if space.type == 'VIEW_3D':
							space.clip_start = 0.5
							space.clip_end = 2000
							space.overlay.display_handle = 'ALL'

		getset_collection_to_target("Patches", scene_collection)
		getset_collection_to_target("Splines", scene_collection)
		getset_collection_to_target("Paths", scene_collection)

		return {'FINISHED'}

class SSX2_OP_WorldReloadNodeTrees(bpy.types.Operator):
	bl_idname = "scene.ssx2_world_reload_node_trees"
	bl_label = "Reload Node Trees"
	bl_description = "Reloads geometry nodes and material nodes from templates.blend"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		warn = False

		cage_loft_appends = []
		grid_tesselate_appends = []
		path_line_appends = []

		mat_reapply_general = []
		mat_reapply_spline_cage = []
		mat_names = []
		mat_textures = []

		for obj in bpy.data.objects:
			
			tex = None
			if (obj.type == 'MESH' and obj.ssx2_PatchProps.isControlGrid) or obj.type == 'SURFACE':
				if len(obj.material_slots) != 0:
					mat = obj.material_slots[0].material
					if mat is not None:
						tex_node = mat.node_tree.nodes.get("Image Texture")
						if tex_node:
							tex = tex_node.image

						if mat.name in mat_names:
							mat_reapply_general.append((obj, mat_names.index(mat.name)))
						else:
							mat_reapply_general.append((obj, len(mat_names)))
							mat_names.append(mat.name)
							mat_textures.append(tex)

			if obj.type != 'MESH' and obj.type != 'CURVE':
				continue

			for j, mod in enumerate(obj.modifiers):
				if mod.type == 'NODES' and mod.node_group:
					if mod.node_group.name.startswith("CageLoftAppend"):
						mod_options = (
							mod["Input_3"], # -loft
							mod["Input_2"], # -ends only
							mod["Input_5"], # -hexa middle
							mod["Input_6"], # -double v
							mod["Input_4"], # -auto smooth
							mod["Input_7"], # -material
						)
						mat = mod["Input_7"]
						if mat is not None:
							tex_node = mat.node_tree.nodes.get("Image Texture")
							if tex_node:
								tex = tex_node.image
							
							if mat.name in mat_names:
								mat_reapply_spline_cage.append((obj, mat_names.index(mat.name), j))
							else:
								mat_reapply_spline_cage.append((obj, len(mat_names), j))
								mat_names.append(mat.name)
								mat_textures.append(tex)

						cage_loft_appends.append((obj, j, mod_options))
						break
					elif mod.node_group.name.startswith("GridTesselateAppend"):
						grid_tesselate_appends.append((obj, j))
						break
					elif mod.node_group.name.startswith("PathLinesAppend"):
						path_line_appends.append((obj, j))
						break

		### Geonodes
		
		if len(cage_loft_appends) != 0:
			for node_group in bpy.data.node_groups:
				if node_group.name.startswith("CageLoftAppend"):
					bpy.data.node_groups.remove(node_group)
				elif node_group.name.startswith("CageLoftGroupA"):
					bpy.data.node_groups.remove(node_group)

			node_tree = append_geonodes("CageLoftAppend")
			if node_tree is not None:
				for item in cage_loft_appends:
					obj = item[0]
					mod = obj.modifiers[item[1]]
					mod.node_group = node_tree

					mod["Input_3"] = item[2][0]
					mod["Input_2"] = item[2][1]
					mod["Input_5"] = item[2][2]
					mod["Input_6"] = item[2][3]
					mod["Input_4"] = item[2][4]
					mod["Input_7"] = item[2][5]
			else:
				warn = True

		if len(grid_tesselate_appends) != 0:
			for node_group in bpy.data.node_groups:
				if node_group.name.startswith("GridTesselateAppend"):
					bpy.data.node_groups.remove(node_group)
				elif node_group.name.startswith("CageLoftGroupB"):
					bpy.data.node_groups.remove(node_group)
				elif node_group.name.startswith("BezierColumnsGroup"):
					bpy.data.node_groups.remove(node_group)
			
			node_tree = append_geonodes("GridTesselateAppend")
			if node_tree is not None:
				for item in grid_tesselate_appends:
					obj = item[0]
					obj.modifiers[item[1]].node_group = node_tree
			else:
				warn = True

		if len(path_line_appends) != 0:
			for node_group in bpy.data.node_groups:
				if node_group.name.startswith("PathLinesAppend"):
					bpy.data.node_groups.remove(node_group)
				
			node_tree = append_geonodes("PathLinesAppend")
			if node_tree is not None:
				for item in path_line_appends:
					obj = item[0]
					obj.modifiers[item[1]].node_group = node_tree
			else:
				warn = True


		### Materials

		mats_new = []

		if len(mat_names) != 0:
			mat = bpy.data.materials.get("PatchMaterialAppend")
			if mat is not None:
				bpy.data.materials.remove(mat)

			for mat_name in mat_names:
				bpy.data.materials.remove(bpy.data.materials.get(mat_name))

			mat_append = append_material("PatchMaterialAppend")

			for i, mat_name in enumerate(mat_names):
				mat = mat_append.copy()
				mat.name = mat_name

				mat.node_tree.nodes["Image Texture"].image = mat_textures[i]
				mats_new.append(mat)

		mat = bpy.data.materials.get("PatchMaterialAppend")
		if mat is not None:
			bpy.data.materials.remove(mat)

		if len(mat_reapply_general) != 0:
			for item in mat_reapply_general:
				obj = item[0]
				obj.material_slots[0].material = mats_new[item[1]]

		if len(mat_reapply_spline_cage) != 0:
			for item in mat_reapply_spline_cage:
				obj = item[0]
				mod = obj.modifiers[item[2]]
				mod["Input_7"] = mats_new[item[1]]
				obj.data.materials.clear()
				obj.data.materials.append(mod["Input_7"])

		if warn:
			BXT.warn(f"Failed to append nodes from {templates_append_path}")
		else:
			BXT.info(self, "Reloaded Node Trees")
		

		return {'FINISHED'}

class SSX2_OP_WorldImport(bpy.types.Operator):
	bl_idname = "wm.ssx2_import_world"
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
			io.importPaths or \
			io.importPrefabs\
			) and \
			(s.bx_PlatformChoice == 'XBX' or s.bx_PlatformChoice == 'NGC' or\
			s.bx_PlatformChoice == 'PS2' or s.bx_PlatformChoice == 'ICE')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.json_patches = []
		self.images = []

		self.scene_collection = None
		self.io = None

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

	def create_prefabs_json(self):
		scene_collection = bpy.context.scene.collection
		active_collection = bpy.context.collection
		io = bpy.context.scene.ssx2_WorldImportExportProps

		models_folder_path = self.folder_path + '/Models/'
		if not os.path.exists(models_folder_path):
			self.report({'ERROR'}, f"Folder 'Models' does not exist in 'Import Folder'")
			return {'CANCELLED'}

		prefabs_file_path = self.folder_path + '/Prefabs.json'
		if not os.path.isfile(prefabs_file_path):
			self.report({'ERROR'}, f"File 'Prefabs.json' does not exist in 'Import Folder'")
			return {'CANCELLED'}

		instances_file_path = self.folder_path + '/Instances.json'
		if not os.path.isfile(instances_file_path):
			self.report({'ERROR'}, f"File 'Instances.json' does not exist in 'Import Folder'")
			return {'CANCELLED'}
		
		prefabs_collection = getset_collection_to_target('Prefabs', scene_collection)
		instances_collection = getset_collection_to_target('Instances', scene_collection)

		
		fab_group_mode = 0 # 0:batch 1:names
		fab_group_size = 400 # make it a scene prop?
		inst_group_size = 500

		# name_grouping_test = []

		### Import Prefabs
		print("\nParsing Prefabs")

		meshes_to_merge = []
		materials_to_import = []

		with open(prefabs_file_path, 'r') as f:
			data = json.load(f)

		prefab_collections = []

		for i, json_fab in enumerate(data["Prefabs"]):
			fab_name = json_fab["PrefabName"]
			# print(fab_name, "sub_objs:", len(json_fab["PrefabObjects"]))

			fab_collection = bpy.data.collections.new(fab_name)
			#prefabs_collection.children.link(fab_collection)

			if fab_group_mode == 0:
				new_group_col = collection_grouping(f"Prefab_Group", prefabs_collection, fab_group_size, i)
				new_group_col.children.link(fab_collection)
			else:
				new_group_name = "Prefab " + ''.join([char for char in fab_name if not char.isdigit()])
				new_group_name = new_group_name[:-1] if new_group_name.endswith('_') else new_group_name
				#print(new_group_name)
				new_group_col = getset_collection(new_group_name)
				new_group_col.children.link(fab_collection)

				if not bpy.context.scene.user_of_id(new_group_col): # if not in scene/layer bring it
					prefabs_collection.children.link(new_group_col)

			fab_collection.ssx2_PrefabCollectionProps.unknown3 = json_fab["Unknown3"]
			fab_collection.ssx2_PrefabCollectionProps.anim_time = json_fab["AnimTime"]

			sub_objs = []

			for j, sub_obj in enumerate(json_fab["PrefabObjects"]):
				primary_mesh = ""
				# primary_mesh_index = -1
				if sub_obj["MeshData"]:
					primary_mesh = sub_obj["MeshData"][0]["MeshPath"]
					# primary_mesh_index = sub_obj["MeshData"][0]["MeshID"]

				sub_obj_dict = {
					"parent_idx": sub_obj["ParentID"],
					"flags": sub_obj["Flags"],
					"animation": sub_obj["Animation"],
					"primary_mesh": primary_mesh,
					# "primary_mesh_index": primary_mesh_index,
					"position": sub_obj["Position"],
					"rotation": sub_obj["Rotation"],
					"scale": sub_obj["Scale"],
					"include_animation": sub_obj["IncludeAnimation"],
					"include_matrix": sub_obj["IncludeMatrix"],
				}

				to_merge = []
				for mesh_data in sub_obj["MeshData"]:
					to_merge.append((mesh_data["MeshPath"], mesh_data["MeshID"], mesh_data["MaterialID"]))

					if mesh_data["MaterialID"] not in materials_to_import:
						materials_to_import.append(mesh_data["MaterialID"])
				meshes_to_merge.append(to_merge)

				sub_objs.append(sub_obj_dict)

				# meshes_to_merge.append([(m["MeshPath"], m["MaterialID"]) for m in sub_obj["MeshData"]])

			# if i == 250:
			# 	break
			
			prefab_collections.append((fab_collection, sub_objs))


		#return ""


		



		# i could apply placeholder materials/material_slots first
		# material
		# unknown int 18
		# unk_18 & 0xFFFF for first 2 bytes
		# unk_18 >> 16 for the last 2 bytes
		# for mat in materials_to_import:
		# 	print(mat)


		new_global_scale = 1 / 100 # WorldScale

		print("\nImporting .obj files")

		obj_file_import_mode = 1

		if obj_file_import_mode == 0:

			import_obj_files_time_start = time.time()

			# obj_files = next(os.walk(models_folder_path))[2]
			# len(obj_files) == 0: ERROR!!!

			bpy.ops.object.select_all(action='DESELECT')
			view_layer = bpy.context.view_layer
			view_layer.active_layer_collection = view_layer.layer_collection # "Scene Collection"

			# obj_file_paths = [models_folder_path + pth for pth in next(os.walk(models_folder_path))[2]]
			obj_files = next(os.walk(models_folder_path))[2]
			obj_files = sorted(obj_files, key=natural_key)
			new_obj_objects = []
			for path in obj_files:
				bpy.ops.wm.obj_import(filepath=models_folder_path + path, global_scale=new_global_scale)
				new_obj = bpy.context.view_layer.objects.active
				new_obj_objects.append(new_obj)

			print("importing .obj files took", import_obj_files_time_start - time.time())

			[obj.select_set(True) for obj in new_obj_objects]
			# bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
			bpy.ops.object.rotation_clear()
			bpy.ops.object.transform_apply(location=False)
			bpy.ops.object.select_all(action='DESELECT')
			

			already_merged = []

			for mesh_data in meshes_to_merge:
				if not mesh_data:
					continue
				
				primary_mesh = mesh_data[0][0]
				new_obj_name = primary_mesh[:-4]

				# existing_object = bpy.data.objects.get(new_obj_name)
				# if existing_object is not None:
				# 	if existing_object.type == 'MESH':
				# 		continue

				if new_obj_name in already_merged:
					continue
				
				if len(mesh_data) != 1:
					objs_to_merge = [new_obj_objects[mesh_path[1]] for mesh_path in mesh_data]
					bpy.context.view_layer.objects.active = objs_to_merge[0]
					[obj.select_set(True) for obj in objs_to_merge]
					bpy.ops.object.join()
					new_obj = bpy.context.view_layer.objects.active
				else:
					#bpy.context.view_layer.objects.active = new_obj_objects[mesh_data[0][1]]
					new_obj = new_obj_objects[mesh_data[0][1]]

				new_obj.name = new_obj_name
				new_obj.data.name = new_obj_name

				# print(new_obj.name, new_obj_name)
				if new_obj.name != new_obj_name:
					print("OH OH")
					return ""

				scene_collection.objects.unlink(new_obj)

				already_merged.append(new_obj_name)

		elif obj_file_import_mode == 1:
			already_merged = []

			for mesh_data in meshes_to_merge:
				#print(mesh_data)
				if not mesh_data:
					continue
				
				primary_mesh = mesh_data[0][0]
				new_obj_name = primary_mesh[:-4]

				existing_object = bpy.data.objects.get(new_obj_name)
				if existing_object is not None:
					if existing_object.type == 'MESH':
						continue

				if new_obj_name in already_merged:
					continue

				initial_obj_count = len(bpy.data.objects)
				new_obj_count = 0

				objs_to_merge = []
				for mesh_path in mesh_data:
					bpy.ops.wm.obj_import(filepath=models_folder_path + mesh_path[0], global_scale=new_global_scale)

					new_obj = bpy.context.view_layer.objects.active
					active_collection.objects.unlink(new_obj)

					# if len(bpy.data.objects) != initial_obj_count + new_obj_count:
					# 	new_obj = bpy.context.view_layer.objects.active
					# 	active_collection.objects.unlink(new_obj)
					# 	new_obj_count += 1
					# else:
					# 	print(f"ERROR!!! Invalid .obj file {models_folder_path + mesh_path[0]}")
					# 	return "OH OH"

					objs_to_merge.append(new_obj)

					scene_collection.objects.link(new_obj)

				if len(objs_to_merge) != 1:
					bpy.context.view_layer.objects.active = objs_to_merge[0]
					# for obj in new_objs:
					# 	obj.select_set(True)
					[obj.select_set(True) for obj in objs_to_merge]
					bpy.ops.object.join()

				new_obj = bpy.context.view_layer.objects.active
				new_obj.name = new_obj_name
				new_obj.data.name = new_obj_name
				bpy.ops.object.rotation_clear()
				bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

				scene_collection.objects.unlink(new_obj)

				already_merged.append(new_obj_name)




		print("\nLinking models to prefab collections")

		root_layer_collection = bpy.context.view_layer.layer_collection

		for prefab_collection in prefab_collections:
			fab_collection = prefab_collection[0]
			
			current_new_objs = []
			for sub_obj in prefab_collection[1]:
				primary_mesh = sub_obj["primary_mesh"]

				if not primary_mesh:
					mesh = bpy.data.meshes.new("Empty Mesh")
					new_obj = bpy.data.objects.new("Empty Mesh", mesh)
					new_obj_name = new_obj.name

					new_obj.show_axis = True
					new_obj.show_texture_space = True
				else:
					new_obj_name = primary_mesh[:-4]
					new_obj = bpy.data.objects.get(new_obj_name)

				# print("   ", primary_mesh, new_obj_name, new_obj.name, fab_collection.name)

				current_new_objs.append(new_obj)

				for key in sub_obj:
					# if key in [
					# 	"position",
					# 	"rotation"]:
					# 	continue
					new_obj[key] = sub_obj[key]

				# print("parent_idx:  --- ", sub_obj["parent_idx"])
				# print("flags:  --- ", sub_obj["flags"])
				# print("animation:  --- ", sub_obj["animation"])
				# print("primary_mesh:  --- ", sub_obj["primary_mesh"])
				# print("position:  --- ", sub_obj["position"])
				# print("rotation:  --- ", sub_obj["rotation"])
				# print("scale:  --- ", sub_obj["scale"])
				# print("include_animation:  --- ", sub_obj["include_animation"])
				# print("include_matrix:  --- ", sub_obj["include_matrix"])

				new_obj.ssx2_PrefabObjectProps.flags = sub_obj["flags"]
				new_obj.ssx2_PrefabObjectProps.animated = sub_obj["include_animation"]
				#if sub_obj["IncludeAnimation"]:
					#sub_obj.ssx2_PrefabObjectProps.animation = sub_obj["Animation"]

				if sub_obj["include_matrix"]:
					new_obj.location = Vector(sub_obj["position"]) / 100 # WorldScale
					# new_obj.rotation_mode = 'QUATERNION'
					quat = sub_obj["rotation"]
					new_obj.rotation_quaternion = [quat[3], quat[0], quat[1], quat[2]]
					new_obj.rotation_mode = 'XYZ'

				fab_collection.objects.link(new_obj)
				
				if sub_obj["parent_idx"] != -1:
					parent_object = current_new_objs[sub_obj["parent_idx"]]
					new_obj.parent = parent_object
			current_new_objs.clear()


			layer_collection = get_layer_collection(root_layer_collection, fab_collection.name)
			layer_collection.exclude = True
			#layer_collection.hide_viewport = True # not needed





		
		def remove_trailing_numbers(s): # removes trailing numbers and and '_'
			return re.sub(r'[_\d]+$', '', s)



		### Import Instances
		print("\nImporting Instances")

		with open(instances_file_path, 'r') as f:
			data = json.load(f)

		for i, json_inst in enumerate(data["Instances"]):
			#print(json_inst["InstanceName"])
			empty = bpy.data.objects.new(json_inst["InstanceName"], None)
			empty.empty_display_size = 100 / 100 # WorldScale
			empty.rotation_mode = 'QUATERNION'
			empty.empty_display_type = 'ARROWS'
			empty.location = Vector(json_inst["Location"]) / 100 # WorldScale
			quat = json_inst["Rotation"]
			empty.rotation_quaternion = [quat[3], quat[0], quat[1], quat[2]]
			empty.rotation_mode = 'XYZ'
			empty.scale = json_inst["Scale"]
			empty.instance_type = 'COLLECTION'

			prefab_collection_for_instance = prefab_collections[json_inst["ModelID"]][0]
			empty.ssx2_PrefabForInstance = prefab_collection_for_instance
			empty.instance_collection = prefab_collection_for_instance
			empty.ssx2_EmptyMode = 'INSTANCE'

			# collision mode = enum? (Self, Custom, BBox)

			for key in json_inst:
				if key in [
					"InstanceName",
					"Location",
					"Rotation",
					"Scale"]:
					continue
				empty[key] = json_inst[key]
				# print(type(json_inst[key]), key)
				# if isinstance(json_inst[key], list):
				# 	print(type(json_inst[key][0])) # 'dict' 'str' makes it 'Python' type in blender

			# instances_collection.objects.link(empty)
			# new_instances_to_group.append(empty)

			if io.instanceImportGrouping == 'BATCH':
				new_group_col = collection_grouping(f"Inst_Group", instances_collection, inst_group_size, i)
				new_group_col.objects.link(empty)
			elif io.instanceImportGrouping == 'NAME':
				### groups by prefab
				# new_group_col = getset_collection("Inst " + prefab_collection_for_instance.name)
				# new_group_col.objects.link(empty)
				# if not bpy.context.scene.user_of_id(new_group_col): # if not in scene/layer bring it
				# 	instances_collection.children.link(new_group_col)

				### groups by name (excluding numbers)
				# i could create a list of unique prefab_collections names and another list with
				# indices to names in that list. then use json_inst["ModelID"] to get the corresponding name here

				new_group_name = re.sub(r'_\d+$', '_', json_inst["InstanceName"]) # removes only the last number
				# new_group_name = "Ins_" + remove_trailing_numbers(json_inst["InstanceName"]).removeprefix("Mdl_") # more accurate
				#new_group_name = "Ins_" + ''.join([char for char in json_inst["InstanceName"] if not char.isdigit()]).removeprefix("Mdl_")
				#new_group_name = new_group_name[:-1] if new_group_name.endswith('_') else new_group_name
				new_group_col = getset_collection(new_group_name)
				new_group_col.objects.link(empty)

				if not bpy.context.scene.user_of_id(new_group_col): # if not in scene/layer bring it
					instances_collection.children.link(new_group_col)

			# elif io.instanceImportGrouping == 'MESH':
				#TODO: Implement!

	def create_splines_json(self):
		print("Importing Splines")

		collection = bpy.data.collections.get('Splines')
		if collection is None:
			collection = bpy.data.collections.new('Splines')
			self.scene_collection.children.link(collection)


		file_path = self.folder_path + '/Splines.json'
		if not os.path.isfile(file_path):
			self.report({'ERROR'}, f"File 'Splines.json' does not exist in 'Import Folder'")
			return {'CANCELLED'}

		PT_CO = 0
		PT_LEFT_CO = 1
		PT_RIGHT_CO = 2
		PT_LEFT_TYPE = 3
		PT_RIGHT_TYPE = 4

		with open(file_path, 'r') as f:
			data = json.load(f)

			for i, json_spline in enumerate(data["Splines"]):

				print("\nSpline", i, json_spline["SplineName"])
				
				merged_points = []
				for j, segment in enumerate(json_spline["Segments"]):

					for k in range(3):
						x,y,z = segment["Points"][k]
						merged_points.append((x/100, y/100, z/100)) # world scale
						# print((x/100, y/100, z/100))

					# 	x,y,z = segment["Points"][k]
					# 	if self.io.splineImportAsNURBS:
					# 		merged_points.append((x/100, y/100, z/100, 1.0))
					# 	else:
					# 		merged_points.append((x/100, y/100, z/100))

				last = json_spline["Segments"][-1]["Points"][3]
				merged_points.append((last[0] / 100, last[1] / 100, last[2] / 100)) # world scale

				len_merged_points = len(merged_points)

				name = json_spline["SplineName"]
				# curve = bpy.data.curves.get(name)
				# if curve is None:
				# 	curve = bpy.data.curves.new(name, 'CURVE')

				curve = bpy.data.curves.new(name, 'CURVE')
				curve.dimensions = '3D'

				if self.io.splineImportAsNURBS: 			# NURBS Spline Curve

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
						point_current = Vector(merged_points[j]) # Current Point
						pt = [point_current, None, None, 'FREE', 'FREE']

						# Previous Point
						if j != 0:
							point_prev = Vector(merged_points[j-1])

						# Next Point
						if j+1 != len_merged_points:
							point_next = Vector(merged_points[j+1])
							pt[PT_RIGHT_CO] = point_next

						# Final Point
						if j+1 == len_merged_points:
							pt[PT_RIGHT_CO] = calc_opposite_point_co(point_current, point_prev)
							pt[PT_LEFT_CO] = point_prev

							if point_prev == point_current:
								pass # type = 'FREE'
							else:
								pt[PT_RIGHT_TYPE] = 'ALIGNED'
								pt[PT_LEFT_TYPE] = 'ALIGNED'

						# First Point
						if j == 0:
							pt[PT_LEFT_CO] = calc_opposite_point_co(point_current, point_next)
							pt[PT_RIGHT_TYPE] = 'ALIGNED'
							pt[PT_LEFT_TYPE] = 'ALIGNED'

						# Middle Points
						if (j != 0) and (j+1 != len_merged_points): 
							point_prev = Vector(merged_points[j-1])
							point_next = Vector(merged_points[j+1])

							# pt[PT_RIGHT_TYPE] = 'ALIGNED'
							# pt[PT_LEFT_TYPE] = 'ALIGNED'
							pt[PT_RIGHT_TYPE] = 'FREE'
							pt[PT_LEFT_TYPE] = 'FREE'
							
							pt[PT_RIGHT_CO] = point_next
							pt[PT_LEFT_CO] = point_prev

						# print("	left", pt[PT_LEFT_CO])
						# print("	curr", pt[PT_CO])
						# print("	right", pt[PT_RIGHT_CO])

						new_bezier_points.append(pt)
						
					spline = curve.splines.new(type='BEZIER')
					spline.bezier_points.add(len(new_bezier_points)-1)
					
					for j, bez_point in enumerate(new_bezier_points):
						point = spline.bezier_points[j]

						point.co = bez_point[PT_CO]
						point.handle_left = bez_point[PT_LEFT_CO]
						point.handle_right = bez_point[PT_RIGHT_CO]
						point.handle_left_type  = bez_point[PT_LEFT_TYPE]	#'FREE'
						point.handle_right_type = bez_point[PT_RIGHT_TYPE]	#'FREE'

					curve_obj = bpy.data.objects.new(name, curve)
					curve_obj.ssx2_CurveMode = "SPLINE"
					curve_obj.ssx2_SplineProps.type = str(json_spline["SplineStyle"])

					collection.objects.link(curve_obj)

		# SELECT ALL AT THE END AND SET ORIGIN
		#bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

	def import_json(self):
		scene = bpy.context.scene
		self.scene_collection = scene.collection

		io = scene.ssx2_WorldImportExportProps
		self.io = io
		#io.importNames
		#io.importTextures
		#io.patchImportGrouping

		self.folder_path = scene.ssx2_WorldImportExportProps.importFolderPath
		self.folder_path = os.path.abspath(bpy.path.abspath(self.folder_path))
		if not os.path.exists(self.folder_path): #.isdir
			self.report({'ERROR'}, f"Import Folder does not exist")
			return {'CANCELLED'}

		if io.importPatches: # <------------------------------- Import Patches
			getset_collection_to_target('Patches', self.scene_collection)

			temp_time_start = time.time()
			self.json_patches = get_patches_json(self.folder_path+'/Patches.json')
			self.images = get_images_from_folder(self.folder_path+'/Textures/')

			run_without_update(self.create_patches_json)

			print("importing patches took:", time.time() - temp_time_start, "seconds")


		if io.importPrefabs: # <------------------------------- Import Prefabs & Instances
			run_without_update(self.create_prefabs_json)


		if io.importPaths: # <------------------------------- Import Paths
			print("Importing Paths")

			aip_file_path = self.folder_path + '/AIP.json'
			sop_file_path = self.folder_path + '/SOP.json'
			if not os.path.isfile(aip_file_path):
				self.report({'ERROR'}, f"File 'AIP.json' does not exist in 'Import Folder'")
				return {'CANCELLED'}
			if not os.path.isfile(aip_file_path):
				self.report({'ERROR'}, f"File 'SOP.json' does not exist in 'Import Folder'")
				return {'CANCELLED'}

			collection_paths = bpy.data.collections.get('Paths')
			if collection_paths is None:
				collection_paths = bpy.data.collections.new('Paths')
				self.scene_collection.children.link(collection_paths)


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
			run_without_update(self.create_splines_json)



	def execute(self, context):
		
		import_time_start = time.time()

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

			print("seconds:", time.time() - import_time_start)

			self.report({'INFO'}, "Imported")

		
		bpy.data.materials.remove(self.appended_material)

		return {'FINISHED'}

class SSX2_OP_WorldExport(bpy.types.Operator):
	bl_idname = "wm.ssx2_export_world"
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

		export_folder = bpy.path.abspath(io.exportFolderPath)

		if len(export_folder) == 0:
			self.report({'ERROR'}, "'Export Folder' property is empty")
			return {"CANCELLED"}

		if not os.path.isdir(export_folder):
			self.report({'ERROR'}, "The chosen 'Export Folder' doesn't exist")
			return {"CANCELLED"}

		if io.exportAutoBuild:
			multitool_path = bpy.context.preferences.addons['bxtools'].preferences.multitool_path

			if len(multitool_path) == 0:
				self.report({'ERROR'}, "'Multitool Executable' property is empty. Choose the exe path first")
				return {"CANCELLED"}

			if not os.path.isfile(bpy.path.abspath(multitool_path)):
				self.report({'ERROR'}, "The chosen Multitool path doesn't exist")
				return {"CANCELLED"}

		do_json_indend = True
		export_counts = dict(
			paths_general = 0, # todo
			paths_showoff = 0, # todo
			splines = 0, # incomplete
			patch_objects = 0, # todo
			patch_segments = 0, # todo
		)

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
					if do_json_indend:
						json.dump(temp_json, f, indent=2)
					else:
						json.dump(temp_json, f, separators=(',', ':'))

			# ENDOF Export Paths


		if io.exportSplines: # <------------------------------------------------------ Export Splines
			print("Exporting Splines")

			spline_collection = bpy.data.collections.get("Splines")
			if spline_collection is None:
				self.report({'ERROR'}, "'Splines' collection not found")#spline_collection = bpy.context.collection
				return {'CANCELLED'}

			

			json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath))+'/Splines.json'
			
			if not os.path.isfile(json_export_path):
				self.report({'ERROR'}, f"'Splines.json' not found.\n{json_export_path}")
				return {'CANCELLED'}

			spline_objects = []
			for obj in spline_collection.all_objects:
				if obj.type != 'CURVE':
					continue

				if len(obj.data.splines) == 0:
					continue

				if obj.data.splines[0].type != 'BEZIER':
					continue

				spline_objects.append(obj)

			new_json = {}

			if len(spline_objects) == 0:
				if io.exportSplinesOverride:
					new_json['Splines'] = []
				else:
					self.report({'ERROR'}, "'Splines' collection is empty. Disable 'Splines' export or enable 'Override' to delete the JSON content")
			else:
				final_splines = []
				names = []

				for obj in spline_objects:

					props = obj.ssx2_SplineProps
					m = obj.matrix_world

					print("\n    ", obj.name)

					all_points = []
					segments = [] # from all_points to split segments of 4

					get_name = False
					for i, s in enumerate(obj.data.splines):
						current_points = []

						if s.type == 'BEZIER':
							if len(s.bezier_points) < 2:
								# print(f"Not enough points in {obj.name} spline {i}")
								BXT.error(self, f"Not enough points in object '{obj.name}'. Spline index {i}")
								bpy.ops.object.select_all(action='DESELECT')
								obj.select_set(True)
								set_active(obj)
								return {'CANCELLED'}
								#continue

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
						# elif s.type == 'NURBS':
						# 	continue
							# if len(s.points) % 4 != 0:
							# 	self.report({'ERROR'}, f"NURBS Spline in object {obj.name} is invalid\nPoint count must be divisible by 4")
							# 	return {'CANCELLED'}
							# for j, p in enumerate(s.points):
							# 	current_points.append( (m @ p.co) * scale)

							# check if points divide by 4
							# if not cancel and error
						# 	pass
						else:
							continue


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

						coeffs = calc_coefficients(*segment_points, samples=200)

						spline_segments_json_obj = {
							"Points": [pt.to_tuple() for pt in segment_points],
							"U0": coeffs[0],
							"U1": coeffs[1],
							"U2": coeffs[2],
							"U3": coeffs[3],
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
								self.report({'WARNING'}, "BXT Error occurred. Skipping.")

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

						export_counts['splines'] = len(final_splines)
			
			with open(json_export_path, 'w') as f:
				if do_json_indend:
					json.dump(new_json, f, indent=2)
				else:
					json.dump(new_json, f, separators=(',', ':'))

			# ENDOF Export Splines

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
							bpy.ops.object.mode_set(mode="OBJECT")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}
						elif length < 4:
							# continue
							self.report({'ERROR'}, f"Not enough bezier points in {obj_name}")
							bpy.ops.object.mode_set(mode="OBJECT")
							bpy.ops.object.select_all(action='DESELECT')
							set_active(obj)
							return {'CANCELLED'}
						elif len(raw) == 0:
							# continue
							self.report({'ERROR'}, f"No bezier points in {obj_name}")
							bpy.ops.object.mode_set(mode="OBJECT")
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

					tex = "0000.png"
					if len(obj.material_slots) != 0:
						mat = bpy.data.materials.get(obj.material_slots[0].name)
						if mat is not None:
							tex_node = mat.node_tree.nodes.get("Image Texture")
							if tex_node is not None:
								tex_image = tex_node.image
								if tex_image is not None:
									tex = tex_image.name

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
						grid_points.append((x, y, z))

					# grid_uvs = [(uv[0], -uv[1]) for uv in get_uvs_per_verts(obj)]
					# patch_uvs = [grid_uvs[12], grid_uvs[0], grid_uvs[15], grid_uvs[3]] # uv corners from mesh

					if props.useManualUV:
						patch_uvs = [(props.manualUV0[0], -props.manualUV0[1]),
									 (props.manualUV2[0], -props.manualUV2[1]), # dont forget these
									 (props.manualUV1[0], -props.manualUV1[1]), # are swapped
									 (props.manualUV3[0], -props.manualUV3[1])]
					else:
						patch_uvs = patch_known_uvs[patch_tex_map_equiv_uvs[int(props.texMapPreset)]].copy()
						
					tex = "0000.png"
					if len(obj.material_slots) != 0:
						mat = bpy.data.materials.get(obj.material_slots[0].name)
						if mat is not None:
							tex_node = mat.node_tree.nodes.get("Image Texture")
							if tex_node is not None:
								tex_image = tex_node.image
								if tex_image is not None:
									tex = tex_image.name

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
				if do_json_indend:
					json.dump(temp_json, f, indent=2)
				else:
					json.dump(temp_json, f)

			# ENDOF Export Patches

		if io.exportAutoBuild:
			# subprocess_run(
			# 	[multitool_path, "trickylevel", "trickybuild", export_folder], 
			# 	capture_output=False
			# )
			Popen(
				[multitool_path, "trickylevel", "trickybuild", export_folder]
			)

		print("Time taken:", time.time() - time_export_star, "seconds")
		self.report({'INFO'}, "Exported")
		return {'FINISHED'}

class SSX2_OP_SelectPrefab(bpy.types.Operator):
	bl_idname = "scene.ssx2_select_prefab"
	bl_label = "Select Prefab"
	bl_description = "Active selects the Prefab collection and object"
	bl_options = {'REGISTER', 'UNDO'}

	add_mode: bpy.props.BoolProperty(default=False)

	def execute(self, context):
		active_object = bpy.context.view_layer.objects.active
		target_collection = active_object.instance_collection
		target_name = target_collection.name

		layer_collection = get_layer_collection(bpy.context.view_layer.layer_collection, "Prefabs")
		if layer_collection:
			# layer_collection.exclude = False
			layer_collection.hide_viewport = False

		layer_collection = get_layer_collection(bpy.context.view_layer.layer_collection, target_name)

		if layer_collection:
			layer_collection.exclude = False
			layer_collection.hide_viewport = False

			if not self.add_mode:
				bpy.ops.object.select_all(action='DESELECT')

			bpy.context.view_layer.active_layer_collection = layer_collection
			print(f"Active collection set to: {layer_collection.name}")

			if layer_collection.has_objects:
				first_object = target_collection.objects[0]
				first_object.select_set(True)
				bpy.context.view_layer.objects.active = first_object
			return {'FINISHED'}
		
		#self.report({"WARNING"}, "Collection not found in 'Prefabs' Collection")
		self.report({"WARNING"}, "Collection not found")
		return {'CANCELLED'}

class SSX2_OP_ChooseMultitoolExe(bpy.types.Operator, ImportHelper):
	bl_idname = "scene.ssx2_choose_multitool_exe"
	bl_label = "Set Multitool Path"

	filter_glob: bpy.props.StringProperty(default="*.exe", options={'HIDDEN'})

	def execute(self, context):
		io = context.scene.ssx2_WorldImportExportProps
		bpy.context.preferences.addons['bxtools'].preferences.multitool_path = self.filepath
		return {'FINISHED'}

### PropertyGroups

class SSX2_WorldImportExportPropGroup(bpy.types.PropertyGroup): # ssx2_WorldImportExportProps
	importFolderPath: bpy.props.StringProperty(name="", subtype='DIR_PATH', 
		default="",
		description="Folder that contains the world files")
	worldChoice: bpy.props.EnumProperty(name='World Choice', items=enum_ssx2_world, default='gari')
	worldChoiceCustom: bpy.props.StringProperty(name="", default="gari", subtype='NONE',
		description="Name of input file e.g gari, megaple, pipe")
	importTextures: bpy.props.BoolProperty(name="Import Textures", default=True)
	importNames: bpy.props.BoolProperty(name="Import Names", default=True)

	# patches
	importPatches: bpy.props.BoolProperty(name="Import Patches", default=True)
	expandImportPatches: bpy.props.BoolProperty(default=False)
	patchImportGrouping: bpy.props.EnumProperty(name='Grouping', items=enum_ssx2_patch_group, default='BATCH')
	patchImportAsControlGrid: bpy.props.BoolProperty(default=False)

	# prefabs & instances
	importPrefabs: bpy.props.BoolProperty(name="Import Prefabs", default=True)
	expandImportPrefab: bpy.props.BoolProperty(default=False)
	# prefabImportGrouping: bpy.props.EnumProperty(name='Grouping', items=enum_ssx2_patch_group, default='BATCH')
	instanceImportGrouping: bpy.props.EnumProperty(name='Grouping', items=enum_ssx2_instance_group, default='BATCH')

	# splines
	importSplines: bpy.props.BoolProperty(name="Import Splines", default=True)
	expandImportSplines: bpy.props.BoolProperty(default=False)
	splineImportAsNURBS: bpy.props.BoolProperty(default=False)

	# paths
	importPaths: bpy.props.BoolProperty(name="Import Paths", default=True)
	importPathsAsCurve: bpy.props.BoolProperty(default=True)
	expandImportPaths: bpy.props.BoolProperty(default=False)

	# export
	exportFolderPath: bpy.props.StringProperty(subtype='DIR_PATH', default="",
		description="Export folder path")
	exportAutoBuild: bpy.props.BoolProperty(name="Auto Build", default=False)

	exportPatches: bpy.props.BoolProperty(name="Export Patches", default=True)
	exportPatchesCages: bpy.props.BoolProperty(name="Cages", default=True)
	exportPatchesOverride: bpy.props.BoolProperty(name="Override", default=True)

	exportSplines: bpy.props.BoolProperty(name="Export Splines", default=True)
	exportSplinesOverride: bpy.props.BoolProperty(name="Override", default=True,
		description="Overrides existing JSON splines. Will delete JSON contents if 'Splines' collection is empty")

	exportPathsGeneral: bpy.props.BoolProperty(name="Export Paths General", default=True)
	exportPathsShowoff: bpy.props.BoolProperty(name="Export Paths Showoff", default=True)

class SSX2_WorldPrefabCollectionPropGroup(bpy.types.PropertyGroup):
	unknown3: bpy.props.IntProperty(name="Unknown3")
	anim_time: bpy.props.FloatProperty(name="AnimTime")

class SSX2_WorldPrefabObjectPropGroup(bpy.types.PropertyGroup):
	flags: bpy.props.BoolProperty(name="Flags")
	animation: bpy.props.IntProperty(name="Animation") # temp. replace with appropriate data later
	animated: bpy.props.BoolProperty(name="Animated", default=False) # to show and hide panel

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
	u2: bpy.props.FloatProperty(name="u2", min=0.0, update=update_event_start_end)
	u3: bpy.props.FloatProperty(name="u3", min=0.0, update=update_event_start_end)

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

class SSX2_WorldSplinePropGroup(bpy.types.PropertyGroup): # ssx2_SplineProps
	type: bpy.props.EnumProperty(name='Spline Type', items=enum_ssx2_surface_type_spline)

	# change these to enum? spline_hide_mode = (NONE, SHOWOFF, RACE)
	#	assuming showoff and race set to True hides it in every mode
	#
	# hideShowoff: bpy.props.BoolProperty(name="Hide Showoff", default=False,
	# 	description="Hide in showoff modes.")
	# hideRace: bpy.props.BoolProperty(name="Hide Race", default=False,
	# 	description="Hide in race modes.")

class SSX2_WorldUIPropGroup(bpy.types.PropertyGroup): # ssx2_WorldUIProps class definition
	type: bpy.props.EnumProperty(name='Surface Type', items=enum_ssx2_surface_type)
	patchSelectByType: bpy.props.EnumProperty(name='Select by Surface Type', items=enum_ssx2_surface_type_extended, update=update_select_by_surface_type,
		description="Select all patches with the same type")


classes = (
	SSX2_WorldImportExportPropGroup,
	SSX2_WorldUIPropGroup,
	SSX2_WorldPrefabCollectionPropGroup,
	SSX2_WorldPrefabObjectPropGroup,
	SSX2_WorldSplinePropGroup,
	SSX2_WorldPathEventPropGroup,
	SSX2_WorldPathPropGroup,

	SSX2_OP_BakeTest,

	SSX2_OP_AddSplineBezier,
	SSX2_OP_AddSplineNURBS,
	SSX2_OP_AddInstance,
	SSX2_OP_AddPath,
	SSX2_OP_AddPathChild,
	SSX2_OP_WorldImport,
	SSX2_OP_WorldExport,
	SSX2_OP_WorldReloadNodeTrees,
	SSX2_OP_WorldInitiateProject,
	SSX2_OP_PathEventAdd,
	SSX2_OP_PathEventRemove,

	SSX2_OP_SelectPrefab,
	SSX2_OP_ChooseMultitoolExe,

)

def ssx2_world_register():
	for c in classes:
		register_class(c)

	bpy.types.Scene.ssx2_WorldProjectMode = bpy.props.EnumProperty(name='Project Mode', items=enum_ssx2_world_project_mode, default='JSON')

	bpy.types.Scene.ssx2_WorldImportExportProps = bpy.props.PointerProperty(type=SSX2_WorldImportExportPropGroup)
	bpy.types.Scene.ssx2_WorldUIProps = bpy.props.PointerProperty(type=SSX2_WorldUIPropGroup)
	bpy.types.Collection.ssx2_PrefabCollectionProps = bpy.props.PointerProperty(type=SSX2_WorldPrefabCollectionPropGroup)
	bpy.types.Object.ssx2_PrefabObjectProps = bpy.props.PointerProperty(type=SSX2_WorldPrefabObjectPropGroup)
	bpy.types.Object.ssx2_SplineProps = bpy.props.PointerProperty(type=SSX2_WorldSplinePropGroup)
	bpy.types.Object.ssx2_PathProps = bpy.props.PointerProperty(type=SSX2_WorldPathPropGroup)
	bpy.types.Object.ssx2_EmptyMode = bpy.props.EnumProperty(name='Empty Mode', items=enum_ssx2_empty_mode)
	bpy.types.Object.ssx2_CurveMode = bpy.props.EnumProperty(name='Curve Mode', items=enum_ssx2_curve_mode)

	bpy.types.Object.ssx2_PrefabForInstance = bpy.props.PointerProperty(type=bpy.types.Collection, poll=poll_prefab_for_inst, update=update_prefab_for_inst)


def ssx2_world_unregister():

	del bpy.types.Object.ssx2_PrefabForInstance

	del bpy.types.Scene.ssx2_WorldImportExportProps
	del bpy.types.Scene.ssx2_WorldUIProps
	del bpy.types.Collection.ssx2_PrefabCollectionProps
	del bpy.types.Object.ssx2_PrefabObjectProps
	del bpy.types.Object.ssx2_SplineProps
	del bpy.types.Object.ssx2_PathProps

	del bpy.types.Scene.ssx2_WorldProjectMode

	for c in classes:
		unregister_class(c)