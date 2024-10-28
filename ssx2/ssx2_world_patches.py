import bpy, bmesh
from bpy.utils import register_class, unregister_class
from mathutils import Vector, Matrix

from ..external.ex_utils import prop_split
from ..general.blender_get_data import get_uvs_per_verts#get_uvs
from ..general.blender_set_data import set_patch_material, set_patch_object, set_patch_control_grid
from ..general.bx_utils import *

from ..panels import SSX2_Panel
from .ssx2_world_io_in import *

# from .ssx2_world import ssx2_WorldUIProps

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


#import math

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

	def info(string):
		self.report({'INFO'}, string)

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

## Operators

class SSX2_OP_PatchSplit4x4(bpy.types.Operator):
	bl_idname = 'object.ssx2_patch_split_4x4'
	bl_label = "Split 4x4"
	bl_description = "Splits selected patch into 4x4 patches"
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

	keep_original: bpy.props.BoolProperty(name="Keep Original", default=False)
	apply_rotation: bpy.props.BoolProperty(name="Apply Rotation", default=True)
	apply_scale: bpy.props.BoolProperty(name="Apply Scale", default=True)
	
	@classmethod
	def poll(self, context):
		#context.active_object # context.object
		active_object = context.active_object
		return (len(bpy.context.selected_objects) != 0) and (active_object is not None) and \
		(active_object.type == 'SURFACE' or active_object.ssx2_PatchProps.isControlGrid)

	def execute(self, context):
		print("\nSplitting\n")

		# testing on active object first, make it do every patch and control grid after
		# use run_without... function when creating patches

		bpy.ops.object.mode_set(mode='OBJECT')
		collection = bpy.context.collection
		selected_objs = bpy.context.selected_objects # all selected objects
		active_obj = bpy.context.active_object
		bpy.context.view_layer.objects.active = None
		active_obj.select_set(False)

		if active_obj.ssx2_PatchProps.isControlGrid:
			print("Control Grid")
			return {'CANCELLED'}

		active_obj_name = active_obj.name
		active_obj_matrix = active_obj.matrix_local
		islands = active_obj.data.splines
		num_surfaces = len(islands)
		split_islands = []
		for j, s in enumerate(islands): # splines actually means internal surfaces/islands
			num_points = len(s.points)
			num_u = s.point_count_u
			num_v = s.point_count_v # 4
			all_spline_segs = []

			if num_v > num_u:
				num_u = num_v
				num_v = s.point_count_u # 4
			# ^ get the longest for 4x? strip to work
			# or actually try to split ?x? patches

			#print(num_u, num_u % 4)
			if num_points < 16:
				self.report({'WARNING'}, "INVALID 1")
				return {'CANCELLED'}
			elif num_points == 16:
				segment_points = [sp.co for sp in s.points[0:16]]
				all_spline_segs.append([segment_points])

			#return {'CANCELLED'}
			
			#print("points u/v",num_u, num_v)

			# Split into segments of 16 points

			segment_count = (num_u - 1) // 3
			segments = [[] for i in range(segment_count)]
			#print(f"\nsegments: {segment_count}\n")
			
			for v in range(4):#num_v):             # e.g 4v's each with 7u's
				#print("\nv:", v, v * num_u)

				v_start = v * num_u
				v_end = v_start + num_u

				this_spline = []
				for u in range(v_start, v_end, 3):
					segment_points = s.points[u:u + 4]
					segment_points = [sp.co for sp in segment_points]
					#print("u:", u, v_end-1, u + 4)
					this_spline.append(segment_points)

					if u + 4 >= v_end-1: # must break
						break

				all_spline_segs.append(this_spline)

			for segs in all_spline_segs:
				for k, seg in enumerate(segs):
					segments[k] += seg
			split_islands.append(segments)

			#break # only do first island, for now

		# for island in islands:
		# 	islands.remove(island)

		if len(split_islands) == 0:
			return {'CANCELLED'}

		to_reselect = []
		current_patch = 0
		for split_island in split_islands:
			for new_patch_points in split_island: # EACH ONE OBJECT WITH 16 POINTS (4x4)

				name = f"{active_obj_name}.s{current_patch}"
				current_patch += 1
				surface_data = bpy.data.curves.new(name, 'SURFACE') # Create Final Patch
				#surface_data = active_obj.data
				surface_data.dimensions = '3D'
				for i in range(4):
					spline = surface_data.splines.new(type='NURBS')
					spline.points.add(3) # one point already exists
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

				for j, p in enumerate(splines[0].points):
					nx, ny, nz, nw = new_patch_points[j]
					p.co = nx, ny, nz, 1.0

				bpy.ops.object.mode_set(mode = 'OBJECT')
				surface_object.matrix_local = active_obj_matrix
				to_reselect.append(surface_object)
				#surface_object.select_set(False)


		if not self.keep_original:
			bpy.data.objects.remove(active_obj)
			#bpy.data.curves.remove(active_obj.data) # also removes all objects that are linked. not always wanted

		for obj in to_reselect:
			obj.select_set(True)

		bpy.context.view_layer.objects.active = surface_object #obj
		if self.apply_rotation:
			bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
		if self.apply_scale:
			bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

		# bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

		self.report({'INFO'}, f"Split into {len(segments)} Patches")

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
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}
	
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
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}
	
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
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

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

		props.type = bpy.context.scene.ssx2_WorldUIProps.patchTypeChoice #'1'
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
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}

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
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}
	
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


class SSX2_PatchPanel(SSX2_Panel):
	bl_label = "BX Surface Patch"
	bl_idname = "OBJECT_PT_SSX2_Surface_Patch"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"
	bl_options = {"HIDE_HEADER"}

	@classmethod
	def poll(cls, context):
		return context.scene.bx_GameChoice == 'SSX2' and \
		(context.object is not None) # and context.object.type == 'SURFACE')
		# context.ssx2_PatchProps.isControlGrid # this doesn't work

	def draw(self, context):
		col = self.layout.column()
		obj = context.object
		# col.label(text=str(context.object.ssx2_PatchProps.isControlGrid))
		
		if obj.type == 'SURFACE' or obj.ssx2_PatchProps.isControlGrid or obj.ssx2_CurveMode == 'CAGE':
			prop_split(col, obj.ssx2_PatchProps, 'type', "Patch Type")
			#prop_split(col, obj.ssx2_PatchProps, 'useManualUV', "Manual Mapping")
			col.prop(obj.ssx2_PatchProps, 'showoffOnly', text="Showoff Only")
		# if context.object.type == 'SURFACE':
			# if obj.ssx2_CurveMode != 'CAGE':
			col.prop(obj.ssx2_PatchProps, 'fixU', text="Fix U Seam")
			col.prop(obj.ssx2_PatchProps, 'fixV', text="Fix V Seam")
			col.prop(obj.ssx2_PatchProps, 'useManualUV', text="Manual Mapping")
			if not obj.ssx2_PatchProps.useManualUV:
				prop_split(col, obj.ssx2_PatchProps, 'texMapPreset', "Mapping Preset")
				#col.prop(obj.ssx2_PatchProps, 'patchFixUVRepeat', text="Fix UV Repeat")
				#prop_split(col, obj.ssx2_PatchProps, "texMap", "Texture Mapping")
			col_split = col.split(factor=0.5)
			row = col.row()
			row_split = row.split(factor=0.5)
			if obj.ssx2_PatchProps.useManualUV:
				# col_split.prop(obj.ssx2_PatchProps, "manualUV0", text="")
				# col_split.prop(obj.ssx2_PatchProps, "manualUV1", text="")
				# row_split.prop(obj.ssx2_PatchProps, "manualUV2", text="")
				# row_split.prop(obj.ssx2_PatchProps, "manualUV3", text="")

				col_split.prop(obj.ssx2_PatchProps, "manualUV1", text="")
				col_split.prop(obj.ssx2_PatchProps, "manualUV3", text="")
				row_split.prop(obj.ssx2_PatchProps, "manualUV0", text="")
				row_split.prop(obj.ssx2_PatchProps, "manualUV2", text="")




def update_patch_uv_preset(self, context):
	self.texMap = patch_tex_maps[int(self.texMapPreset)]
	# update manual uvs too


class SSX2_PatchPropGroup(bpy.types.PropertyGroup):
	type: bpy.props.EnumProperty(name='Surface Type', items=enum_ssx2_surface_type)
	showoffOnly: bpy.props.BoolProperty(name="Showoff Only", default=False,
		description="Only shows up in Showoff modes.")
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
	# texMap: bpy.props.BoolProperty(name="Manual UVs", default=False,
	# 	description="Manually enter UV values. Cannot be previewed")
	texMap: bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0),
		min=-3.14159265359,
		max=3.14159265359,
		subtype='EULER')
	texMapPreset: bpy.props.EnumProperty(name='Mapping Preset', items=enum_ssx2_patch_uv_preset, 
		update=update_patch_uv_preset,
		default='0')
	# patchFixUVRepeat: bpy.props.BoolProperty(name="Fix UV Repeat", default=False,
	# 	description="Scales up the UVs on export in order to remove the visible outline")
	fixU: bpy.props.BoolProperty(name="Fix U Seam",default=False,description="")
	fixV: bpy.props.BoolProperty(name="Fix V Seam",default=False,description="")
	useManualUV: bpy.props.BoolProperty(name="Manual UVs", default=False,
		description="Manually enter UV values. Cannot be previewed!")
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
	SSX2_OP_SendMaterialToModifier,

	SSX2_PatchPanel,
	SSX2_PatchPropGroup,

	SSX2_OP_ToggleControlGrid,
	SSX2_OP_CageToPatch,
	SSX2_OP_FlipSplineOrder,
	SSX2_OP_PatchSplit4x4,
)

def ssx2_world_patches_register():
	for c in classes:
		register_class(c)
	
	bpy.types.Object.ssx2_PatchProps = bpy.props.PointerProperty(type=SSX2_PatchPropGroup)

def ssx2_world_patches_unregister():

	del bpy.types.Object.ssx2_PatchProps

	for c in classes:
		unregister_class(c)