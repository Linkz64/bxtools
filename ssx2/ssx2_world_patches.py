import bpy, bmesh
from bpy.utils import register_class, unregister_class
from mathutils import Vector, Matrix

from ..external.ex_utils import prop_split
from ..general.blender_get_data import get_uvs
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
	patch_tex_maps,
	patch_uv_equiv_tex_maps,
	patch_tex_map_equiv_uvs,
	indices_for_control_grid,
)

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

				set_patch_control_grid(mesh, patch_points, pch_data[1])

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

		scale = (100 / bpy.context.scene.bx_WorldScale) + 14

		bpy.ops.mesh.primitive_grid_add(enter_editmode=False, align='CURSOR',
			x_subdivisions=3,
			y_subdivisions=3)

		grid = bpy.context.active_object
		collection_it_was_added_to = grid.users_collection[0]
		grid.scale = (scale, scale, 0)
		bpy.ops.object.transform_apply(scale=True)
		grid_data = grid.data

		props = grid.ssx2_PatchProps

		props.type = bpy.context.scene.ssx2_WorldUIProps.patchTypeChoice #'1'
		props.isControlGrid = True
		props.useManualUV = True
		props.manualUV0 = (0.0, 0.0)
		props.manualUV1 = (0.0, 0.0)
		props.manualUV2 = (0.0, 0.0)
		props.manualUV3 = (0.0, 0.0)

		mat = bpy.context.scene.ssx2_WorldUIProps.patchMaterialChoice
		if mat is not None:
			#mat_name = mat.name
			pass
		else:
			mat = set_patch_material(f"pch")
			bpy.context.scene.ssx2_WorldUIProps.patchMaterialChoice = mat

		grid.data.materials.append(mat)

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
		patch.ssx2_PatchProps.texMapPreset = '2'
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
		return active_object is not None and \
		(active_object.type == 'SURFACE' or active_object.ssx2_PatchProps.isControlGrid)

	def toggle_to_control_grid(self, context, objects_to_convert):
		# to_reselect = []
		for obj in objects_to_convert:
			if obj.type != 'SURFACE':
				print("NOT SURFACE", obj.name)
				#obj.select_set(True)
				continue # skip

			# print(obj.name)

			collection = obj.users_collection[0]

			patch_name = obj.name
			patch_matrix = Matrix(obj.matrix_world) # should work
			patch_points = []
			patch_uvs = []
			patch_material = obj.data.materials[0]
			props = obj.ssx2_PatchProps
			patch_type = props.type
			patch_showoff_only = props.showoffOnly

			for spline in obj.data.splines:
				for p in spline.points:
					x, y, z, w = p.co# * context.scene.bx_WorldScale
					patch_points.append((x, y, z))

			if not props.useManualUV:
				patch_uvs = patch_known_uvs[patch_tex_map_equiv_uvs[int(props.texMapPreset)]]
			else:
				patch_uvs = [
					props.manualUV0.to_tuple(),
					props.manualUV1.to_tuple(),
					props.manualUV2.to_tuple(),
					props.manualUV3.to_tuple(),
				]

			# delete method
			bpy.data.objects.remove(obj, do_unlink=True) # delete object

			new_grid = bpy.data.objects.get(patch_name)
			if new_grid is None or new_grid.type != 'MESH':
				mesh = bpy.data.meshes.new(patch_name)
				new_grid = bpy.data.objects.new(patch_name, mesh)

			new_grid.data = set_patch_control_grid(mesh, patch_points, patch_uvs)
			new_grid.data.materials.append(patch_material)
			new_grid.ssx2_PatchProps.type = patch_type
			new_grid.ssx2_PatchProps.showoffOnly = patch_showoff_only
			new_grid.ssx2_PatchProps.isControlGrid = True

			collection.objects.link(new_grid)

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

			new_grid.select_set(True)
		# 	to_reselect.append(new_grid)
		# for obj in to_reselect:
		# 	obj.select_set(True)

	def toggle_to_patch(self, context, objects_to_convert):
		to_reselect = []
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
			grid_uvs = [(uv[0], -uv[1]) for uv in get_uvs(obj)]
			if len(obj.data.materials) > 0:
				grid_material = obj.data.materials[0]
			else:
				grid_material = None
			grid_type = props.type
			grid_showoff_only = props.showoffOnly

			grid_uv_square = [grid_uvs[12], grid_uvs[0], grid_uvs[15], grid_uvs[3]]
			print(grid_uv_square)

			for vtx in obj.data.vertices:
				grid_points.append((vtx.co.x, vtx.co.y, vtx.co.z, 1.0))

			bpy.data.objects.remove(obj, do_unlink=True) # delete object


			print(collection.name)
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
			new_patch.ssx2_PatchProps.manualUV1 = grid_uvs[1]
			new_patch.ssx2_PatchProps.manualUV2 = grid_uvs[2]
			new_patch.ssx2_PatchProps.manualUV3 = grid_uvs[3]

			# new_patch.select_set(True)
			to_reselect.append(new_patch)
		for obj in to_reselect:
			obj.select_set(True)

	def execute(self, context):
		selected_objects = context.selected_objects
		active_object = context.active_object
		active_object_name = active_object.name
		objects_to_convert = []

		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

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

	SSX2_PatchPanel,
	SSX2_PatchPropGroup,

	SSX2_OP_ToggleControlGrid,
)

def ssx2_world_patches_register():
	for c in classes:
		register_class(c)
	
	bpy.types.Object.ssx2_PatchProps = bpy.props.PointerProperty(type=SSX2_PatchPropGroup)

def ssx2_world_patches_unregister():

	del bpy.types.Object.ssx2_PatchProps

	for c in classes:
		unregister_class(c)