import bpy, bmesh
from bpy.utils import register_class, unregister_class
from mathutils import Vector, Matrix
import gpu
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils
import functools

# from ..general.blender_get_data import get_uvs_per_verts
from ..general.blender_set_data import set_patch_material, set_patch_object, set_patch_control_grid
from ..general.bx_utils import *

from .ssx2_world_io_in import *


from .ssx2_constants import (
	#enum_ssx2_world_project_mode,
	#enum_ssx2_world,
	enum_ssx2_surface_type,
	enum_ssx2_patch_group,
	enum_ssx2_patch_uv_preset,
	enum_ssx2_spline_cage_type,
	patch_known_uvs,
	patch_known_uvs_blender,
	patch_tex_maps,
	patch_uv_equiv_tex_maps,
	patch_tex_map_equiv_uvs,
	indices_for_control_grid,
)

import os
import time

glob_start_time = time.time()
glob_obj_pch = None
glob_obj_pch_name = ""
glob_obj_proxy = None
glob_obj_proxy_name = "BXT_UV_PROXY"
glob_bm = None

def check_valid_spline_cage(obj) -> tuple:
	num_splines = len(obj.data.splines)

	if num_splines == 0:
		return False, f"'{obj.name}' is empty"

	if num_splines == 3 or num_splines == 5:
		return False, f"'{obj.name}' needs to have 2, 4 or 6 splines"

	if num_splines > 6:
		return False, f"'{obj.name}' has too many splines"

	equal_point_count = len(obj.data.splines[0].bezier_points)

	for spline in obj.data.splines:

		if spline.type != 'BEZIER':
			return False, f"'{obj.name}' contains non-bezier splines"

		if spline.point_count_u != equal_point_count:
			return False, f"'{obj.name}': Point count among the splines is not equal"

	return True, ""

def existing_patch_uvs(in_uvs):
	uvs = [tuple(round(flt, 5) for flt in uv) for uv in in_uvs]
	#uvs = in_uvs
	# if in_uvs != uvs:
	# 	#print(in_uvs, '\n', uvs)
	# 	#return None
	if uvs in patch_known_uvs:
		return patch_uv_equiv_tex_maps[patch_known_uvs.index(uvs)]
	else:
		return None

def round_uvs_for_check(uvs):
	new_uvs = [list(uv) for uv in uvs]
	for i, tup in enumerate(uvs):
		#new_tup = []
		for j, flt in enumerate(tup):
			absflt = abs(flt)
			if absflt <= 0.01:
				new_uvs[i][j] = round(flt)
			elif absflt >= 0.99 and absflt < 1.01:
				new_uvs[i][j] = round(flt)
			elif absflt >= 1.99 and absflt < 2.01:
				new_uvs[i][j] = round(flt)
			else:
				pass#print("hmmmmmmmmmmmmmm", flt)
	return new_uvs

def create_imported_patches(self, context, path, images, map_info=None):
	print("Importing Patches")

	io_props = context.scene.ssx2_WorldImportExportProps
	use_names = io_props.importNames
	import_textures = io_props.importTextures
	world_scale = context.scene.bx_WorldScale

	patch_grouping = io_props.patchImportGrouping

	if bpy.data.collections.get('Patches') is None:
		bpy.context.collection.children.link(bpy.data.collections.new('Patches'))

	if context.scene.bx_PlatformChoice == 'XBX':
		patch_data = ssx2_get_xbd_patches(path, scale = world_scale)


	print(patches_json.patches[0].points)
	print("DOESN'T WORK ANYMORE")
	return False

	if use_names:
		patch_names = [entry[0] for entry in map_info['PATCHES']]
	else:
		patch_names = [f"patch.{i}" for i in range(len(patch_data[0]))]

	
	to_group = []

	def create_patches():
		if len(bpy.context.selected_objects) != 0:
			bpy.ops.object.mode_set(mode = 'OBJECT')
			bpy.ops.object.select_all(action='DESELECT')
		
		if io_props.patchImportAsControlGrid:
			for i, patch_points in enumerate(patch_data[0]):
				pch_data = patch_data[1][i]
				name = patch_names[i]

				# patch = bpy.data.objects.get(name)
				# if patch is None or patch.type != 'MESH':
				mesh = bpy.data.meshes.new(name)
				patch = bpy.data.objects.new(name, mesh)

				set_patch_control_grid(mesh, patch_points, pch_data[1]) # uv Y axis needs to be flipped beforehand

				if import_textures and len(images) != 0:
					pch_mat_name = f"pch.{pch_data[3]}"
					pch_mat = bpy.data.materials.get(pch_mat_name)
					if pch_mat is None:
						pch_mat = set_patch_material(pch_mat_name)

					pch_mat.node_tree.nodes["Image Texture"].image = bpy.data.images.get(pch_data[3])
					patch.data.materials.append(pch_mat)

				if patch_grouping != 'NONE':
					to_group.append(patch)

				print(str(pch_data[2]))
				patch.ssx2_PatchProps.type = str(pch_data[2])
				patch.ssx2_PatchProps.showoffOnly = pch_data[5]
				patch.ssx2_PatchProps.isControlGrid = True
				patch['index'] = i
				patch["offset"] = int(i * 720 + 160)

		else:
			for i, patch_points in enumerate(patch_data[0]):
				pch_data = patch_data[1][i]
				
				patch = bpy.data.objects.get(patch_names[i])
				if patch is None or patch.type != 'SURFACE':
					patch = set_patch_object(patch_points, patch_names[i])
				else:
					# bpy.data.surfaces # is this a thing?
					# override it's data with a function?
					continue

				#existing_patch_uv_idx = existing_patch_uvs(round_uvs_for_check(pch_data[1]))
				existing_patch_uv_idx = existing_patch_uvs(pch_data[1])

				if existing_patch_uv_idx is None:
					patch.ssx2_PatchProps.useManualUV = True
					patch.color = (0.76, 0.258, 0.96, 1.0) # to see which ones are manual
				else:
					patch.ssx2_PatchProps.useManualUV = False
					patch.ssx2_PatchProps.texMapPreset = str(existing_patch_uv_idx)
					# patch.ssx2_PatchProps.texMap = patch_tex_maps[existing_patch_uv_idx] # already set by preset

				patch.ssx2_PatchProps.type = str(pch_data[2])
				patch.ssx2_PatchProps.showoffOnly = pch_data[5]
				patch.ssx2_PatchProps.manualUV0 = (pch_data[1][0][0], pch_data[1][0][1])
				patch.ssx2_PatchProps.manualUV1 = (pch_data[1][1][0], pch_data[1][1][1])
				patch.ssx2_PatchProps.manualUV2 = (pch_data[1][2][0], pch_data[1][2][1])
				patch.ssx2_PatchProps.manualUV3 = (pch_data[1][3][0], pch_data[1][3][1])
				patch['index'] = i
				patch["offset"] = int(i * 720 + 160)
				# patch["adjust_scale"] = adjust_scale


				if import_textures and len(images) != 0:
					pch_mat_name = f"pch.{pch_data[3]}"
					pch_mat = bpy.data.materials.get(pch_mat_name)
					if pch_mat is None:
						pch_mat = set_patch_material(pch_mat_name)

					pch_mat.node_tree.nodes["Image Texture"].image = images[pch_data[3]]
					patch.data.materials.append(pch_mat)

				if patch_grouping != 'NONE':
					to_group.append(patch)

	run_without_update(create_patches)

	if patch_grouping != 'NONE':
		parent_col = bpy.data.collections['Patches']
		layer_collection = bpy.context.view_layer.layer_collection
		if patch_grouping == "BATCH":
			group_size = 700 # make it a scene prop?
			for i, patch in enumerate(to_group):
				new_col = collection_grouping(f"Patch_Group", parent_col, group_size, i)
				new_col.objects.link(patch)
				if not io_props.patchImportAsControlGrid:
					parent_col.objects.unlink(patch)

		for collection in parent_col.children:
			layer_col = get_layer_collection(layer_collection, collection.name)
			layer_col.exclude = True

def reset_proxy_state():
	global glob_obj_pch, glob_obj_pch_name, glob_obj_proxy, glob_bm
	glob_obj_pch = None
	glob_obj_pch_name = ""
	glob_obj_proxy = None
	glob_bm = None
	obj_to_delete = bpy.data.objects.get(glob_obj_proxy_name)
	mesh_to_delete = bpy.data.meshes.get(glob_obj_proxy_name)
	if obj_to_delete is not None:
		bpy.data.objects.remove(obj_to_delete, do_unlink=True)
		bpy.data.meshes.remove(mesh_to_delete, do_unlink=True)
	
	obj_pch = bpy.data.objects.get(glob_obj_pch_name)
	if obj_pch is not None:
		set_active(obj_pch)

def live_uv_update():
	print("hmmm")
	global glob_obj_pch
	global glob_obj_proxy
	global glob_bm
	timer = time.time() - glob_start_time
	if timer > 1800:
		reset_proxy_state()
		return None

	if glob_obj_proxy is None:
		reset_proxy_state()
		return None

	if repr(glob_obj_proxy) == "<bpy_struct, Object invalid>":
		# sometimes undo will cause it to lose RNA
		glob_obj_proxy = bpy.data.objects.get("BXT_UV_PROXY")
		if glob_obj_proxy is None:
			reset_proxy_state()
			return None
	if repr(glob_obj_pch) == "<bpy_struct, Object invalid>":
		# sometimes undo will cause it to lose RNA
		glob_obj_pch = bpy.data.objects.get(glob_obj_pch_name)
		if glob_obj_pch is None:
			reset_proxy_state()
			return None

	mesh = glob_obj_proxy.data

	if glob_obj_proxy.mode == 'EDIT':
		if glob_bm is None or glob_bm.is_valid == False:
			glob_bm = bmesh.from_edit_mesh(mesh)

		if len(glob_bm.faces) != 1:
			reset_proxy_state()
			return None
		if len(glob_bm.verts) != 4:
			reset_proxy_state()
			return None

		uv_layer = glob_bm.loops.layers.uv.active
		for face in glob_bm.faces:
			glob_obj_pch.ssx2_PatchProps.manualUV0 = face.loops[0][uv_layer].uv
			glob_obj_pch.ssx2_PatchProps.manualUV2 = face.loops[1][uv_layer].uv
			glob_obj_pch.ssx2_PatchProps.manualUV3 = face.loops[2][uv_layer].uv
			glob_obj_pch.ssx2_PatchProps.manualUV1 = face.loops[3][uv_layer].uv
			
			glob_obj_pch.update_tag()
	else:
		glob_bm = None

	return 0.005

def update_patch_uv_preset(self, context):
	known_uvs = patch_known_uvs_blender[patch_tex_map_equiv_uvs[int(self.texMapPreset)]]

	self.manualUV0 = known_uvs[0]
	self.manualUV1 = known_uvs[2]
	self.manualUV2 = known_uvs[1]
	self.manualUV3 = known_uvs[3]

## Operators

class SSX2_OP_PatchUVTransform(bpy.types.Operator):
	bl_idname = "scene.ssx2_patch_uv_transform"
	bl_label = "Transform Patch UVs"
	bl_description = "Transforms the patches UVs"
	bl_options = {'REGISTER', 'UNDO'}

	xform: bpy.props.IntProperty(min=0, max=3, options={'HIDDEN'})

	def execute(self, context):
		objs = bpy.context.selected_objects
		patches = []

		for obj in objs:
			if obj.ssx2_PatchProps.isControlGrid:
				patches.append(obj)
			elif obj.type == 'SURFACE':
				patches.append(obj)
			elif obj.type == 'CURVE' and obj.ssx2_CurveMode == 'CAGE':
				patches.append(obj)

		if len(patches) == 0:
			BXT.warn(self, "No patches selected")
			return {'CANCELLED'}

		rotate_rl_enum = {'3': '1', '1': '4', '2': '3', '4': '2', '0': '6', '7': '5', '5': '0', '6': '7'}
		rotate_rr_enum = {'3': '2', '1': '3', '2': '4', '4': '1', '0': '5', '7': '6', '5': '7', '6': '0'}
		flipped_u_enum = {'3': '5', '1': '0', '2': '7', '4': '6', '0': '1', '7': '2', '5': '3', '6': '4'}
		flipped_v_enum = {'3': '6', '1': '7', '2': '0', '4': '5', '0': '2', '7': '1', '5': '4', '6': '3'}

		if self.xform == 0:
			print("Rotate -90")
			for obj in objs:
				flipped_preset = rotate_rl_enum[obj.ssx2_PatchProps.texMapPreset]
				obj.ssx2_PatchProps.texMapPreset = flipped_preset
		elif self.xform == 1:
			print("Rotate 90")
			for obj in objs:
				flipped_preset = rotate_rr_enum[obj.ssx2_PatchProps.texMapPreset]
				obj.ssx2_PatchProps.texMapPreset = flipped_preset
		elif self.xform == 2:
			print("Flip U")
			for obj in objs:
				flipped_preset = flipped_u_enum[obj.ssx2_PatchProps.texMapPreset]
				obj.ssx2_PatchProps.texMapPreset = flipped_preset
		elif self.xform == 3:
			print("Flip V")
			for obj in objs:
				flipped_preset = flipped_v_enum[obj.ssx2_PatchProps.texMapPreset]
				obj.ssx2_PatchProps.texMapPreset = flipped_preset
		else:
			print("Oops")
			{'CANCELLED'}


		return {'FINISHED'}

class SSX2_OP_PatchUVEditor(bpy.types.Operator):
	bl_idname = "object.patch_uv_editor"
	bl_label = "Patch UV Editor"
	bl_description = "Opens UV editing window"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		if glob_obj_proxy is None:
			active_object = context.active_object
			return (len(bpy.context.selected_objects) != 0) and (active_object is not None)
		else:
			return True

	# @classmethod
	# def poll(self, context):
	# 	active_object = context.active_object
	# 	return ((len(bpy.context.selected_objects) != 0) and (active_object is not None) and 
	# 	(active_object.type == 'SURFACE' or active_object.ssx2_PatchProps.isControlGrid
	# 	or active_object.ssx2_CurveMode == 'CAGE'))

	def test(self, context):
		print("hmmmmmmmmmm", self.obj_pch)
		return 0.8
	
	def execute(self, context):
		global glob_obj_pch
		global glob_obj_pch_name
		global glob_obj_proxy
		global glob_bm

		if glob_obj_proxy is not None:
			reset_proxy_state()
			self.report({'INFO'}, "Done")
			return {'FINISHED'}

		glob_obj_pch = bpy.context.active_object
		self.obj_pch = bpy.context.active_object
		props = glob_obj_pch.ssx2_PatchProps
		
		if (
			glob_obj_pch.type != 'SURFACE' and props.isControlGrid != True and 
			glob_obj_pch.ssx2_CurveMode != 'CAGE'
			):
			self.report({'WARNING'}, f"Active object is not a patch: {glob_obj_pch.name}")
			return {'CANCELLED'}
		
		glob_obj_pch_name = glob_obj_pch.name

		mat = None
		if len(glob_obj_pch.data.materials) != 0:
			mat = glob_obj_pch.data.materials[0]

		if props.useManualUV:
			patch_uvs = [
				props.manualUV0,
				props.manualUV1,
				props.manualUV2,
				props.manualUV3,
			]
		else:
			patch_uvs = patch_known_uvs_blender[patch_tex_map_equiv_uvs[int(props.texMapPreset)]].copy()
			patch_uvs = [
				patch_uvs[0],
				patch_uvs[2],
				patch_uvs[1],
				patch_uvs[3],
			]
			
		props.useManualUV = True
		
		glob_obj_proxy = bpy.data.objects.get(glob_obj_proxy_name)
		if glob_obj_proxy is None:
			bpy.ops.mesh.primitive_plane_add(enter_editmode=True,
				align='WORLD',
				location=(0, 0, 0),
				scale=(1, 1, 1)
			)
			glob_obj_proxy = bpy.context.active_object
			glob_obj_proxy.name = glob_obj_proxy_name
			glob_obj_proxy.data.name = glob_obj_proxy_name
		else:
			set_active(glob_obj_proxy)
			if glob_obj_proxy.mode != 'EDIT':
				bpy.ops.object.mode_set(mode='EDIT')

		# glob_obj_pch.lock_location = True


		mesh = glob_obj_proxy.data
		bpy.ops.uv.select_all(action='SELECT')

		mesh.materials.clear()
		if mat is not None:
			mesh.materials.append(mat)

		glob_bm = bmesh.from_edit_mesh(mesh)

		uv_layer = glob_bm.loops.layers.uv.active
		for face in glob_bm.faces:
			face.loops[0][uv_layer].uv = patch_uvs[0]
			face.loops[1][uv_layer].uv = patch_uvs[2]
			face.loops[2][uv_layer].uv = patch_uvs[3]
			face.loops[3][uv_layer].uv = patch_uvs[1]

		bmesh.update_edit_mesh(mesh)

		# bpy.ops.screen.back_to_previous()
		screen = bpy.context.screen
		if bpy.context.screen.show_fullscreen:
			bpy.ops.screen.back_to_previous()
			#bpy.ops.screen.screen_full_area(use_hide_panels=False)
		
		#window = bpy.context.window
		for area in bpy.context.screen.areas:
			if area.type == 'VIEW_3D':
				with bpy.context.temp_override(area=area):
					bpy.ops.screen.area_dupli('INVOKE_DEFAULT')
					break
				break
		
		for window in bpy.context.window_manager.windows:
			if len(window.screen.areas) == 1:
				for area in window.screen.areas:
					if area.type == 'VIEW_3D':
						with bpy.context.temp_override(window=window):
							with bpy.context.temp_override(area=area):
								bpy.ops.screen.area_split(direction='VERTICAL')
								#area.type = 'IMAGE_EDITOR'
								#area.ui_type = 'UV'
								break
							break
				window.screen.areas[1].type = 'IMAGE_EDITOR'
				window.screen.areas[1].ui_type = 'UV'
				window.screen.areas[1].spaces[0].show_region_toolbar = True
				window.screen.areas[1].spaces[0].show_region_ui = False
				window.screen.areas[0].spaces[0].show_region_toolbar = False
				window.screen.areas[0].spaces[0].show_region_ui = False
				window.screen.areas[0].spaces[0].show_region_tool_header = False

		print("\nstarting bpy timer")
		#bpy.app.timers.register(functools.partial(live_uv_update, [glob_obj_pch, glob_obj_proxy, glob_bm]))
		bpy.app.timers.register(live_uv_update)
		bpy.app.timers.register(functools.partial(self.test, [context]))
		return {'FINISHED'}

class SSX2_OP_SelectSplineCageU(bpy.types.Operator):
	bl_idname = "curve.select_spline_cage_along_u"
	bl_label = "Select Along U"
	bl_description = "Selects all points along U. Requires initial selection"
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	select_left: bpy.props.BoolProperty(name="Left", default=True)
	select_control: bpy.props.BoolProperty(name="Control", default=True)
	select_right: bpy.props.BoolProperty(name="Right", default=True)

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

		# if active_obj.ssx2_CurveMode != 'CAGE':
		# 	return {'CANCELLED'}
		# if active_obj.mode != 'EDIT':
		# 	return {'CANCELLED'}

		splines = active_obj.data.splines

		select_indices = []
		for i, spline in enumerate(splines):
			for p in spline.bezier_points:
				if p.select_control_point:
					select_indices.append(i)
					break
				elif p.select_left_handle:
					select_indices.append(i)
					break
				elif p.select_right_handle:
					select_indices.append(i)
					break

		if len(select_indices) == 0:
			self.report({'WARNING'}, "No points selected")
			return {'CANCELLED'}

		for spline_index in select_indices:
			for p in splines[spline_index].bezier_points:
				if self.select_control:
					p.select_control_point = True
				if self.select_left:
					p.select_left_handle = True
				if self.select_right:
					p.select_right_handle = True
		
		return {'FINISHED'}

class SSX2_OP_SelectSplineCageV(bpy.types.Operator):
	bl_idname = "curve.select_spline_cage_along_v"
	bl_label = "Select Along V"
	bl_description = "Selects all points along V. Requires initial selection"
	bl_options = {'REGISTER', 'UNDO'}

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

		# if active_obj.ssx2_CurveMode != 'CAGE':
		# 	return {'CANCELLED'}
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

class SSX2_OP_PatchSplit4x4(bpy.types.Operator):
	bl_idname = 'object.ssx2_patch_split_4x4'
	bl_label = "Split 4x4"
	bl_description = "Splits selected patch into 4x4 patches"
	bl_options = {'REGISTER', 'UNDO'}#, 'PRESET'}

	keep_original: bpy.props.BoolProperty(name="Keep Original", default=False)
	#apply_rotation: bpy.props.BoolProperty(name="Apply Rotation", default=True)
	#apply_scale: bpy.props.BoolProperty(name="Apply Scale", default=True)
	
	@classmethod
	def poll(self, context):
		#context.active_object # context.object
		active_object = context.active_object
		return (len(bpy.context.selected_objects) != 0) and (active_object is not None) and \
		(active_object.type == 'SURFACE')# or active_object.ssx2_PatchProps.isControlGrid)

	def execute(self, context):
		bpy.ops.object.mode_set(mode='OBJECT')

		collection = bpy.context.collection
		#selected_objs = bpy.context.selected_objects # all selected objects
		active_obj = bpy.context.active_object
		active_obj_name = active_obj.name
		active_obj_matrix = active_obj.matrix_local
		islands = active_obj.data.splines

		if active_obj.ssx2_PatchProps.isControlGrid:
			print("Control Grid")
			return {'CANCELLED'}

		if len(islands) == 1:
			if len(islands[0].points) == 16:
				self.report({'WARNING'}, "Already a single 4x4 segment")
				return {'CANCELLED'}
			
		bpy.context.view_layer.objects.active = None
		active_obj.select_set(False)

		all_patch_segments = []
		for j, s in enumerate(islands): # splines actually means internal surfaces/islands
			num_points = len(s.points)
			num_u = s.point_count_u
			num_v = s.point_count_v
			#num_segments = (num_u - 1) // 3
			num_strips = (num_v - 1) // 3

			print("points total/u/v", num_points, num_u, num_v)

			if num_u < 4 or num_v < 4:
				self.report({'WARNING'}, f"{active_obj_name}, Must have at least 4 points on U and V on each island")
				return {"CANCELLED"}

			splines = [] # each is a single spline curve

			for v in range(num_v):
				spline = []
				for u in range(num_u):
					spline.append((num_u*v) + u)
				splines.append(spline)

			new_patch_strips = [
				[splines[0], splines[1], splines[2], splines[3]]
			]

			if num_strips > 1:
				for i in range(1, num_strips):
					start = 3 * i
					new_patch_strips.append(
						[splines[start + 0], splines[start + 1], splines[start + 2], splines[start + 3]]
					)

			for new_strip in new_patch_strips:
				segments = segment_spline(new_strip)

				for i, spline in enumerate(segments):
					seg = []
					for point_indices in spline:
						for point_index in point_indices:
							seg.append(s.points[point_index].co)
					all_patch_segments.append(seg)

		num_all_patch_segments = len(all_patch_segments)
		if num_all_patch_segments == 0:
			return {'CANCELLED'}

		to_reselect = []
		current_patch = 0
		for patch_segment in all_patch_segments: # EACH ONE OBJECT WITH 16 POINTS (4x4)
			name = f"{active_obj_name}.s{current_patch}"
			current_patch += 1
			surface_data = bpy.data.curves.new(name, 'SURFACE') # Create Final Patch
			surface_data.dimensions = '3D'
			for i in range(4):
				spline = surface_data.splines.new(type='NURBS')
				spline.points.add(3) # one point already exists
				for j, point in enumerate(spline.points):
					point.select = True

			surface_data.resolution_u = 2
			surface_data.resolution_v = 2

			surface_object = bpy.data.objects.new(name, surface_data)
			collection.objects.link(surface_object)
			
			splines = surface_data.splines # this is a single surface/island, not multiple curves

			bpy.context.view_layer.objects.active = surface_object
			bpy.ops.object.mode_set(mode = 'EDIT')
			bpy.ops.curve.make_segment()
			
			splines[0].order_u = 4
			splines[0].order_v = 4
			splines[0].use_endpoint_u = True
			splines[0].use_endpoint_v = True
			splines[0].use_bezier_u = True
			splines[0].use_bezier_v = True

			for j, p in enumerate(splines[0].points):
				nx, ny, nz, nw = patch_segment[j]
				p.co = nx, ny, nz, 1.0

			bpy.ops.object.mode_set(mode = 'OBJECT')
			surface_object.matrix_local = active_obj_matrix
			to_reselect.append(surface_object)

		if not self.keep_original:
			bpy.data.objects.remove(active_obj)
		
		for obj in to_reselect:
			obj.select_set(True)

		bpy.context.view_layer.objects.active = surface_object

		self.report({'INFO'}, f"Split into {num_all_patch_segments} Patches")

		return {'FINISHED'}

class SSX2_OP_CageToPatch(bpy.types.Operator): # Curve/Spline Cage to Patch.
	bl_idname = 'object.patch_from_cage'
	bl_label = "Patch from Cage"
	bl_description = "Generates a patch from 2 or 4 bezier splines"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		active_object = context.active_object
		if active_object is not None:
			if active_object.type == 'CURVE':
				if len(active_object.data.splines) > 1:
					return True
					
		# return \
		# (len(bpy.context.selected_objects) != 0) and \
		# (active_object is not None) and \
		# (active_object.type == 'CURVE')

	def execute(self, context):
		# if bpy.context.mode != 'OBJECT':
		# 	bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

		collection = bpy.context.collection
		selected_objs = bpy.context.selected_objects
		active_obj = bpy.context.active_object

		if active_obj is None:
			self.report({'ERROR'}, "An active object is required")
			return {'CANCELLED'}

		if active_obj.type != 'CURVE': # can be removed, 
			self.report({'ERROR'}, f"Active object '{active_obj.name}' is not a bezier curve")
			return {'CANCELLED'}

		for obj in selected_objs:
			num_splines = len(obj.data.splines)
			data_splines = obj.data.splines
			obj_name = obj.name
			m = obj.matrix_world
			#matrices = []
			all_splines = []

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

			if num_splines == 2: # Dual Spline Cage
				print("2 splines")

				new_splines = [[], [], [], []]

				for i, s in enumerate(obj.data.splines):

					if s.type != 'BEZIER':
						self.report({'ERROR'}, "Splines must be bezier type (with handles)")
						return {'CANCELLED'}
					if len(s.bezier_points) == 1:
						self.report({'ERROR'}, f"Not enough points in spline {i+1}")
						return {'CANCELLED'}

					for j, p in enumerate(s.bezier_points):
						current_points = []

						if j == 0: # first
							current_points.append(m @ p.co)
							current_points.append(m @ p.handle_right)
						elif j == len(s.bezier_points)-1: # last
							current_points.append(m @ p.handle_left)
							current_points.append(m @ p.co)
						elif (j != 0) and (j != len(s.bezier_points)-1): # mids
							current_points.append(m @ p.handle_left)
							current_points.append(m @ p.co)
							current_points.append(m @ p.handle_right)

						if i == 0:
							new_splines[0] += current_points
						else:
							new_splines[3] += current_points

				row1_length = len(new_splines[0])#(len(obj.data.splines[0].bezier_points) * 2) + 3 # * 3 - 2
				
				if row1_length != len(new_splines[3]):
					self.report({'ERROR'}, f"Number of points must match on both splines")
					return {'CANCELLED'}
				
				for i in range(len(new_splines[0])):
					c1p = new_splines[0][i]
					c2p = new_splines[3][i]
					new_splines[1].append(c1p + ((c2p - c1p) / 3))
					new_splines[2].append(c2p - ((c2p - c1p) / 3))

				
				if double_v:
					doubled = double_quad_cage(new_splines)
					double_a = next(doubled)
					double_b = next(doubled)

					for spli in double_a:
						all_splines.append(spli)

					for i in range(1, 4):
						all_splines.append(double_b[i])
				else:
					all_splines.extend(new_splines)


			elif num_splines == 4: # Quad Spline Cage
				print("4 splines")

				raw = [bezier_to_raw(spline.bezier_points, m, 1.0) for spline in data_splines\
							if spline.type == 'BEZIER']

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
					double_a = next(doubled)
					double_b = next(doubled)

					for spli in double_a:
						all_splines.append(spli)

					for i in range(1, 4):
						all_splines.append(double_b[i])
				else:
					for spli in raw:
						all_splines.append(spli)

				row1_length = len(raw[0])
				
			elif num_splines == 6: # Hexa Spline Cage
				print("BXT 4 splines")

				raw = [bezier_to_raw(spline.bezier_points, m, 1.0) for spline in data_splines\
					if spline.type == 'BEZIER']
				
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

				row1_length = len(temp_strip1[0])

				if double_v:
					# these were taken from the export class.
					# i should probably make a new method so i dont have to combine strips then split again
					
					temp_strip1.append(inbetween_spline)
					temp_strip2 = [inbetween_spline] + temp_strip2

					doubled = double_quad_cage(temp_strip1)
					double_a = next(doubled)
					double_b = next(doubled)

					for spli in double_a:
						all_splines.append(spli)

					for i in range(1, 4):
						all_splines.append(double_b[i])


					doubled = double_quad_cage(temp_strip2)
					double_a = next(doubled)
					double_b = next(doubled)

					for i in range(1, 4):
						all_splines.append(double_a[i])

					for i in range(1, 4):
						all_splines.append(double_b[i])

				else:
					for spli in temp_strip1:
						all_splines.append(spli)
					all_splines.append(inbetween_spline)
					for spli in temp_strip2:
						all_splines.append(spli)
				

				# self.report({'WARNING'}, "Cancel")
				# return {'CANCELLED'}

			else:
				self.report({'ERROR'}, "Active object must have 2, 4 or 6 splines.")
				return {'CANCELLED'}


			all_points_combined = []

			for spl in all_splines:
				all_points_combined += spl

			# for p in all_points_combined:
			# 	print(p)

			#return {'CANCELLED'}

			print("\nPATCH STRIP")

			name = f"PatchStrip"
			surface_data = bpy.data.curves.new(name, 'SURFACE') # Create Final Patch

			surface_data.dimensions = '3D'
			for i in range(row1_length):
				spline = surface_data.splines.new(type='NURBS')
				#spline.points.add(3) # one point already exists

				spline.points.add(len(all_splines) - 1)#6)

				for j, point in enumerate(spline.points):
					point.select = True
					#nx, ny, nz = all_splines[i][j]
					#point.co = 0.0, 0.0, 0.0, 1.0#nx, ny, nz, 1.0

			surface_data.resolution_u = 2
			surface_data.resolution_v = 2

			surface_object = bpy.data.objects.new(name, surface_data)
			collection.objects.link(surface_object)
			
			splines = surface_data.splines # this is a single surface, not multiple splines

			bpy.context.view_layer.objects.active = surface_object
			bpy.ops.object.mode_set(mode = 'EDIT')
			bpy.ops.curve.make_segment()
			
			splines[0].order_u = 4
			splines[0].order_v = 4
			splines[0].use_endpoint_u = True
			splines[0].use_endpoint_v = True
			splines[0].use_bezier_u = True
			splines[0].use_bezier_v = True

			for j, p in enumerate(splines[0].points): # points of surface 0
				nx, ny, nz = all_points_combined[j]
				p.co = nx, ny, nz, 1.0

			bpy.ops.object.mode_set(mode = 'OBJECT')
			bpy.context.active_object.select_set(False)

		self.report({'INFO'}, "Finished")
		return {'FINISHED'}

class SSX2_OP_QuadToPatch(bpy.types.Operator):
	bl_idname = 'object.patch_from_quad'
	bl_label = "Patch from Quad"
	bl_description = "Generates a patch from each quad"
	bl_options = {'REGISTER', 'UNDO'}

	split_all_quads: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

	@classmethod
	def poll(self, context):
		active_object = context.active_object
		if active_object is not None:
			if active_object.type == 'MESH':
				return True

	def execute(self, context):
		collection = bpy.context.collection
		self.selected_objs = bpy.context.selected_objects
		active_obj = bpy.context.active_object

		self.patches_collection = getset_collection_to_target("Patches", bpy.context.scene.collection)


		self.profile_get_data = 0.0
		self.profile_setup_majors = 0.0
		self.profile_generate_patches = 0.0
		profile_total_start = time.time()

		self.append_control_grid_nodes()

		self.control_grid_faces = [
			(0, 4, 5, 1),
			(1, 5, 6, 2),
			(2, 6, 7, 3),

			(4, 8, 9, 5),
			(5, 9, 10, 6),
			(6, 10, 11, 7),

			(8, 12, 13, 9),
			(9, 13, 14, 10),
			(10, 14, 15, 11),
		]


		if active_obj is None:
			self.report({'ERROR'}, "An active object is required")
			return {'CANCELLED'}

		for obj in self.selected_objs:
			time_started = time.time()

			bpy.ops.object.mode_set(mode='EDIT', toggle=False)

			if self.split_all_quads:
				test = self.quads_to_patches_split(obj)
			else:
				test = self.quads_to_patches(obj)

			if test == False:
				return {'CANCELLED'}

		bpy.context.view_layer.objects.active = active_obj
		bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


		print()
		print("get_data:", round(self.profile_get_data, 5))
		print("setup_majors:", round(self.profile_setup_majors, 5))
		print("generate_patches:", round(self.profile_generate_patches, 5))
		print("total:", round(time.time() - profile_total_start, 5))


		return {'FINISHED'}

	def append_control_grid_nodes(self):
		append_path = templates_append_path
		node_tree_name = "GridTesselateAppend"
		node_tree = bpy.data.node_groups.get(node_tree_name)

		if node_tree is not None:
			return

		if not os.path.isfile(append_path):
			self.report({'ERROR'}, f"Failed to append {append_path}")
			return {'CANCELLED'}

		with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
			if node_tree_name in data_from.node_groups:
				data_to.node_groups = [node_tree_name]
			else:
				self.report({'ERROR'}, f"Failed to append geonodes from {append_path}")
				return {'CANCELLED'}

	def quads_to_patches_split(self, obj):
		mesh = obj.data
		vertices = mesh.vertices
		bm = bmesh.from_edit_mesh(mesh)

		handle_scalar = 0.3333333333333333

		for i, f in enumerate(mesh.polygons):
			if len(f.vertices) != 4:
				continue

			v0, v1, v2, v3 = vertices[f.vertices[0]].co, \
				vertices[f.vertices[1]].co, \
				vertices[f.vertices[2]].co, \
				vertices[f.vertices[3]].co

			points = [Vector((0,0,0))] * 16

			# points[ 0] = v0
			# points[ 1] = ((v0 - v1) * -handle_scalar) + v0
			# points[ 2] = ((v1 - v0) * -handle_scalar) + v1
			# points[ 3] = v1

			# points[ 4] = ((v0 - v3) * -handle_scalar) + v0
			# points[ 5] = (((v1 - v0) + (v3 - v0)) * handle_scalar) + v0
			# points[ 6] = (((v0 - v1) + (v2 - v1)) * handle_scalar) + v1
			# points[ 7] = ((v1 - v2) * -handle_scalar) + v1

			# points[ 8] = ((v3 - v0) * -handle_scalar) + v3
			# points[ 9] = (((v0 - v3) + (v2 - v3)) * handle_scalar) + v3
			# points[10] = (((v1 - v2) + (v3 - v2)) * handle_scalar) + v2
			# points[11] = ((v2 - v1) * -handle_scalar) + v2

			# points[12] = v3
			# points[13] = ((v3 - v2) * -handle_scalar) + v3
			# points[14] = ((v2 - v3) * -handle_scalar) + v2
			# points[15] = v2

			points[ 0] = v1
			points[ 1] = ((v1 - v0) * -handle_scalar) + v1
			points[ 2] = ((v0 - v1) * -handle_scalar) + v0
			points[ 3] = v0

			points[ 4] = ((v1 - v2) * -handle_scalar) + v1
			points[ 5] = (((v0 - v1) + (v2 - v1)) * handle_scalar) + v1
			points[ 6] = (((v1 - v0) + (v3 - v0)) * handle_scalar) + v0
			points[ 7] = ((v0 - v3) * -handle_scalar) + v0

			points[ 8] = ((v2 - v1) * -handle_scalar) + v2
			points[ 9] = (((v1 - v2) + (v3 - v2)) * handle_scalar) + v2
			points[10] = (((v0 - v3) + (v2 - v3)) * handle_scalar) + v3
			points[11] = ((v3 - v0) * -handle_scalar) + v3

			points[12] = v2
			points[13] = ((v2 - v3) * -handle_scalar) + v2
			points[14] = ((v3 - v2) * -handle_scalar) + v3
			points[15] = v3


			test_mesh = bpy.data.meshes.new("PatchFromQuad" + str(i))
			
			test_mesh.from_pydata(points, [], self.control_grid_faces)
			test_mesh.update()
			# bpy.ops.object.mode_set(mode='EDIT', toggle=False)

			new_patch = bpy.data.objects.new("PatchFromQuad" + str(i), test_mesh)


			# bpy.context.collection.objects.link(new_patch)
			bpy.data.collections['Patches'].objects.link(new_patch)


			# TODO: check node tree existance before main loop
			node_tree = bpy.data.node_groups.get("GridTesselateAppend")
			if node_tree is not None:
				node_modifier = new_patch.modifiers.new(name="GeoNodes", type='NODES')
				node_modifier.node_group = node_tree

			new_patch.ssx2_PatchProps.type = '1'

			new_patch.matrix_world = obj.matrix_world


	def quads_to_patches(self, obj):

		# if len(bpy.context.selected_objects) != 0:
		# 	bpy.ops.object.select_all(action='DESELECT')
		# obj.select_set(True)
		# bpy.context.view_layer.objects.active = obj
		# bpy.ops.object.mode_set(mode='EDIT', toggle=False)

		profile_timer = time.time()

		mesh = obj.data
		verts = mesh.vertices
		bm = bmesh.from_edit_mesh(mesh)

		handle_scalar = 0.3333333333333333

		NORTH, WEST, SOUTH, EAST = 0, 1, 2, 3
		cardinal_opposites = (SOUTH, EAST, NORTH, WEST)

		swapped = (1, 0)

		# majors_to_fix = {i: [] for i in range(len(verts))}
		majors_to_fix = {}
		patches_to_fix = {}

		for i, f in enumerate(bm.faces):
			# print("\n__________________ Face:", i, "______________________")
			bm.faces.ensure_lookup_table()

			if len(f.verts) != 4:
				# raise ValueError(f"Face {i} is not a quad")
				continue

			# face loops are CCW, so this is consistent (v0, v1, v2, v3)
			loops = [l for l in f.loops]
			v = [l.vert for l in loops]  # v[0]..v[3]

			edges = (
				loops[0].edge, # (v0, v1)
				loops[1].edge, # (v1, v2)
				loops[2].edge, # (v2, v3)
				loops[3].edge  # (v3, v0)
			)

			edges_list = [loops[0].edge, loops[1].edge, loops[2].edge, loops[3].edge]
			edges_verts = [(e.verts[0].index, e.verts[1].index) for e in edges_list]

			result = {}
			for corner in v:
				result[corner.index] = [None, None, None, None] # cardinal vertex neighbors 


			for j, edge in enumerate(edges):
				# print("\nCurrent loop:", _i)
				# print("BM Edge:", edge.index, "Verts: {", edge.verts[0].index, ",", edge.verts[1].index, "}")

				linked_faces = [lf for lf in edge.link_faces if lf != f]

				# verts inside the edges
				e_v1, e_v2 = edge.verts
				ev1, ev2 = e_v1.index, e_v2.index

				opposite_direction = cardinal_opposites[j]

				# get the internal neighbors
				a = None
				b = None

				for z, _entry in enumerate(edges_verts):
					if ev2 in _entry:
						continue
					if ev1 in _entry:
						a = _entry[swapped[_entry.index(ev1)]]

				for z, _entry in enumerate(edges_verts):
					if ev1 in _entry:
						continue
					if ev2 in _entry:
						b = _entry[swapped[_entry.index(ev2)]]


				result[ev1][opposite_direction] = a
				result[ev2][opposite_direction] = b

				if not linked_faces:
					# print("<-----------------------------------skipped")
					continue # boundary edge. no neighbor

				if mesh.edges[edge.index].crease > 0.99:
					continue

				neighbor = linked_faces[0] # one face (unless there's triangles?)

				def find_adjacent_in_neighbor(shared_a, shared_b):
					for nl in neighbor.loops:
						if nl.vert is shared_a and nl.link_loop_next.vert is shared_b:
							# the vertex before shared_a (in this loop order) is the non-shared neighbor for shared_a
							return nl.link_loop_prev.vert

					# swapped order (if loops list is oriented opposite)
					for nl in neighbor.loops:
						if nl.vert is shared_a and nl.link_loop_prev.vert is shared_b:
							return nl.link_loop_next.vert
					return None

				nbr_for_e_v1 = find_adjacent_in_neighbor(e_v1, e_v2)
				nbr_for_e_v2 = find_adjacent_in_neighbor(e_v2, e_v1)

				# assign to both corners that touch this edge (both shared verts should get this direction)
				result[ev1][j] = nbr_for_e_v1.index if nbr_for_e_v1 else None
				result[ev2][j] = nbr_for_e_v2.index if nbr_for_e_v2 else None


			result = list(result.values())

			
			self.profile_get_data += time.time() - profile_timer
			profile_timer = time.time()


			# C, N, W, S, E, NW, SW, SE, NE
			# 0, 1, 2, 3, 4,  5,  6,  7,  8
			majors = [[None, None, None, None, None, None, None, None, None] for i in range(4)]


			# print("\nBuilding Majors/Handles")

			for j, neighbor_info in enumerate(result):
				# print(j, f.verts[j].index, neighbor_info) # aka nbr_verts

				core = f.verts[j].co

				cardinal_handles = [None, None, None, None] # N, W, S, E
				quadrant_handles = [None, None, None, None] # NW, SW, SE, NE


				for direction, neighbor in enumerate(neighbor_info):
					if neighbor is None:
						opposite_vtx = neighbor_info[cardinal_opposites[direction]]
						new_handle = (core - verts[opposite_vtx].co) * handle_scalar
					else:
						new_handle = (verts[neighbor].co - core) * handle_scalar

					cardinal_handles[direction] = new_handle


				quadrant_handles[0] = cardinal_handles[0] + cardinal_handles[1]
				quadrant_handles[1] = cardinal_handles[1] + cardinal_handles[2]
				quadrant_handles[2] = cardinal_handles[2] + cardinal_handles[3]
				quadrant_handles[3] = cardinal_handles[0] + cardinal_handles[3]

				cardinal_handles[0] = core + ((quadrant_handles[0] + quadrant_handles[1]) * 0.5)
				cardinal_handles[1] = core + ((quadrant_handles[1] + quadrant_handles[2]) * 0.5)
				cardinal_handles[2] = core + ((quadrant_handles[2] + quadrant_handles[3]) * 0.5)
				cardinal_handles[3] = core + ((quadrant_handles[3] + quadrant_handles[0]) * 0.5)

				quadrant_handles[0] += core
				quadrant_handles[1] += core
				quadrant_handles[2] += core
				quadrant_handles[3] += core

				majors[j][0] = (quadrant_handles[0] + quadrant_handles[1] + quadrant_handles[2] + quadrant_handles[3]) * 0.25
				
				majors[j][1] = cardinal_handles[0]
				majors[j][2] = cardinal_handles[1]
				majors[j][3] = cardinal_handles[2]
				majors[j][4] = cardinal_handles[3]

				majors[j][5] = quadrant_handles[0]
				majors[j][6] = quadrant_handles[1]
				majors[j][7] = quadrant_handles[2]
				majors[j][8] = quadrant_handles[3]


				if f.verts[j].index not in majors_to_fix:
					majors_to_fix[f.verts[j].index] = [majors[j][0], [(i, j)]]
				else:
					majors_to_fix[f.verts[j].index][0] += majors[j][0]
					majors_to_fix[f.verts[j].index][1].append((i, j))


			self.profile_setup_majors += time.time() - profile_timer
			profile_timer = time.time()


			points = [Vector((0,0,0))] * 16

			# C, N, W, S, E, NW, SW, SE, NE
			# 0, 1, 2, 3, 4,  5,  6,  7,  8

			new_obj_mode = 0

			if new_obj_mode == 0:
				points[ 0] = majors[1][0] # majors[2][0]
				points[ 1] = majors[1][3] # majors[2][3]
				points[ 2] = majors[0][1] # majors[3][1]
				points[ 3] = majors[0][0] # majors[3][0]

				points[ 4] = majors[1][2] # majors[2][4]
				points[ 5] = majors[1][7] # majors[2][8]
				points[ 6] = majors[0][6] # majors[3][5]
				points[ 7] = majors[0][2] # majors[3][4]

				points[ 8] = majors[2][4] # majors[1][2]
				points[ 9] = majors[2][8] # majors[1][7]
				points[10] = majors[3][5] # majors[0][6]
				points[11] = majors[3][4] # majors[0][2]

				points[12] = majors[2][0] # majors[1][0]
				points[13] = majors[2][3] # majors[1][3]
				points[14] = majors[3][1] # majors[0][1]
				points[15] = majors[3][0] # majors[0][0]

				# bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
				test_mesh = bpy.data.meshes.new("PatchFromQuad" + str(i))
				
				test_mesh.from_pydata(points, [], self.control_grid_faces)
				test_mesh.update()
				# bpy.ops.object.mode_set(mode='EDIT', toggle=False)

				new_patch = bpy.data.objects.new("PatchFromQuad" + str(i), test_mesh)


				# bpy.context.collection.objects.link(new_patch)
				bpy.data.collections['Patches'].objects.link(new_patch)


				# new_patch.location = obj.location
				new_patch.matrix_world = obj.matrix_world
				# # # new_patch.scale = obj.scale
				# # # new_patch.rotation_euler = obj.rotation_euler

				# TODO: check node tree existance before main loop
				node_tree = bpy.data.node_groups.get("GridTesselateAppend")
				if node_tree is not None:
					node_modifier = new_patch.modifiers.new(name="GeoNodes", type='NODES')
					node_modifier.node_group = node_tree

				new_patch.ssx2_PatchProps.isControlGrid = True

				patches_to_fix[i] = new_patch.data

			elif new_obj_mode == 1:
				points[ 0] = majors[1][0]
				points[ 1] = majors[1][3]
				points[ 2] = majors[0][1]
				points[ 3] = majors[0][0]

				points[ 4] = majors[1][2]
				points[ 5] = majors[1][7]
				points[ 6] = majors[0][6]
				points[ 7] = majors[0][2]

				points[ 8] = majors[2][4]
				points[ 9] = majors[2][8]
				points[10] = majors[3][5]
				points[11] = majors[3][4]

				points[12] = majors[2][0]
				points[13] = majors[2][3]
				points[14] = majors[3][1]
				points[15] = majors[3][0]

				for j, point in enumerate(points):
					points[j] = Vector((point.x, point.y, point.z, 1.0))

				new_patch = set_patch_object(points, "PatchFromQuad" + str(i))
				
				patches_to_fix[i] = new_patch.data.splines[0]


			new_patch.ssx2_PatchProps.type = '1'
			new_patch.matrix_world = obj.matrix_world


			self.profile_generate_patches += time.time() - profile_timer
			profile_timer = time.time()
			
			# if i == 0:
			# 	break


		if new_obj_mode == 1:

			corner_index_translate = (3, 0, 12, 15)

			for major_index, to_fix in majors_to_fix.items():

				num_cores = len(to_fix[1])

				if num_cores < 3:
					continue

				# print(major_index, to_fix)

				midpoint = to_fix[0] / num_cores
				midpoint = Vector((midpoint[0], midpoint[1], midpoint[2], 1.0))

				for patch_index, corner_index in to_fix[1]:
					idx = corner_index_translate[corner_index]
					patches_to_fix[patch_index].points[idx].co = midpoint

		else:
			corner_index_translate = (3, 0, 12, 15)

			for major_index, to_fix in majors_to_fix.items():

				num_cores = len(to_fix[1])

				if num_cores < 3:
					continue

				# print(major_index, to_fix)

				midpoint = to_fix[0] / num_cores
				midpoint = Vector((midpoint[0], midpoint[1], midpoint[2], 1.0))

				for patch_index, corner_index in to_fix[1]:
					idx = corner_index_translate[corner_index]
					patches_to_fix[patch_index].vertices[idx].co = midpoint.to_3d()
			

		bm.free()






class SSX2_OP_FlipSplineOrder(bpy.types.Operator):
	bl_idname = 'object.flip_spline_order'
	bl_label = "Flip Spline Order"
	bl_description = "Edit mode: Flips the order of selected\nObject mode: Flips order of all"
	bl_options = {'REGISTER', 'UNDO'}

	# selected_only: bpy.props.BoolProperty(name="Selected Only", default=False)

	@classmethod
	def poll(self, context):
		active_object = context.active_object
		if active_object is not None:
			if active_object.type == 'CURVE':
				if len(active_object.data.splines) > 1:
					return True
					
		# return \
		# (len(bpy.context.selected_objects) != 0) and \
		# (active_object is not None) and \
		# (active_object.type == 'CURVE')

	def flip(self, splines):
		num_splines = len(splines)
		# if num_splines == 2:
		# 	print("2 splines")

		# 	if len(splines[0].bezier_points) != len(splines[1].bezier_points):
		# 		return False

		# 	temp_data0 = [(p.co[:], p.handle_left[:], p.handle_right[:], p.handle_left_type, p.handle_right_type) for p in splines[0].bezier_points]
		# 	temp_data1 = [(p.co[:], p.handle_left[:], p.handle_right[:], p.handle_left_type, p.handle_right_type) for p in splines[1].bezier_points]

		# 	for i, p in enumerate(splines[1].bezier_points):
		# 		p.handle_left_type = temp_data0[i][3]
		# 		p.handle_right_type = temp_data0[i][4]
		# 		p.co = temp_data0[i][0]
		# 		p.handle_left = temp_data0[i][1]
		# 		p.handle_right = temp_data0[i][2]

		# 	for i, p in enumerate(splines[0].bezier_points):
		# 		p.handle_left_type = temp_data1[i][3]
		# 		p.handle_right_type = temp_data1[i][4]
		# 		p.co = temp_data1[i][0]
		# 		p.handle_left = temp_data1[i][1]
		# 		p.handle_right = temp_data1[i][2]

		# elif num_splines > 2:
		print(num_splines, "splines")

		adj = num_splines - 1

		num_points = len(splines[0].bezier_points)

		temp_data = []
		for i, s in enumerate(splines):
			if len(s.bezier_points) != num_points:
				print("spline", i, "incorrect point count")
				return False
			#temp_data.append([(p.co[:], p.handle_left[:], p.handle_right[:]) for p in s.bezier_points])
			temp_data.append([(p.co[:], p.handle_left[:], p.handle_right[:], p.handle_left_type, p.handle_right_type) for p in s.bezier_points])
			# print(i, temp_data[i][0][3], temp_data[i][0][4])

		for i, s in enumerate(splines):
			for j, p in enumerate(s.bezier_points):
				p.handle_left_type = temp_data[-i+adj][j][3]
				p.handle_right_type = temp_data[-i+adj][j][4]
				p.co = temp_data[-i+adj][j][0]
				p.handle_left = temp_data[-i+adj][j][1]
				p.handle_right = temp_data[-i+adj][j][2]

	def execute(self, context):
		# if bpy.context.mode != 'OBJECT':
		# 	bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

		collection = bpy.context.collection
		selected_objs = bpy.context.selected_objects
		active_obj = bpy.context.active_object

		failed_objs = ""

		for obj in selected_objs:

			if obj.type != "CURVE":
				continue

			splines = obj.data.splines
			num_splines = len(splines)
			# m = obj.matrix_world
			matrices = []
			all_splines = []

			# if num_splines < 2:
			# 	self.report({'WARNING'}, f"{obj} needs at least 2 splines")
			# 	continue
				#return {"CANCELLED"}

			print(obj.name)

			if obj.mode == 'EDIT':
				selected_splines = []

				for spline in splines:
					for p in spline.bezier_points:
						if p.select_control_point or p.select_left_handle or p.select_right_handle:
							selected_splines.append(spline)
							break

				if len(selected_splines) < 2:
					print("NOT ENOUGH SELECTED. FLIPPING ALL")
				else:
					print("FLIPPING SELECTED")
					splines = selected_splines

			else:
				print("FLIPPING ALL")

			flip = self.flip(splines)
			if flip == False:
				failed_objs += "\n" + obj.name

		if len(failed_objs) != 0:
			self.report({'WARNING'}, "The following objects do not have the same number of points on all splines:" + failed_objs)
			self.report({'WARNING'}, "Finished with exceptions (Click here)")
		else:
			self.report({'INFO'}, "Flipped")

		return {"FINISHED"}


class SSX2_OP_AddSplineCage(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_spline_cage'
	bl_label = "Spline Cage"
	bl_description = 'Generate a spline cage'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	type: bpy.props.EnumProperty(name='Cage Type', items=enum_ssx2_spline_cage_type, default='QUAD')
	origin: bpy.props.BoolProperty(name='Origin at Center')
	
	
	def execute(self, context):
		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		collection = bpy.context.collection
		append_path = templates_append_path
		
		if self.type == 'DUAL':
			curve_data_name = "SplineCageDualAppend"
		elif self.type == 'QUAD':
			curve_data_name = "SplineCageAppend"
		elif self.type == 'HEXA':
			curve_data_name = "SplineCageHexaAppend"

		node_tree_name = "CageLoftAppend"
		curve_data = bpy.data.curves.get(curve_data_name)
		node_tree = bpy.data.node_groups.get(node_tree_name)

		print("Append Spline Cage:", curve_data is None)
		print("Append Node Tree:", node_tree is None)

		if not os.path.isfile(append_path):
			self.report({'ERROR'}, f"Failed to append {append_path}")
			return {'CANCELLED'}

		with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
			if node_tree is None:
				if node_tree_name in data_from.node_groups:
					data_to.node_groups = [node_tree_name]
				else:
					self.report({'ERROR'}, f"Failed to append geonodes from {append_path}")
					return {'CANCELLED'}

			if curve_data is None:
				if curve_data_name in data_from.curves:
					data_to.curves = [curve_data_name]
				else:
					self.report({'ERROR'}, f"Failed to append spline cage from {append_path}")
					return {'CANCELLED'}

		curve_data = bpy.data.curves.get(curve_data_name)
		# if curve_data.users == 0:
		# 	curve_data.use_fake_user = True
		curve_data = curve_data.copy()
		curve_obj = bpy.data.objects.new("SplineCage", curve_data)
		curve_data.name = curve_obj.name
		curve_obj.location = bpy.context.scene.cursor.location

		node_tree = bpy.data.node_groups.get(node_tree_name)
		# if node_tree.users == 0:
		# 	node_tree.use_fake_user = True
		node_modifier = curve_obj.modifiers.new(name="GeoNodes", type='NODES')
		node_modifier.node_group = node_tree

		curve_obj.ssx2_CurveMode = 'CAGE'
		curve_obj.ssx2_PatchProps.type = '1'
		curve_obj.ssx2_PatchProps.texMapPreset = '3'

		collection.objects.link(curve_obj)

		curve_obj.select_set(True)
		bpy.context.view_layer.objects.active = curve_obj

		if self.origin:
			bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')

		return {'FINISHED'}

class SSX2_OP_AddPatchMaterial(bpy.types.Operator):
	bl_idname = 'material.ssx2_add_patch_material'
	bl_label = "Patch Material"
	bl_description = 'Create a Patch Material'
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):

		obj = bpy.context.active_object

		append_path = templates_append_path
		material_name = "PatchMaterialAppend"
		material = bpy.data.materials.get(material_name)

		if material is None:
			print("Append Material: True")
			if not os.path.isfile(append_path):
				self.report({'ERROR'}, f"Failed to append {append_path}")
				return {'CANCELLED'}

			with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
				if material_name in data_from.materials:
					data_to.materials = [material_name]
				else:
					self.report({'ERROR'}, f"Failed to append material from {append_path}")
					return {'CANCELLED'}

		material = bpy.data.materials.get(material_name)
		# if material.users == 0:
		# 	material.use_fake_user = True
		# material = material.copy()
		material.name = "pch"
		obj.data.materials.clear()
		obj.data.materials.append(material)

		if obj.type == 'CURVE':
			cage_nodes = None
			for mod in obj.modifiers:
				if mod.type == 'NODES' and mod.node_group:
					if "CageLoftAppend" in mod.node_group.name:
						cage_nodes = mod.node_group
						break
			if cage_nodes is not None:
				mod["Input_7"] = material
			else:
				self.report({'WARNING'}, "Modifier is missing. Modifiers > Geometry Nodes > CageLoftAppend")

		return {'FINISHED'}

class SSX2_OP_SendMaterialToModifier(bpy.types.Operator):
	bl_idname = 'material.ssx2_send_material_to_modifier'
	bl_label = "Send Material to Modifier"
	bl_description = 'Sends material to modifier'
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):

		obj = bpy.context.active_object
		active_material = obj.active_material

		if active_material is not None:
			cage_nodes = None
			for mod in obj.modifiers:
				if mod.type == 'NODES' and mod.node_group:
					if "CageLoftAppend" in mod.node_group.name:
						cage_nodes = mod.node_group
						break
			if cage_nodes is not None:
				mod["Input_7"] = active_material
				obj.data.materials.clear()
				obj.data.materials.append(active_material)
			else:
				self.report({'WARNING'}, "Modifier is missing. Modifiers > Geometry Nodes > CageLoftAppend")
				return {'CANCELLED'}
		return {'FINISHED'}


class SSX2_OP_AddControlGrid(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_control_grid'
	bl_label = "Control Grid"
	bl_description = 'Generate a control grid patch'
	bl_options = {'REGISTER', 'UNDO'}

	origin: bpy.props.BoolProperty(name='Origin at Center')
	
	def execute(self, context):
		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		collection = bpy.data.collections.get("Patches")

		if collection is None:
			self.report({'WARNING'}, "'Patches' Collection not found!")
			collection = bpy.context.collection

		append_path = templates_append_path
		material_name = "PatchMaterialAppend"
		node_tree_name = "GridTesselateAppend"
		material = bpy.data.materials.get(material_name)
		node_tree = bpy.data.node_groups.get(node_tree_name)

		print("Append Material:", material is None)
		print("Append Node Tree:", node_tree is None)

		if not os.path.isfile(append_path):
			self.report({'ERROR'}, f"Failed to append {append_path}")
			return {'CANCELLED'}

		with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
			if node_tree is None:
				if node_tree_name in data_from.node_groups:
					data_to.node_groups = [node_tree_name]
				else:
					self.report({'ERROR'}, f"Failed to append geonodes from {append_path}")
					return {'CANCELLED'}
			if material is None:
				if material_name in data_from.materials:
					data_to.materials = [material_name]
				else:
					self.report({'ERROR'}, f"Failed to append material from {append_path}")
					return {'CANCELLED'}

		# I should just append grid from templates.blend

		#scale = (100 / bpy.context.scene.bx_WorldScale) + 14
		bpy.ops.mesh.primitive_grid_add(enter_editmode=False, size=10, #align='CURSOR', align='WORLD'
			x_subdivisions=3,
			y_subdivisions=3,
			location=(5, 5, 0),
			rotation=(0, 0, -1.57079632679)) # scale= doens't work. blender plz fix

		bpy.ops.transform.resize(value=(-1, 1, 1), orient_type='LOCAL', constraint_axis=(False, True, False))
		#orient_type='LOCAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='LOCAL'

		bpy.ops.object.transform_apply(location=True, rotation=True, scale=True) # sets origin to bottom left
		bpy.ops.object.editmode_toggle()
		bpy.ops.mesh.flip_normals()
		bpy.ops.object.editmode_toggle()

		grid = bpy.context.active_object
		collection_it_was_added_to = grid.users_collection[0]
		grid.location = bpy.context.scene.cursor.location

		props = grid.ssx2_PatchProps

		props.type = '1'
		props.isControlGrid = True
		props.texMapPreset = '3'
		props.useManualUV = True
		props.manualUV0 = (0.0, 0.0)
		props.manualUV1 = (0.0, 1.0)
		props.manualUV2 = (1.0, 0.0)
		props.manualUV3 = (1.0, 1.0)

		material = bpy.data.materials.get("pch")
		if material is None:
			material = bpy.data.materials.get(material_name)
			# if material.users == 0:
			# 	material.use_fake_user = True
			material = material.copy()
			material.name = "pch"
		grid.data.materials.append(material)

		node_tree = bpy.data.node_groups.get(node_tree_name)
		# if node_tree.users == 0:
		# 	node_tree.use_fake_user = True
		node_modifier = grid.modifiers.new(name="GeoNodes", type='NODES')
		node_modifier.node_group = node_tree
		node_modifier["Input_3"] = 1

		if collection_it_was_added_to.name != collection.name:
			collection_it_was_added_to.objects.unlink(grid)
			collection.objects.link(grid)

		
		if self.origin:
			bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')


		return {'FINISHED'}

class SSX2_OP_AddPatch(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_patch'
	bl_label = "Surface Patch"
	bl_description = 'Generate a surface patch'
	bl_options = {'REGISTER', 'UNDO'}

	origin: bpy.props.BoolProperty(name='Origin at Center')
	
	def execute(self, context):
		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		collection = bpy.data.collections.get("Patches")

		if collection is None:
			self.report({'WARNING'}, "'Patches' Collection not found!")
			collection = bpy.context.collection
			#return {'CANCELLED'}

		append_path = templates_append_path
		material_name = "PatchMaterialAppend"
		surface_name = "SurfPatchAppend"
		material = bpy.data.materials.get(material_name)
		surface = bpy.data.curves.get(surface_name)

		print("Append Material:", material is None)
		print("Append Surface:", surface is None)

		if not os.path.isfile(append_path):
			self.report({'ERROR'}, f"Failed to append {append_path}")
			return {'CANCELLED'}

		with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
			if surface is None:
				if surface_name in data_from.curves:
					data_to.curves = [surface_name]
				else:
					self.report({'ERROR'}, f"Failed to append surface from {append_path}")
					return {'CANCELLED'}
			if material is None:
				if material_name in data_from.materials:
					data_to.materials = [material_name]
				else:
					self.report({'ERROR'}, f"Failed to append material from {append_path}")
					return {'CANCELLED'}

		surface = bpy.data.curves.get(surface_name)
		print(surface)
		print(surface.users)
		# if surface.users == 0:
		# 	surface.use_fake_user = True
		surface = surface.copy()
		patch = bpy.data.objects.new("SurfPatch", surface)
		surface.name = patch.name#"SurfPatch"

		patch.location = bpy.context.scene.cursor.location
		patch.ssx2_PatchProps.type = '1'
		patch.ssx2_PatchProps.texMapPreset = '3'
		patch.ssx2_PatchProps.manualUV0 = (0.0, 0.0)
		patch.ssx2_PatchProps.manualUV1 = (0.0, 1.0)
		patch.ssx2_PatchProps.manualUV2 = (1.0, 0.0)
		patch.ssx2_PatchProps.manualUV3 = (1.0, 1.0)

		material = bpy.data.materials.get("pch")
		if material is None:
			material = bpy.data.materials.get(material_name)
			# if material.users == 0:
			# 	material.use_fake_user = True
			material = material.copy()
			material.name = "pch"
		patch.data.materials.append(material)
		collection.objects.link(patch)

		patch.select_set(True)
		bpy.context.view_layer.objects.active = patch

		if self.origin:
			bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')

		return {"FINISHED"}

class SSX2_OP_ToggleControlGrid(bpy.types.Operator):
	bl_idname = 'object.ssx2_toggle_control_grid'
	bl_label = "Toggle Control Grid"
	bl_description = 'Converts selection to a NURBS Patch or a Control Grid depending on active object'
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(self, context):
		#context.active_object # context.object
		active_object = context.active_object
		return (len(bpy.context.selected_objects) != 0) and (active_object is not None) and \
		(active_object.type == 'SURFACE' or active_object.ssx2_PatchProps.isControlGrid)

	def toggle_to_control_grid(self, context, objects_to_convert):
		# to_reselect = []

		append_path = templates_append_path
		node_tree_name = "GridTesselateAppend"
		node_tree = bpy.data.node_groups.get(node_tree_name)

		if node_tree is None:
			print("Append Node Tree: True")

			if not os.path.isfile(append_path):
				self.report({'ERROR'}, f"Failed to append {append_path}")
				return {'CANCELLED'}

			with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
				if node_tree_name in data_from.node_groups:
					data_to.node_groups = [node_tree_name]
				else:
					self.report({'ERROR'}, f"Failed to append geonodes from {append_path}")
					return {'CANCELLED'}

		node_tree = bpy.data.node_groups.get(node_tree_name)

		def temp_function_a():
			for old_obj in objects_to_convert:
				if old_obj.type != 'SURFACE':
					print("NOT SURFACE", old_obj.name)#obj.select_set(False)
					continue

				if len(old_obj.data.splines) == 0:
					self.report({'WARNING'}, f"{old_obj.name} is empty. Skipping.")
					self.warning_count += 1
					continue
				if len(old_obj.data.splines[0].points) != 16:
					self.report({'WARNING'}, f"{old_obj.name} does not have 16 points. Skipping.")
					self.warning_count += 1
					continue

				# print(obj.name)
				collection = old_obj.users_collection[0]
				old_name = old_obj.name
				old_props = old_obj.ssx2_PatchProps
				old_points = []
				uvs = []

				old_data = old_obj.data

				if len(old_obj.data.materials) > 0:
					old_material = old_obj.data.materials[0]
				else:
					old_material = None

				for spline in old_obj.data.splines:
					for p in spline.points:
						x, y, z, w = p.co# * context.scene.bx_WorldScale
						old_points.append((x, y, z))

				#uvs = [(uv[0], -uv[1]) for uv in uvs]
				uvs = patch_known_uvs_blender[0]

				new_obj = bpy.data.objects.get(old_name)
				if new_obj is None or new_obj.type != 'MESH':
					mesh = bpy.data.meshes.new(old_name)
					new_obj = bpy.data.objects.new(old_name, mesh)

				new_obj.data = set_patch_control_grid(mesh, old_points, uvs)
				if old_material is not None:
					new_obj.data.materials.append(old_material)

				node_modifier = new_obj.modifiers.new(name="GeoNodes", type='NODES')
				node_modifier.node_group = node_tree
				#node_modifier["Input_3"] = 1
				
				collection.objects.link(new_obj)

				new_obj.matrix_world = Matrix(old_obj.matrix_world)
				new_obj.color = old_obj.color
				new_obj_props = new_obj.ssx2_PatchProps
				new_obj_props.isControlGrid = True
				new_obj_props.type = old_props.type
				new_obj_props.showoffOnly = old_props.showoffOnly
				new_obj_props.fixU = old_props.fixU
				new_obj_props.fixV = old_props.fixV
				new_obj_props.texMapPreset = old_props.texMapPreset
				new_obj_props.useManualUV = old_props.useManualUV
				new_obj_props.manualUV0 = old_props.manualUV0
				new_obj_props.manualUV1 = old_props.manualUV1
				new_obj_props.manualUV2 = old_props.manualUV2
				new_obj_props.manualUV3 = old_props.manualUV3

				bpy.data.objects.remove(old_obj, do_unlink=True) # delete object
				if old_data.users == 0:
					bpy.data.curves.remove(old_data)
				new_obj.name = old_name

				


				# convert method
				# obj.select_set(True)

				# bpy.ops.object.mode_set(mode = "EDIT")
				# bpy.ops.curve.select_all(action='SELECT')
				# bpy.ops.curve.delete(type='VERT')
				# bpy.ops.object.mode_set(mode = "OBJECT")
				# #bpy.ops.curve.select_all(action='DESELECT')
				# bpy.ops.object.convert(target='MESH')#, keep_original=False)
				# bpy.ops.object.mode_set(mode = "OBJECT")
				# bpy.ops.object.select_all(action = "DESELECT")

				# obj.ssx2_PatchProps.type = patch_type
				# obj.ssx2_PatchProps.showoffOnly = patch_showoff_only
				# obj.ssx2_PatchProps.isControlGrid = True
				
				# mesh = obj.data

				# set_patch_control_grid(mesh, patch_points, patch_uvs)
				# break
				# mesh.materials.append(patch_material)
				# obj.select_set(False)

				self.objects_toggled_count += 1
				new_obj.select_set(True)
		
		run_without_update(temp_function_a)

	def toggle_to_patch(self, context, objects_to_convert):
		to_reselect = []

		def temp_function_b():
			for old_obj in objects_to_convert:
				if len(old_obj.data.vertices) != 16:
					print(old_obj.name, "does not have 16 vertices.")
					continue
				#print(old_obj.name)

				collection = old_obj.users_collection[0]

				old_name = old_obj.name
				old_props = old_obj.ssx2_PatchProps
				old_points = []

				old_data = old_obj.data
				
				if len(old_obj.data.materials) > 0:
					old_material = old_obj.data.materials[0]
				else:
					old_material = None
				
				#grid_uvs = [(uv[0], -uv[1] ) for uv in get_uvs_per_verts(old_obj)]
				#grid_uv_square = [grid_uvs[0], grid_uvs[12], grid_uvs[3], grid_uvs[15]] # 0 12 3 15
				#existing_patch_uv_idx = existing_patch_uvs(grid_uv_square) # problem causer 1

				for vtx in old_obj.data.vertices:
					old_points.append((vtx.co.x, vtx.co.y, vtx.co.z, 1.0))

				new_obj = set_patch_object(old_points, old_name, collection=collection.name)
				if old_material is not None:
					new_obj.data.materials.append(old_material)

				new_obj.matrix_world = Matrix(old_obj.matrix_world)
				new_obj.color = old_obj.color
				new_obj_props = new_obj.ssx2_PatchProps
				new_obj_props.isControlGrid = False
				new_obj_props.type = old_props.type
				new_obj_props.showoffOnly = old_props.showoffOnly
				new_obj_props.fixU = old_props.fixU
				new_obj_props.fixV = old_props.fixV
				new_obj_props.texMapPreset = old_props.texMapPreset
				new_obj_props.useManualUV = old_props.useManualUV
				new_obj_props.manualUV0 = old_props.manualUV0
				new_obj_props.manualUV1 = old_props.manualUV1
				new_obj_props.manualUV2 = old_props.manualUV2
				new_obj_props.manualUV3 = old_props.manualUV3

				self.objects_toggled_count += 1
				to_reselect.append(new_obj)

				bpy.data.objects.remove(old_obj, do_unlink=True) # delete object
				if old_data.users == 0:
					bpy.data.meshes.remove(old_data)
				new_obj.name = old_name
				# i moved delete further down so name has to be set again or itll have .00* on the end

			for obj in to_reselect:
				obj.select_set(True)
		run_without_update(temp_function_b)

	def execute(self, context):
		selected_objects = context.selected_objects
		active_object = context.active_object
		active_object_name = active_object.name
		objects_to_convert = []

		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		self.objects_toggled_count = 0
		self.warning_count = 0

		if active_object.type == 'SURFACE':
			print("SURFACE -> CONTROL GRID\n")

			for obj in selected_objects:
				if obj.type != 'SURFACE':
					continue
				objects_to_convert.append(obj)

			self.toggle_to_control_grid(context, objects_to_convert)

		elif active_object.type == 'MESH' and active_object.ssx2_PatchProps.isControlGrid: #
			print("CONTROL GRID -> SURFACE\n")

			#'ssx2_PatchProps.isControlGrid' in obj.keys():
			#active_object.ssx2_PatchProps.isControlGrid

			for obj in selected_objects:
				if obj.type != 'MESH':
					continue
				if obj.ssx2_PatchProps.isControlGrid:
					objects_to_convert.append(obj)

			self.toggle_to_patch(context, objects_to_convert)
		else:
			self.report({'WARNING'}, "Active object is not a PATCH or CONTROL GRID")

		bpy.context.view_layer.objects.active = bpy.data.objects.get(active_object_name) # set active object again

		print("\nFinished")

		self.report({'INFO'}, f"Toggled {self.objects_toggled_count} objects")

		if self.warning_count:
			self.report({'WARNING'}, f"Warnings occurred. Click here to view.")
			
		return {"FINISHED"}

class SSX2_OP_CopyMaterialToSelected(bpy.types.Operator):
	bl_idname = "object.ssx2_copy_material"
	bl_label = "Copy Material to Selected"
	bl_description = "Copy material from active object to all selected objects"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		active_object = context.active_object
		return ((len(bpy.context.selected_objects) != 0) and (active_object is not None) and 
		(active_object.type == 'SURFACE' or active_object.ssx2_PatchProps.isControlGrid
		or active_object.ssx2_CurveMode == 'CAGE'))
	
	def execute(self, context):
		active_object = context.active_object
		selected_objects = context.selected_objects

		new_mat = None

		if active_object.ssx2_CurveMode == 'CAGE':
			cage_nodes = None
			for mod in active_object.modifiers:
				if mod.type == 'NODES' and mod.node_group:
					if "CageLoftAppend" in mod.node_group.name:
						cage_nodes = mod.node_group
						break
			if cage_nodes is not None:
				new_mat = mod["Input_7"]
			else:
				self.report({'WARNING'}, "Modifier is missing on active object")
				return {'CANCELLED'}
		
		if new_mat is None:
			if len(active_object.data.materials) == 0:
				new_mat = None
				# self.report({'ERROR'}, "Material is missing on active object")
				# return {'CANCELLED'}
			else:
				new_mat = active_object.data.materials[0]

		for obj in selected_objects:
			if ((obj.type == 'SURFACE' or 
			obj.ssx2_PatchProps.isControlGrid or 
			obj.ssx2_CurveMode == 'CAGE')):
				obj.data.materials.clear()
				if new_mat is not None:
					obj.data.materials.append(new_mat)

				if obj.ssx2_CurveMode == 'CAGE':
					cage_nodes = None
					for mod in obj.modifiers:
						print(mod)
						if mod.type == 'NODES' and mod.node_group:
							if "CageLoftAppend" in mod.node_group.name:
								cage_nodes = mod.node_group
								break
					if cage_nodes is not None:
						mod["Input_7"] = new_mat
					else:
						self.report({'WARNING'}, f"Modifier is missing on {obj.name}")
						return {'CANCELLED'}

		return {'FINISHED'}

class SSX2_OP_CopyPatchUVsToSelected(bpy.types.Operator):
	bl_idname = "object.ssx2_patches_copy_uvs"
	bl_label = "Copy UVs to Selected"
	bl_description = "Copy UVs from active object to all selected objects"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		active_object = context.active_object
		return ((len(bpy.context.selected_objects) != 0) and (active_object is not None) and 
		(active_object.type == 'SURFACE' or active_object.ssx2_PatchProps.isControlGrid
		or active_object.ssx2_CurveMode == 'CAGE'))

	def execute(self, context):
		active_object = context.active_object
		selected_objects = context.selected_objects
		patch_props = active_object.ssx2_PatchProps

		useManualUVs = patch_props.useManualUV
		manualUV0 = patch_props.manualUV0
		manualUV1 = patch_props.manualUV1
		manualUV2 = patch_props.manualUV2
		manualUV3 = patch_props.manualUV3
		texMapPreset = patch_props.texMapPreset

		for obj in selected_objects:
			if ((obj.type == 'SURFACE' or 
			obj.ssx2_PatchProps.isControlGrid or 
			obj.ssx2_CurveMode == 'CAGE')):
				obj.ssx2_PatchProps.useManualUV = useManualUVs
				obj.ssx2_PatchProps.manualUV0 = manualUV0
				obj.ssx2_PatchProps.manualUV1 = manualUV1
				obj.ssx2_PatchProps.manualUV2 = manualUV2
				obj.ssx2_PatchProps.manualUV3 = manualUV3
				obj.ssx2_PatchProps.texMapPreset = texMapPreset

		return {'FINISHED'}

class SSX2_OP_MergePatches(bpy.types.Operator):
	bl_idname = "object.ssx2_merge_patches"
	bl_label = "Merge Patches"
	bl_description = "Join patch objects together and merge the closest points."
	bl_options = {'REGISTER', 'UNDO'}

	keep_overhang_handles: bpy.props.BoolProperty(name="Keep Overhang Handles", default=False)
	auto_align_handles: bpy.props.BoolProperty(name="Auto Align Handles", default=True)

	@classmethod
	def poll(self, context):
		active_object = context.active_object
		if active_object:
			if active_object.mode == 'EDIT':
				return
			# return ((len(bpy.context.selected_objects) != 0) and (active_object is not None) and 
			# (active_object.type == 'SURFACE' or active_object.ssx2_PatchProps.isControlGrid
			# or active_object.ssx2_CurveMode == 'CAGE'))
			return ((len(bpy.context.selected_objects) != 0) and (active_object is not None) and 
			(active_object.ssx2_CurveMode == 'CAGE'))

	def execute(self, context):
		active_object = context.active_object
		selected_objects = context.selected_objects
		patch_props = active_object.ssx2_PatchProps

		num_objects = len(selected_objects)

		if num_objects < 2:
			self.report({'WARNING'}, "You need to select 2 objects")
			return {'CANCELLED'}

		if num_objects > 2:
			self.report({'WARNING'}, "Can only merge 2 objects")
			return {'CANCELLED'}

		
		if selected_objects[0] == active_object:
			selected_object = selected_objects[1]
		else:
			selected_object = selected_objects[0]


		cage_is_valid = check_valid_spline_cage(active_object)
		if not cage_is_valid[0]:
			self.report({'WARNING'}, cage_is_valid[1])

		cage_is_valid = check_valid_spline_cage(selected_object)
		if not cage_is_valid[0]:
			self.report({'WARNING'}, cage_is_valid[1])

		if len(active_object.data.splines) != len(selected_object.data.splines):
			self.report({'WARNING'}, "Both cages need to have the same number of splines")
			return {'CANCELLED'}


		obj_a_pos = active_object.location
		obj_b_pos = selected_object.location

		obj_a_mtx = active_object.matrix_world
		obj_b_mtx = selected_object.matrix_world
		obj_a_mtx_inv = active_object.matrix_world.inverted()
		
		obj_a_num_points = len(active_object.data.splines[0].bezier_points)
		obj_b_num_points = len(selected_object.data.splines[0].bezier_points)

		obj_a_pt0 = active_object.data.splines[0].bezier_points[0].co + obj_a_pos
		obj_a_pt1 = active_object.data.splines[0].bezier_points[obj_a_num_points - 1].co + obj_a_pos
		obj_b_pt0 = selected_object.data.splines[0].bezier_points[0].co + obj_b_pos
		obj_b_pt1 = selected_object.data.splines[0].bezier_points[obj_b_num_points - 1].co + obj_b_pos
		

		merge_at_end = (obj_a_pt1 - obj_b_pt0).length < (obj_a_pt0 - obj_b_pt1).length
		# end is the last point of the active object's spline

		error_threshold = 0.001
		
		if merge_at_end:
			for i, spline_b in enumerate(selected_object.data.splines):
				spline_a = active_object.data.splines[i]
				spline_a.bezier_points.add(obj_b_num_points - 1)

				if not self.keep_overhang_handles:
					a_bez = spline_a.bezier_points[obj_a_num_points - 1]
					b_bez = spline_b.bezier_points[0]

					if self.auto_align_handles:
						temp = b_bez.handle_right - b_bez.co
						a_direction = -(a_bez.handle_left - a_bez.co).normalized()
						a_bez.handle_right = a_bez.co + (a_direction * temp.length)
						a_bez.handle_right_type = 'ALIGNED'

					else:
						a_direction = ((obj_a_mtx @ a_bez.handle_left) - (obj_a_mtx @ a_bez.co)).normalized()
						b_direction = ((obj_b_mtx @ b_bez.handle_left) - (obj_b_mtx @ b_bez.co)).normalized()

						error_check = 0

						error_check += abs(b_direction.x - a_direction.x) < error_threshold
						error_check += abs(b_direction.y - a_direction.y) < error_threshold
						error_check += abs(b_direction.z - a_direction.z) < error_threshold

						if error_check == 3: # close enough for alignment
							temp = b_bez.handle_right - b_bez.co
							a_direction = -(a_bez.handle_left - a_bez.co).normalized()
							a_bez.handle_right = a_bez.co + (a_direction * temp.length)

							a_bez.handle_right_type = b_bez.handle_right_type

						else:
							a_bez.handle_right_type = 'FREE'

							temp = (obj_b_mtx @ b_bez.handle_right) - (obj_b_mtx @ b_bez.co)
							b_direction = temp.normalized()
							a_bez.handle_right = a_bez.co + (b_direction * temp.length)


				for j in range(obj_b_num_points - 1):
					# print(j, "  ", j + 1, "  ", j + obj_a_num_points)
					a_bez = spline_a.bezier_points[j + obj_a_num_points]
					b_bez = spline_b.bezier_points[j + 1]

					pt_b_co = obj_b_mtx @ b_bez.co
					pt_b_handle_left = obj_b_mtx @ b_bez.handle_left
					pt_b_handle_right = obj_b_mtx @ b_bez.handle_right

					a_bez.co = obj_a_mtx_inv @ pt_b_co
					a_bez.handle_left = obj_a_mtx_inv @ pt_b_handle_left
					a_bez.handle_right = obj_a_mtx_inv @ pt_b_handle_right
					a_bez.handle_left_type = b_bez.handle_left_type
					a_bez.handle_right_type = b_bez.handle_right_type

		else:
			for i, spline_a in enumerate(active_object.data.splines):
				spline_b = selected_object.data.splines[i]

				saved_root_left = ()
				saved_root_left_type = ()

				if not self.keep_overhang_handles:
					a_bez = spline_a.bezier_points[0]
					b_bez = spline_b.bezier_points[obj_b_num_points - 1]

					if self.auto_align_handles:
						temp = b_bez.handle_left - b_bez.co
						a_direction = -(a_bez.handle_left - a_bez.co).normalized()

						saved_root_left = a_bez.co + (a_direction * temp.length)
						saved_root_left_type = 'ALIGNED'

					else:
						a_direction = ((obj_a_mtx @ a_bez.handle_right) - (obj_a_mtx @ a_bez.co)).normalized()
						b_direction = ((obj_b_mtx @ b_bez.handle_right) - (obj_b_mtx @ b_bez.co)).normalized()

						error_check = 0

						error_check += abs(b_direction.x - a_direction.x) < error_threshold
						error_check += abs(b_direction.y - a_direction.y) < error_threshold
						error_check += abs(b_direction.z - a_direction.z) < error_threshold

						if error_check == 3: # close enough for alignment
							temp = b_bez.handle_left - b_bez.co
							a_direction = -(a_bez.handle_right - a_bez.co).normalized()
							saved_root_left = a_bez.co + (a_direction * temp.length)
							saved_root_left_type = b_bez.handle_left_type

						else:
							saved_root_left = b_bez.handle_left - b_bez.co
							saved_root_left = obj_b_mtx.to_3x3() @ saved_root_left
							saved_root_left = obj_a_mtx.to_3x3().inverted() @ saved_root_left
							saved_root_left = a_bez.co + saved_root_left
							saved_root_left_type = 'FREE'


				combined_bez_points = []
				for j in range(obj_b_num_points - 1):
					bez_point = spline_b.bezier_points[j]

					combined_bez_points.append(
						(
							obj_a_mtx_inv @ (obj_b_mtx @ bez_point.co),
							obj_a_mtx_inv @ (obj_b_mtx @ bez_point.handle_left),
							obj_a_mtx_inv @ (obj_b_mtx @ bez_point.handle_right),
							bez_point.handle_left_type,
							bez_point.handle_right_type,
							bez_point.radius,
							bez_point.tilt,
						)
					)

				for j in range(obj_a_num_points):
					bez_point = spline_a.bezier_points[j]
					combined_bez_points.append(
						(
							bez_point.co,
							bez_point.handle_left,
							bez_point.handle_right,
							bez_point.handle_left_type,
							bez_point.handle_right_type,
							bez_point.radius,
							bez_point.tilt,
						)
					)

				spline_a.bezier_points.add(obj_b_num_points - 1)

				for j, bez_point in enumerate(combined_bez_points):
					a_bez = spline_a.bezier_points[j]
					a_bez.co = bez_point[0]
					a_bez.handle_left = bez_point[1]
					a_bez.handle_right = bez_point[2]
					a_bez.handle_left_type = bez_point[3]
					a_bez.handle_right_type = bez_point[4]
					a_bez.radius = bez_point[5]
					a_bez.tilt = bez_point[6]


				if not self.keep_overhang_handles:
					a_bez = spline_a.bezier_points[obj_b_num_points - 1]
					a_bez.handle_left_type = saved_root_left_type
					a_bez.handle_left = saved_root_left

		bpy.data.objects.remove(selected_object)

		return {'FINISHED'}

class SSX2_OP_AddCageVGuide(bpy.types.Operator):
	bl_idname = "object.ssx2_add_v_guide"
	bl_label = ""
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		active_object = context.active_object
		# return ((len(bpy.context.selected_objects) != 0) and (active_object is not None) and 
		# (active_object.type == 'SURFACE' or active_object.ssx2_PatchProps.isControlGrid
		# or active_object.ssx2_CurveMode == 'CAGE'))
		return ((len(bpy.context.selected_objects) != 0) and 
			(active_object is not None) and 
			(active_object.ssx2_CurveMode == 'CAGE'))

	def execute(self, context):
		active_obj = context.active_object

		if active_obj.ssx2_CurveMode != 'CAGE':
			return {'CANCELLED'}
		# if active_obj.mode != 'EDIT':
		# 	return {'CANCELLED'}

		splines = active_obj.data.splines

		# new_splines = [[] for i in range( len(splines[0].bezier_points) * 3)]
		# print(len(splines[0].bezier_points) * 3)
		linear_list = []
		
		for i, spline in enumerate(splines):
			speen = []
			for j, p in enumerate(spline.bezier_points):
				speen.append(p.handle_left)
				speen.append(p.co)
				speen.append(p.handle_right)
			linear_list.append(speen)

		num_splines = len(splines)

		curve_data = bpy.data.curves.new("Patch V Guide", type='CURVE')
		curve_data.dimensions = '3D'

		if num_splines == 2:
			for i in range(len(splines[0].bezier_points) * 3):
				spline = curve_data.splines.new(type='BEZIER')
				spline.bezier_points.add(1)
				spline.resolution_u = 7

				p0_co = linear_list[0][i]
				p1_co = linear_list[1][i]

				# right handle
				a = p1_co - p0_co
				p0_hr = a / 3
				p0_hr = p0_hr + p0_co

				# left handle
				a = p0_hr - p0_co
				p0_hl = a * -1
				p0_hl = p0_hl + p0_co

				spline.bezier_points[0].handle_left =  p0_hl
				spline.bezier_points[0].co =           p0_co
				spline.bezier_points[0].handle_right = p0_hr
				spline.bezier_points[0].handle_left_type = 'ALIGNED'
				spline.bezier_points[0].handle_right_type = 'ALIGNED'

				# left handle
				a = p1_co - p0_co
				p1_hl = a / 1.5
				p1_hl = p1_hl + p0_co

				# right handle
				a = p1_hl - p1_co
				p1_hr = a * -1
				p1_hr = p1_hr + p1_co

				spline.bezier_points[1].handle_left  = p1_hl
				spline.bezier_points[1].co =           p1_co
				spline.bezier_points[1].handle_right = p1_hr
				spline.bezier_points[1].handle_left_type = 'ALIGNED'
				spline.bezier_points[1].handle_right_type = 'ALIGNED'

		elif num_splines == 4:
			for i in range(len(splines[0].bezier_points) * 3):
				spline = curve_data.splines.new(type='BEZIER')
				spline.bezier_points.add(1)
				spline.resolution_u = 7

				p0_co = linear_list[0][i]
				p0_hr = linear_list[1][i]

				a = p0_hr - p0_co
				p0_hl = a * -1
				p0_hl = p0_hl + p0_co

				spline.bezier_points[0].handle_left =  p0_hl
				spline.bezier_points[0].co =           p0_co
				spline.bezier_points[0].handle_right = p0_hr
				spline.bezier_points[0].handle_left_type = 'ALIGNED'
				spline.bezier_points[0].handle_right_type = 'ALIGNED'

				p1_hl = linear_list[2][i]
				p1_co = linear_list[3][i]
				
				a = p1_hl - p1_co
				p1_hr = a * -1
				p1_hr = p1_hr + p1_co

				spline.bezier_points[1].handle_left  = p1_hl
				spline.bezier_points[1].co =           p1_co
				spline.bezier_points[1].handle_right = p1_hr
				spline.bezier_points[1].handle_left_type = 'ALIGNED'
				spline.bezier_points[1].handle_right_type = 'ALIGNED'

		elif num_splines == 6:
			for i in range(len(splines[0].bezier_points) * 3):
				spline = curve_data.splines.new(type='BEZIER')
				spline.bezier_points.add(2)
				spline.resolution_u = 7

				p0_co = linear_list[0][i] # 1st new point
				p0_hr = linear_list[1][i]
				p1_hl = linear_list[2][i]
				p1_co = (linear_list[2][i] + linear_list[3][i]) / 2 # 2nd new point
				p1_hr = linear_list[3][i]
				p2_hl = linear_list[4][i]
				p2_co = linear_list[5][i] # 3rd new point

				a = p0_hr - p0_co
				p0_hl = a * -1
				p0_hl = p0_hl + p0_co

				spline.bezier_points[0].handle_left =  p0_hl
				spline.bezier_points[0].co =           p0_co
				spline.bezier_points[0].handle_right = p0_hr
				spline.bezier_points[0].handle_left_type = 'ALIGNED'
				spline.bezier_points[0].handle_right_type = 'ALIGNED'

				spline.bezier_points[1].handle_left  = p1_hl
				spline.bezier_points[1].co =           p1_co
				spline.bezier_points[1].handle_right = p1_hr
				spline.bezier_points[1].handle_left_type = 'ALIGNED'
				spline.bezier_points[1].handle_right_type = 'ALIGNED'

				a = p2_hl - p2_co
				p2_hr = a * -1
				p2_hr = p2_hr + p2_co

				spline.bezier_points[2].handle_left  = p2_hl
				spline.bezier_points[2].co =           p2_co
				spline.bezier_points[2].handle_right = p2_hr
				spline.bezier_points[2].handle_left_type = 'ALIGNED'
				spline.bezier_points[2].handle_right_type = 'ALIGNED'

		curve_object = bpy.data.objects.new("Patch V Guide", curve_data)
		scene_collection = bpy.context.scene.collection
		scene_collection.objects.link(curve_object)

		curve_object.matrix_world = active_obj.matrix_world

		return {'FINISHED'}



class SSX2_OP_Patch_Slide_V(bpy.types.Operator):
	bl_idname = "object.ssx2_slide_v"
	bl_label = "Slide V"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(self, context):
		obj = context.active_object
		if obj is None:
			return False
		elif context.active_object.mode == 'EDIT':
			if obj.type == 'CURVE':
				return True

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._handle = None
		self.all_coords = []
		self.all_selected_co = []
		self.all_target_co = []
		self.all_slide_co = []
		self.all_selected_indices = []

		self.target_spline_idx = None
		self.num_selected = -1
		
		self.cursor_initial = Vector()
		self.cursor_offset = Vector()
		#self.cur_init_x = 0
		#self.cur_global_x = 0.0
		self.CUR_SPEED_DEFAULT = 0.02
		self.CUR_SPEED_SLOWED = 0.002
		self.cur_speed = self.CUR_SPEED_DEFAULT
		
		self.obj = None
		self.dat = None
		self.mtx = Matrix()
		
		self.clamp_mode = False

	def invoke(self, context, event):
		print("\nStarting")
		
		self.obj = bpy.context.active_object
		self.mtx = self.obj.matrix_world
		
		if not self.obj.type == 'CURVE':
			self.report({'WARNING'}, "Not a curve object!")
			return {'CANCELLED'}
		
		self.dat = self.obj.data
		self.all_coords = [self.mtx @ p.co for spline in self.dat.splines for p in spline.bezier_points]
		
		
		if len(self.all_coords) == 0:
			self.report({'WARNING'}, "No Bézier points found!")
			return {'CANCELLED'}
		
		num_splines = len(self.dat.splines)
		num_u = len(self.dat.splines[0].bezier_points)

		found_selected = False
		for i, spline in enumerate(self.dat.splines):
			for j, p in enumerate(spline.bezier_points):
				if p.select_control_point:
					self.all_selected_co.append(p.co)
					self.all_selected_indices.append(j)
					self.selected_spline_index = i
					
					if len(self.dat.splines) < 2:
						self.report({'WARNING'}, "Needs at least 2 Bézier splines to work.")
						return {'CANCELLED'}

					if i == 0:
						self.all_target_co.append(self.dat.splines[1].bezier_points[j].co)
						self.target_spline_idx = 1
					elif i == 1:
						self.all_target_co.append(self.dat.splines[0].bezier_points[j].co)
						self.target_spline_idx = 0
					elif i == 2:
						self.all_target_co.append(self.dat.splines[3].bezier_points[j].co)
						self.target_spline_idx = 3
					elif i == 3:
						self.all_target_co.append(self.dat.splines[2].bezier_points[j].co)
						self.target_spline_idx = 2
					else:
						self.report({'WARNING'}, "Too many splines. Not supported yet.")
						return {'CANCELLED'}

					found_selected = True

				if found_selected and j == num_u - 1:
					break
			
			if found_selected:
				break
		
		if not found_selected:
			self.report({'WARNING'}, "No points selected!")
			return {'CANCELLED'}
		
		self.all_slide_co = [co for co in self.all_selected_co]
		self.num_selected = len(self.all_selected_co)

		context.area.header_text_set(f"(C) Clamp: {self.clamp_mode}")
		context.window.cursor_modal_set("SCROLL_X")

		# for window in bpy.context.window_manager.windows:
		# 	self.screen_width, self.screen_height = window.width, window.height
		# 	print(self.screen_width, self.screen_height)
		self.screen_width = context.window.width
		self.screen_height = context.window.height
		context.window.cursor_warp(self.screen_width//2, self.screen_height//2)

		#self.cursor_initial = Vector((event.mouse_x, event.mouse_y, 0.0))
		self.cursor_initial = Vector((self.screen_width // 2, self.screen_height // 2, 0.0))
		#self.cur_init_x = event.mouse_x
		#self.cur_global_x = self.cur_init_x - event.mouse_x
		#self.prev_x = event.mouse_x


		biggest_distance = 0.0
		self.biggest_distance_index = 0
		for i, sel_co in enumerate(self.all_selected_co):
			tar_co = self.all_target_co[i]

			distance = (tar_co - sel_co).length
			print("temp distance:", distance)
			if distance > biggest_distance:
				biggest_distance = distance
				self.biggest_distance_index = i
				print("Set new biggest")

		self.biggest_selected = self.all_selected_co[self.biggest_distance_index]
		self.biggest_target = self.all_target_co[self.biggest_distance_index]
		self.biggest_direction = (self.biggest_target - self.biggest_selected).normalized()

		print("\tDistance:", biggest_distance)
		print("\tDirection:", self.biggest_direction)

		
		if context.area.type == 'VIEW_3D':
			args = (self, )
			self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback, args, 'WINDOW', 'POST_VIEW')
			context.window_manager.modal_handler_add(self)
			context.area.tag_redraw()
			return {'RUNNING_MODAL'}
		else:
			self.report({'ERROR'}, "3D Viewport not found")
			return {'CANCELLED'}



	def modal(self, context, event):
		context.window.cursor_modal_set("SCROLL_X")

		if event.type in {'MOUSEMOVE', 'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'NDOF_MOTION'}:
			self.cursor_offset = (self.cursor_initial - Vector((event.mouse_x, event.mouse_y, 0.0))) * self.cur_speed#0.02
			
			cur_offset = self.cursor_offset.x * self.calc_flip_offset(bpy.context)
			
			temp_slide = self.biggest_selected + (self.biggest_direction * cur_offset)

			if self.clamp_mode:
				distance_to_target = (self.biggest_target - self.biggest_selected).length
				#clamped_offset = max(min(cur_offset, distance_to_target), 0)
				clamped_offset = min(cur_offset, distance_to_target)
				temp_slide = self.biggest_selected + self.biggest_direction * clamped_offset


			A = self.biggest_selected
			B = temp_slide
			C = self.biggest_target

			AC = C - A
			AB = B - A

			_lensquared = AC.length_squared

			if _lensquared == 0.0:
				_lensquared = 1.0

			t = AB.dot(AC) / _lensquared


			for i in range(self.num_selected):
				selected_index = self.all_selected_indices[i]

				bez_A = self.dat.splines[self.selected_spline_index].bezier_points[selected_index]
				bez_B = self.dat.splines[self.target_spline_idx].bezier_points[selected_index]
				
				new_co_local = bez_A.co - bez_B.co
				self.all_slide_co[i] = self.mtx @ (bez_A.co + (-new_co_local * t))


			
			context.area.tag_redraw()
			

			# mouse cursor wrap around screen
			if False:

				# this warp method is inconsistent
				# try the ctypes method.
				# may be able to get the blender window position and size with
				# context.window
				
				window = context.window
				screen_width = window.width
				screen_height = window.height
				mouse_x = event.mouse_x
				mouse_y = event.mouse_y
				warp_margin = 2

				new_x, new_y = mouse_x, mouse_y
				wrapped = False

				if mouse_x <= warp_margin:
					new_x = screen_width - warp_margin - 1
					wrapped = True
				elif mouse_x >= screen_width - warp_margin:
					new_x = warp_margin + 1
					wrapped = True

				if mouse_y <= warp_margin:
					new_y = screen_height - warp_margin - 1
					wrapped = True
				elif mouse_y >= screen_height - warp_margin:
					new_y = warp_margin + 1
					wrapped = True

				if wrapped:
					context.window.cursor_warp(new_x, new_y)
				else:

					# this move method seems to have inconsistent speeds
					# either revert to the old method or find a new one

					# maybe every time theres a warp i should add the screen width to it

					# if event.mouse_x > self.prev_x:
					# 	self.cur_global_x += 1
					# elif event.mouse_x < self.prev_x:
					# 	self.cur_global_x -= 1
					# self.prev_x = event.mouse_x
					pass

			return {'PASS_THROUGH'}
		
		if event.type == 'C' and event.value == 'RELEASE':
			self.clamp_mode = not self.clamp_mode
			context.area.header_text_set(f"(C) Clamp: {self.clamp_mode}")

		if event.type == 'LEFT_SHIFT':
			if event.value == 'PRESS':
				self.cur_speed = self.CUR_SPEED_SLOWED
			elif event.value == 'RELEASE':
				self.cur_speed = self.CUR_SPEED_DEFAULT

		if event.type == 'RIGHTMOUSE' or event.type == 'ESC':
			self.clean_up(context)
			print("Cancelled")
			return {'CANCELLED'}

		if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
			self.clean_up(context)
			self.finish(context)
			return {'FINISHED'}

		return {'RUNNING_MODAL'}

	def finish(self, context):		
		self.biggest_selected = self.all_selected_co[self.biggest_distance_index]
		self.biggest_target = self.all_target_co[self.biggest_distance_index]
		biggest_slide = self.all_slide_co[self.biggest_distance_index]

		A = self.biggest_selected
		B = self.mtx.inverted() @ biggest_slide
		C = self.biggest_target

		AC = C - A
		AB = B - A

		_lensquared = AC.length_squared

		if _lensquared == 0.0:
			_lensquared = 1.0

		t = AB.dot(AC) / _lensquared


		for i, sel_co in enumerate(self.all_selected_co):

			selected_index = self.all_selected_indices[i]

			bez_A = self.dat.splines[self.selected_spline_index].bezier_points[selected_index]
			bez_B = self.dat.splines[self.target_spline_idx].bezier_points[selected_index]

			left_mode_initial = bez_A.handle_left_type
			right_mode_initial = bez_A.handle_right_type
			bez_A.handle_left_type = 'FREE'
			bez_A.handle_right_type = 'FREE'

			#bez_A.co = B
			new_co_local = bez_A.co - bez_B.co
			bez_A.co = bez_A.co + (-new_co_local * t)

			new_left_local = bez_A.handle_left - bez_B.handle_left
			bez_A.handle_left = bez_A.handle_left + (-new_left_local * t)

			new_right_local = bez_A.handle_right - bez_B.handle_right
			bez_A.handle_right = bez_A.handle_right + (-new_right_local * t)


			# have to switch to FREE and back otherwise blender
			# places the handles wherever it wants.

			bez_A.handle_left_type = left_mode_initial
			bez_A.handle_right_type = right_mode_initial


		print("Finished")


	def clean_up(self, context):
		context.area.header_text_set(None)
		#context.window.cursor_modal_set("DEFAULT")
		context.window.cursor_modal_restore()

		if self._handle:
			bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
			self._handle = None
		context.area.tag_redraw()

	def calc_flip_offset(self, context):
		region = context.region
		rv3d = context.region_data

		if region and rv3d:
			sel_screen_co = view3d_utils.location_3d_to_region_2d(region, rv3d, self.mtx @ self.biggest_selected)
			tar_screen_co = view3d_utils.location_3d_to_region_2d(region, rv3d, self.mtx @ self.biggest_target)

			if sel_screen_co and tar_screen_co:
				if sel_screen_co.x > tar_screen_co.x:
					return 1.0

		# maybe i should make it so moving right is always towards target

		return -1.0


	def draw_callback(self, context):
		shader = gpu.shader.from_builtin('UNIFORM_COLOR')
		
		#combined = [self.mtx @ co for co in self.all_selected_co] + [self.mtx @ co for co in self.all_target_co]
		combined = [self.mtx @ co for co in self.all_target_co]
		batch = batch_for_shader(shader, 'POINTS', {"pos": combined})
		gpu.state.blend_set('ALPHA')
		gpu.state.point_size_set(5.0)
		shader.bind()
		shader.uniform_float("color", (0.0, 1.0, 0.0, 1.0)) # green
		batch.draw(shader)
		
		preview_batch = batch_for_shader(shader, 'POINTS', {"pos": self.all_slide_co})
		gpu.state.point_size_set(5.0)
		shader.bind()
		shader.uniform_float("color", (1.0, 0.0, 0.0, 1.0)) # red
		preview_batch.draw(shader)
		
		gpu.state.blend_set('NONE')







### PropertyGroups

class SSX2_PatchPropGroup(bpy.types.PropertyGroup):
	type: bpy.props.EnumProperty(name='Surface Type', items=enum_ssx2_surface_type)
	showoffOnly: bpy.props.BoolProperty(name="Showoff Only", default=False,
		description="Only shows up in Showoff modes")
	"""
	adjust_scale	 "Adjust UV scale"
	correct_border	 "Correct UV border"
	continious		 "Continious UV"
	resize			 "Resize UV"
	close_gap		 "Close UV gap"
	shrink_one_pixel "Shrink UV by 1 pixel"
	shrink           "Shrink UV"
	fix_uv_repeat    "Fix UV repeat"
	"""
	# texMap: bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0),
	# 	min=-3.14159265359,
	# 	max=3.14159265359,
	# 	subtype='EULER')
	texMapPreset: bpy.props.EnumProperty(name='Mapping Preset', items=enum_ssx2_patch_uv_preset, 
		update=update_patch_uv_preset,
		default='0')
	# patchFixUVRepeat: bpy.props.BoolProperty(name="Fix UV Repeat", default=False,
	# 	description="Scales up the UVs on export in order to remove the visible outline")
	fixU: bpy.props.BoolProperty(name="Fix U Seam",default=False,
		description="If there's a visible seam between the neighbor, this should hide it")
	fixV: bpy.props.BoolProperty(name="Fix V Seam",default=False,
		description="If there's a visible seam between the neighbor, this should hide it")
	useManualUV: bpy.props.BoolProperty(name="Manual UVs", default=False,
		description="Manually enter UV values",
		update=update_patch_uv_preset)
	manualUV0: bpy.props.FloatVectorProperty(default=(0.0, 0.0),size=2,subtype='XYZ', precision=4)
	manualUV1: bpy.props.FloatVectorProperty(default=(0.0, 1.0),size=2,subtype='XYZ', precision=4)
	manualUV2: bpy.props.FloatVectorProperty(default=(1.0, 0.0),size=2,subtype='XYZ', precision=4)
	manualUV3: bpy.props.FloatVectorProperty(default=(1.0, 1.0),size=2,subtype='XYZ', precision=4)

	isControlGrid: bpy.props.BoolProperty(name="Is Control Grid", default=False)

classes = (
	SSX2_OP_AddPatch,
	SSX2_OP_AddControlGrid,
	SSX2_OP_AddSplineCage,
	SSX2_OP_AddPatchMaterial,
	SSX2_OP_AddCageVGuide,
	SSX2_OP_Patch_Slide_V,
	SSX2_OP_SendMaterialToModifier,


	SSX2_PatchPropGroup,

	SSX2_OP_PatchUVEditor,
	SSX2_OP_ToggleControlGrid,
	SSX2_OP_CageToPatch,
	SSX2_OP_QuadToPatch,
	SSX2_OP_FlipSplineOrder,
	SSX2_OP_PatchSplit4x4,
	SSX2_OP_SelectSplineCageU,
	SSX2_OP_SelectSplineCageV,
	SSX2_OP_CopyMaterialToSelected,
	SSX2_OP_CopyPatchUVsToSelected,
	SSX2_OP_MergePatches,
	SSX2_OP_PatchUVTransform,
)

def ssx2_world_patches_register():
	for c in classes:
		register_class(c)
	
	bpy.types.Object.ssx2_PatchProps = bpy.props.PointerProperty(type=SSX2_PatchPropGroup)

def ssx2_world_patches_unregister():

	del bpy.types.Object.ssx2_PatchProps

	for c in classes:
		unregister_class(c)