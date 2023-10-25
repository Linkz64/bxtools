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

			print(num_u, num_u % 4)
			if num_points < 16:
				self.report({'WARNING'}, "INVALID 1")
				return {'CANCELLED'}
			elif num_points == 16:
				segment_points = [sp.co for sp in s.points[0:16]]
				all_spline_segs.append([segment_points])

			#return {'CANCELLED'}
			
			print("points u/v",num_u, num_v)

			# Split into segments of 16 points

			segment_count = (num_u - 1) // 3
			segments = [[] for i in range(segment_count)]
			print(f"\nsegments: {segment_count}\n")
			
			for v in range(4):#num_v):             # e.g 4v's each with 7u's
				print("\nv:", v, v * num_u)

				v_start = v * num_u
				v_end = v_start + num_u

				this_spline = []
				for u in range(v_start, v_end, 3):
					segment_points = s.points[u:u + 4]
					segment_points = [sp.co for sp in segment_points]
					print("u:", u, v_end-1, u + 4)
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
			m = obj.matrix_world
			matrices = []
			all_splines = []

			if num_splines == 2:
				print("2 splines")

				row1_points = [] # final row 1
				row4_points = [] # final row 4
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
							row1_points += current_points
						else:
							row4_points += current_points

				row1_length = len(row1_points)#(len(obj.data.splines[0].bezier_points) * 2) + 3 # * 3 - 2
				
				if row1_length != len(row4_points):
					self.report({'ERROR'}, f"Number of points must match on both splines")
					return {'CANCELLED'}

				row2 = []
				row3 = []
				for i in range(len(row1_points)):
					c1p = row1_points[i]
					c2p = row4_points[i]
					row2.append(c1p + ((c2p - c1p) / 3))
					row3.append(c2p - ((c2p - c1p) / 3))

				all_splines.append(row1_points)
				all_splines.append(row2)
				all_splines.append(row3)
				all_splines.append(row4_points)

			elif num_splines > 3: # == 4
				print("4 splines")

				for i in range(4):
					s = obj.data.splines[i]
					current_spline = []

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

						current_spline += current_points

					all_splines.append(current_spline)

				row1_length = len(current_spline)

				if row1_length * 4 != sum([len(i) for i in all_splines]):
					self.report({'ERROR'}, f"Number of points must match on all splines")
					return {'CANCELLED'}
			else:
				self.report({'ERROR'}, "Active object must have 2 or 4 splines.")
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

			for j, p in enumerate(splines[0].points): # points of surface 0
				nx, ny, nz = all_points_combined[j]
				p.co = nx, ny, nz, 1.0

			bpy.ops.object.mode_set(mode = 'OBJECT')
			bpy.context.active_object.select_set(False)

		self.report({'INFO'}, "Finished")
		return {'FINISHED'}

class SSX2_OP_AddSplineCage(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_spline_cage'
	bl_label = "Spline Cage"
	bl_description = 'Generate a spline cage'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}
	
	def execute(self, context):
		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		collection = bpy.context.collection

		append_path = templates_append_path
		curve_data_name = "SplineCageAppend231022"
		nodes_tree_name = "CageLoftAppend231022"
		curve_data = bpy.data.curves.get(curve_data_name)
		node_tree = bpy.data.node_groups.get(nodes_tree_name)

		print("Append Spline Cage:", curve_data is None)
		print("Append Node Tree:", node_tree is None)

		if not os.path.isfile(append_path):
			self.report({'ERROR'}, f"Failed to append {append_path}")
			return {'CANCELLED'}

		with bpy.data.libraries.load(append_path, link=False) as (data_from, data_to):
			if node_tree is None:
				if nodes_tree_name in data_from.node_groups:
					data_to.node_groups = [nodes_tree_name]
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
		if curve_data.users == 0:
			curve_data.use_fake_user = True
		curve_data = curve_data.copy()
		curve_obj = bpy.data.objects.new("SplineCage", curve_data)
		curve_data.name = curve_obj.name
		curve_obj.location = bpy.context.scene.cursor.location

		node_tree = bpy.data.node_groups.get(nodes_tree_name)
		if node_tree.users == 0:
			node_tree.use_fake_user = True
		node_modifier = curve_obj.modifiers.new(name="GeoNodes", type='NODES')
		node_modifier.node_group = node_tree
		#node_tree.use_fake_user = True # keeps it from being deleted on .blend reopen

		collection.objects.link(curve_obj)

		return {'FINISHED'}

class SSX2_OP_AddPatchMaterial(bpy.types.Operator):
	bl_idname = 'material.ssx2_add_patch_material'
	bl_label = "Patch Material"
	bl_description = 'Create a Patch Material'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}
	
	def execute(self, context):

		obj = bpy.context.active_object

		append_path = templates_append_path
		material_name = "PatchMaterialAppend231022"
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

		print(material.name)
		obj.data.materials.append(material)

		return {'FINISHED'}

class SSX2_OP_AddControlGrid(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_control_grid'
	bl_label = "Control Grid"
	bl_description = 'Generate a control grid patch'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}
	
	def execute(self, context):
		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		collection = bpy.data.collections.get("Patches")

		if collection is None:
			self.report({'WARNING'}, "'Patches' Collection not found!")
			collection = bpy.context.collection

		append_path = templates_append_path
		material_name = "PatchMaterialAppend231022"
		node_tree_name = "GridTesselateAppend231022"
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
		grid_data = grid.data

		props = grid.ssx2_PatchProps

		props.type = bpy.context.scene.ssx2_WorldUIProps.patchTypeChoice #'1'
		props.isControlGrid = True
		props.useManualUV = True
		# props.manualUV0 = (0.0, 0.0) # doesn't need to be set. update when toggling
		# props.manualUV1 = (0.0, 0.0)
		# props.manualUV2 = (0.0, 0.0)
		# props.manualUV3 = (0.0, 0.0)

		# mat = bpy.context.scene.ssx2_WorldUIProps.patchMaterialChoice
		# if mat is not None:
		# 	#mat_name = mat.name
		# 	pass
		# else:
		# 	mat = set_patch_material(f"pch")
		# 	bpy.context.scene.ssx2_WorldUIProps.patchMaterialChoice = mat

		material = bpy.data.materials.get("pch")
		if material is None:
			material = bpy.data.materials.get(material_name)
			if material.users == 0:
				material.use_fake_user = True
			material = material.copy()
			material.name = "pch"
		grid.data.materials.append(material)

		node_tree = bpy.data.node_groups.get(node_tree_name)
		if node_tree.users == 0:
			node_tree.use_fake_user = True
		node_modifier = grid.modifiers.new(name="GeoNodes", type='NODES')
		node_modifier.node_group = node_tree
		node_modifier["Input_3"] = 1

		if collection_it_was_added_to.name != collection.name:
			collection_it_was_added_to.objects.unlink(grid)
			collection.objects.link(grid)

		return {'FINISHED'}

class SSX2_OP_AddPatch(bpy.types.Operator):
	bl_idname = 'object.ssx2_add_patch'
	bl_label = "Surface Patch"
	bl_description = 'Generate a surface patch'
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}
	
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
		material_name = "PatchMaterialAppend231022"
		surface_name = "SurfPatchAppend231022"
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
					self.report({'ERROR'}, f"Failed to append geonodes from {append_path}")
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
		if surface.users == 0:
			surface.use_fake_user = True
		surface = surface.copy()
		patch = bpy.data.objects.new("SurfPatch", surface)
		surface.name = patch.name#"SurfPatch"

		patch.location = bpy.context.scene.cursor.location
		patch.ssx2_PatchProps.type = '1'
		patch.ssx2_PatchProps.texMapPreset = '3'

		material = bpy.data.materials.get("pch")
		if material is None:
			material = bpy.data.materials.get(material_name)
			if material.users == 0:
				material.use_fake_user = True
			material = material.copy()
			material.name = "pch"
		patch.data.materials.append(material)
		collection.objects.link(patch)

		"""
		bpy.ops.surface.primitive_nurbs_surface_surface_add(enter_editmode=False, align='CURSOR', rotation=(0.0, 0.0, 0.0))
		patch = bpy.context.active_object
		collection_it_was_added_to = patch.users_collection[0]
		surface_data = patch.data

		spline = surface_data.splines[0]
		spline.use_endpoint_u = True
		spline.use_endpoint_v = True
		spline.resolution_u = 2
		spline.resolution_v = 2

		scale = (100 / bpy.context.scene.bx_WorldScale) + 9
		align_to_grid = 0.0#scale*1.5

		for i, p in enumerate(spline.points):
			p.co = (p.co.x*scale+align_to_grid, p.co.y*scale+align_to_grid, 0.0, p.co.w)

		patch.ssx2_PatchProps.type = '1'
		patch.ssx2_PatchProps.texMapPreset = '3'#'2'
		#patch.ssx2_PatchProps.texMap = (0.0, 0.0, 0.0)
		# patch.ssx2_PatchProps.useManualUV = False
		# patch.ssx2_PatchProps.manualUV0 = (0.0, 0.0, ) # needs to be like this
		# patch.ssx2_PatchProps.manualUV1 = (0.0, 0.0, )
		# patch.ssx2_PatchProps.manualUV2 = (0.0, 0.0, )
		# patch.ssx2_PatchProps.manualUV3 = (0.0, 0.0, )
		#patch.color = (0.0, 0.0, 0.0, 1.0)

		mat = bpy.context.scene.ssx2_WorldUIProps.patchMaterialChoice
		if mat is not None:
			#mat_name = mat.name
			pass
		else:
			mat = set_patch_material(f"pch")
			bpy.context.scene.ssx2_WorldUIProps.patchMaterialChoice = mat
			#mat.blend_method = 'BLEND' # 'HASHED' 'OPAQUE'

		patch.data.materials.append(mat)

		if collection_it_was_added_to.name != collection.name:
			collection_it_was_added_to.objects.unlink(patch)
			collection.objects.link(patch)
		"""

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
		node_tree_name = "GridTesselateAppend231022"
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

		def temp_function():
			for obj in objects_to_convert:
				if obj.type != 'SURFACE':
					print("NOT SURFACE", obj.name)#obj.select_set(False)
					continue

				# print(obj.name)
				collection = obj.users_collection[0]
				patch_name = obj.name
				patch_matrix = Matrix(obj.matrix_world) # should work
				patch_points = []
				patch_uvs = []
				if len(obj.data.materials) > 0:
					patch_material = obj.data.materials[0]
				else:
					patch_material = None
				props = obj.ssx2_PatchProps
				patch_type = props.type
				patch_showoff_only = props.showoffOnly

				for spline in obj.data.splines:
					for p in spline.points:
						x, y, z, w = p.co# * context.scene.bx_WorldScale
						patch_points.append((x, y, z))

				if not props.useManualUV:
					patch_uvs = patch_known_uvs_blender[patch_tex_map_equiv_uvs[int(props.texMapPreset)]]
				else:
					patch_uvs = [
						props.manualUV0.to_tuple(),
						props.manualUV1.to_tuple(),
						props.manualUV2.to_tuple(),
						props.manualUV3.to_tuple(),
					]
					patch_uvs = [(uv[0], -uv[1]) for uv in patch_uvs]

				# delete method
				bpy.data.objects.remove(obj, do_unlink=True) # delete object

				new_grid = bpy.data.objects.get(patch_name)
				if new_grid is None or new_grid.type != 'MESH':
					mesh = bpy.data.meshes.new(patch_name)
					new_grid = bpy.data.objects.new(patch_name, mesh)

				new_grid.data = set_patch_control_grid(mesh, patch_points, patch_uvs)
				if patch_material is not None:
					new_grid.data.materials.append(patch_material)
				new_grid.ssx2_PatchProps.type = patch_type
				new_grid.ssx2_PatchProps.showoffOnly = patch_showoff_only
				new_grid.ssx2_PatchProps.isControlGrid = True

				collection.objects.link(new_grid)

				node_modifier = new_grid.modifiers.new(name="GeoNodes", type='NODES')
				node_modifier.node_group = node_tree
				node_modifier["Input_3"] = 1


				new_grid.matrix_world = patch_matrix

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

				self.number_of_objects_toggled += 1
				new_grid.select_set(True)
			# 	to_reselect.append(new_grid)
			# for obj in to_reselect:
			# 	obj.select_set(True)
		
		run_without_update(temp_function)

	def toggle_to_patch(self, context, objects_to_convert):
		to_reselect = []

		def temp_function():
			for obj in objects_to_convert:
				if len(obj.data.vertices) != 16:
					print(obj.name, "does not have 16 vertices.")
					continue

				#print(obj.name)

				collection = obj.users_collection[0]
				props = obj.ssx2_PatchProps

				grid_name = obj.name
				grid_matrix = Matrix(obj.matrix_world)
				grid_points = []
				grid_uvs = [(uv[0], -uv[1] ) for uv in get_uvs_per_verts(obj)]

				if len(obj.data.materials) > 0:
					grid_material = obj.data.materials[0]
				else:
					grid_material = None
				grid_type = props.type
				grid_showoff_only = props.showoffOnly
				
				grid_uv_square = [grid_uvs[0], grid_uvs[12], grid_uvs[3], grid_uvs[15]] # 0 12 3 15

				for vtx in obj.data.vertices:
					grid_points.append((vtx.co.x, vtx.co.y, vtx.co.z, 1.0))

				bpy.data.objects.remove(obj, do_unlink=True) # delete object

				new_patch = set_patch_object(grid_points, grid_name, collection=collection.name)
				new_patch.matrix_world = grid_matrix
				if grid_material is not None:
					new_patch.data.materials.append(grid_material)

				existing_patch_uv_idx = existing_patch_uvs(grid_uv_square) # problem causer 1

				if existing_patch_uv_idx is None: # problem causer 2
					new_patch.ssx2_PatchProps.useManualUV = True
					new_patch.color = (0.76, 0.258, 0.96, 1.0) # light purple
				else:
					new_patch.ssx2_PatchProps.useManualUV = False
					new_patch.ssx2_PatchProps.texMapPreset = str(existing_patch_uv_idx)

				new_patch.ssx2_PatchProps.type = grid_type
				new_patch.ssx2_PatchProps.showoffOnly = grid_showoff_only
				new_patch.ssx2_PatchProps.manualUV0 = grid_uvs[0]
				new_patch.ssx2_PatchProps.manualUV1 = grid_uvs[12]
				new_patch.ssx2_PatchProps.manualUV2 = grid_uvs[3]
				new_patch.ssx2_PatchProps.manualUV3 = grid_uvs[15]

				self.number_of_objects_toggled += 1
				to_reselect.append(new_patch)

			for obj in to_reselect:
				obj.select_set(True)
		run_without_update(temp_function)

	def execute(self, context):
		selected_objects = context.selected_objects
		active_object = context.active_object
		active_object_name = active_object.name
		objects_to_convert = []

		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		self.number_of_objects_toggled = 0

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
		self.report({'INFO'}, f"Toggled {self.number_of_objects_toggled} objects")
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
		
		if context.object.type == 'SURFACE' or context.object.ssx2_PatchProps.isControlGrid:
			prop_split(col, obj.ssx2_PatchProps, 'type', "Patch Type")
			#prop_split(col, obj.ssx2_PatchProps, 'useManualUV', "Manual Mapping")
			col.prop(obj.ssx2_PatchProps, 'showoffOnly', text="Showoff Only")
		if context.object.type == 'SURFACE':
			col.prop(obj.ssx2_PatchProps, 'useManualUV', text="Manual Mapping")
			if not obj.ssx2_PatchProps.useManualUV:
				prop_split(col, obj.ssx2_PatchProps, 'texMapPreset', "Mapping Preset")
				#col.prop(obj.ssx2_PatchProps, 'patchFixUVRepeat', text="Fix UV Repeat")
				#prop_split(col, obj.ssx2_PatchProps, "texMap", "Texture Mapping")
			col_split = col.split(factor=0.5)
			row = col.row()
			row_split = row.split(factor=0.5)
			if obj.ssx2_PatchProps.useManualUV:
				col_split.prop(obj.ssx2_PatchProps, "manualUV0", text="")
				col_split.prop(obj.ssx2_PatchProps, "manualUV1", text="")
				row_split.prop(obj.ssx2_PatchProps, "manualUV2", text="")
				row_split.prop(obj.ssx2_PatchProps, "manualUV3", text="")



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
	texMap: bpy.props.FloatVectorProperty(name="Test",
		description="Testing",
		default=(0.0, 0.0, 0.0),
		min=-3.14159265359,
		max=3.14159265359,
		subtype='EULER')
	texMapPreset: bpy.props.EnumProperty(name='Mapping Preset', items=enum_ssx2_patch_uv_preset, 
		update=update_patch_uv_preset,
		default='0')
	# patchFixUVRepeat: bpy.props.BoolProperty(name="Fix UV Repeat", default=False,
	# 	description="Scales up the UVs on export in order to remove the visible outline")
	useManualUV: bpy.props.BoolProperty(name="Manual UVs", default=False,
		description="Manually enter UV values. Cannot be previewed!")
	manualUV0: bpy.props.FloatVectorProperty(default=(0.0, 0.0),size=2,subtype='XYZ')
	manualUV1: bpy.props.FloatVectorProperty(default=(0.0, 0.0),size=2,subtype='XYZ')
	manualUV2: bpy.props.FloatVectorProperty(default=(0.0, 0.0),size=2,subtype='XYZ')
	manualUV3: bpy.props.FloatVectorProperty(default=(0.0, 0.0),size=2,subtype='XYZ')

	isControlGrid: bpy.props.BoolProperty(name="Is Control Grid", default=False)

classes = (
	SSX2_OP_AddPatch,
	SSX2_OP_AddControlGrid,
	SSX2_OP_AddSplineCage,
	SSX2_OP_AddPatchMaterial,

	SSX2_PatchPanel,
	SSX2_PatchPropGroup,

	SSX2_OP_ToggleControlGrid,
	SSX2_OP_CageToPatch,
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