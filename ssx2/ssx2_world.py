import bpy
from bpy.utils import register_class, unregister_class
from mathutils import Vector
import json
import time
import os
import json

from ..panels import SSX2_Panel
from ..external.ex_utils import prop_split
#from ..general.bx_utils import getset_instance_collection, run_without_update
from ..general.blender_set_data import *
from ..general.blender_get_data import get_images_from_folder, get_uvs
from ..general.bx_utils import *

from .ssx2_world_io_in import get_patches_json#*
from .ssx2_world_patches import (
	ssx2_world_patches_register, 
	ssx2_world_patches_unregister,
	create_imported_patches,
	SSX2_OP_AddPatch,
	SSX2_OP_AddControlGrid,
	SSX2_OP_ToggleControlGrid,
	patch_tex_map_equiv_uvs,
	patch_known_uvs,
	existing_patch_uvs, # function
)
from .ssx2_constants import (
	enum_ssx2_world_project_mode,
	enum_ssx2_world,
	enum_ssx2_patch_group,
	enum_ssx2_surface_type,
	enum_ssx2_surface_type_spline,
	enum_ssx2_surface_type_extended
)
from .ssx2_world_lightmaps import SSX2_OP_BakeTest




## Operators

class SSX2_OP_AddInstance(bpy.types.Operator): # recreate this but use collection instead of model object
	bl_idname = 'object.ssx2_add_instance'
	bl_label = "Model Instance"
	bl_description = 'Generate an instance'
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
	importPath: bpy.props.StringProperty(name="", maxlen=1024, subtype='DIR_PATH', 
		default="",
		description="Folder that contains the world files")
	worldChoice: bpy.props.EnumProperty(name='World Choice', items=enum_ssx2_world, default='gari')
	worldChoiceCustom: bpy.props.StringProperty(name="", default="gari", maxlen=8, subtype='NONE',
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

	exportPath: bpy.props.StringProperty(name="", maxlen=1024, subtype='DIR_PATH', default="",
		description="Export folder path")
	exportPatches: bpy.props.BoolProperty(name="Export Patches", default=True)
	exportPatchesOverride: bpy.props.BoolProperty(name="Override", default=True)

	exportSplines: bpy.props.BoolProperty(name="Export Splines", default=True)
	exportSplinesOverride: bpy.props.BoolProperty(name="Override", default=True)

class SSX2_WorldSplinePropGroup(bpy.types.PropertyGroup): # ssx2_SplineProps
	type: bpy.props.EnumProperty(name='Spline Type', items=enum_ssx2_surface_type_spline)

	# change these to enum? spline_hide_mode = (NONE, SHOWOFF, RACE)
	#	assuming showoff and race set to True hides it in every mode
	#
	# hideShowoff: bpy.props.BoolProperty(name="Hide Showoff", default=False,
	# 	description="Hide in showoff modes.")
	# hideRace: bpy.props.BoolProperty(name="Hide Race", default=False,
	# 	description="Hide in race modes.")

class SSX2_SplinePanel(SSX2_Panel):
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
		col = self.layout.column()
		obj = context.object
		if context.object.type == 'CURVE':
			prop_split(col, obj.ssx2_SplineProps, 'type', "Spline Type")

def update_select_by_surface_type(self, context):
	# select surface patches by surface type
	# note context only works on `set=`
	if bpy.context.mode != "OBJECT":
		bpy.ops.object.mode_set(mode="OBJECT")
	
	#selected_type = enum_ssx2_surface_type[context] # check enum_ssx2_surface_type
	selected_type = self.patchSelectByType # string
	found = False
	if selected_type not in ('50', '51'):
		for obj in bpy.data.objects:
			if obj.type == 'SURFACE' or obj.ssx2_PatchProps.isControlGrid:
				#if 'ssx2_PatchType' in dir(obj):if obj.ssx2_PatchType == selected_type:
				if obj.ssx2_PatchProps.type == selected_type:#selected_type[0]:
					obj.select_set(True)
					found = True
	elif selected_type == '50':
		for obj in bpy.data.objects:
			if obj.type == 'SURFACE':
				obj.select_set(True)
				found = True
	elif selected_type == '51':
		for obj in bpy.data.objects:
			if obj.ssx2_PatchProps.isControlGrid:
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
		description="Test") # this is temporary, use Menu class or an enum prop menu ui instead:
	patchMaterialChoice: bpy.props.PointerProperty(type=bpy.types.Material, poll=poll_mat_for_add_patch)
	patchTypeChoice: bpy.props.EnumProperty(name='Select by Surface Type', items=enum_ssx2_surface_type, default='1')

class SSX2_OP_WorldInitiateProject(bpy.types.Operator):
	bl_idname = "scene.ssx2_world_initiate_project"
	bl_label = "Initiate Project"
	bl_description = "Create necessary collections"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):

		scene_collection = bpy.context.scene.collection

		def get_set_collection_to_target(name, target_collection):
			"""Gets or Creats collection and parents it to target collection"""
			col = bpy.data.collections.get(name) # this gets World.001 too, therefore name needs checking
			if col is None:
				col = bpy.data.collections.new(name)
			elif col.name != name:
				col = bpy.data.collections.new(name)
			if target_collection.children.get(name) is None:
				target_collection.children.link(col)
			return col

		#world = get_set_collection_to_target("World", scene_collection)
		patches = get_set_collection_to_target("Patches", scene_collection)
		splines = get_set_collection_to_target("Splines", scene_collection)

		return {'FINISHED'}

class SSX2_OP_WorldExpandUIBoxes(bpy.types.Operator): # turn this into a general thing not just world
	bl_idname = "object.ssx2_expand_ui_boxes"
	bl_label = ""
	bl_description = "Expand box"

	prop: bpy.props.StringProperty()

	def execute(self, context):
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
		return io.exportPatches or io.exportSplines

	def execute(self, context):

		io_props = bpy.context.scene.ssx2_WorldImportExportProps # REMOVE THIS
		io = bpy.context.scene.ssx2_WorldImportExportProps
		scale = bpy.context.scene.bx_WorldScale

		if context.mode != "OBJECT":
			bpy.ops.object.mode_set(mode = "OBJECT")
		bpy.ops.object.select_all(action = "DESELECT")

		if io.exportSplines:

			spline_collection = bpy.data.collections.get("Splines")
			if spline_collection is None:
				self.report({'ERROR'}, "'Splines' collection not found")#spline_collection = bpy.context.collection
				return {'CANCELLED'}

			spline_objects = spline_collection.all_objects

			if len(spline_objects) == 0:
				self.report({'ERROR'}, "No splines found in 'Splines' collection")
				return {'CANCELLED'}

			json_export_path = os.path.abspath(bpy.path.abspath(io_props.exportPath))+'/Splines.json'

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
				segments_unknowns = []

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

					spline_segments_json_obj = {
						"Point1": segment_points[0].to_tuple(),
						"Point2": segment_points[1].to_tuple(),
						"Point3": segment_points[2].to_tuple(),
						"Point4": segment_points[3].to_tuple(),
						"U0": 0.0,
						"U1": 0.0,
						"U2": 0.0,
						"U3": 0.0,
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
							spline['Segments'] = final_splines[index]['Segments']
							overriden_indices.append(index)
						except:
							print(f"{spline['SplineName']} is missing in Blender. Skipping.")

					for i, spline in enumerate(final_splines):

						if i not in overriden_indices:
							print(i, final_splines[i]['SplineName'])
							new_json['Splines'].append(final_splines[i])


				with open(json_export_path, 'w') as f:
					json.dump(new_json, f, indent=2)

			else:
				with open(json_export_path, 'w') as f:
					new_json = {}
					new_json['Splines'] = []

					for spline in final_splines:
						new_json['Splines'].append(spline)

					json.dump(new_json, f, indent=2)


		if io_props.exportPatches: # PATCHES
			patch_collection = bpy.data.collections.get("Patches")

			if patch_collection is None:
				self.report({'ERROR'}, "'Patches' collection not found")#patch_collection = bpy.context.collection
				return {'CANCELLED'}

			patch_objects = patch_collection.all_objects

			if len(patch_objects) == 0:
				self.report({'ERROR'}, "No patches found in 'Patches' collection")
				return {'CANCELLED'}

			json_export_path = os.path.abspath(bpy.path.abspath(io_props.exportPath))+'/Patches.json'

			print(json_export_path)

			if not os.path.isfile(json_export_path):
				self.report({'ERROR'}, f"'Patches.json' not found.\n{json_export_path}")
				return {'CANCELLED'}

			with open(json_export_path, 'w') as f:
				testing = {}
				testing['Patches'] = []

				for obj in patch_objects:
					props = obj.ssx2_PatchProps

					if obj.ssx2_PatchProps.isControlGrid: # EXPORT CONTROL GRID
						grid_points = []

						for vtx in obj.data.vertices:
							x, y, z = vtx.co * scale
							grid_points.append((x, y, z, 1.0))

						grid_uvs = [(uv[0], -uv[1]) for uv in get_uvs_per_verts(obj)]
						grid_uv_square = [grid_uvs[12], grid_uvs[0], grid_uvs[15], grid_uvs[3]]

						if len(obj.material_slots) != 0:
							mat = bpy.data.materials.get(obj.material_slots[0].name)
							tex = mat.node_tree.nodes["Image Texture"].image.name
						else:
							tex = "0000.png"

						if 'lightmap_uvs' in obj.keys(): # and ('lightmap_id' in obj.keys())
							lightmap_uvs = get_custom_prop_vec4(obj, 'lightmap_uvs')
							lightmap_id = obj['lightmap_id']
						else:
							lightmap_uvs = [0.0, 0.0, 0.0625, 0.0625]
							lightmap_id = 0

						patch_json_obj = {
							"PatchName": obj.name,
							"LightMapPoint": lightmap_uvs,
							"UVPoints": grid_uv_square,
							"Points": grid_points,
							"PatchStyle": int(props.type),
							"TrickOnlyPatch": props.showoffOnly,
							"TexturePath": tex,
							"LightmapID": lightmap_id
						}

						print(patch_json_obj)

						testing['Patches'].append(patch_json_obj)

					if obj.type == 'SURFACE': # EXPORT PATCH
						
						patch_points = []
						for spline in obj.data.splines:
							for p in spline.points:
								x, y, z, w = p.co * scale
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

						if len(obj.material_slots) != 0:
							mat = bpy.data.materials.get(obj.material_slots[0].name)
							tex = mat.node_tree.nodes["Image Texture"].image.name
						else:
							tex = "0053.png"

						if 'lightmap_uv' in obj.keys():
							lightmap_uvs = get_custom_prop_vec4(obj, 'lightmap_uvs')
							lightmap_id = obj['lightmap_id']
						else: # scaling down to 0.0 doesn't work
							lightmap_uvs = [0.0, 0.0, 0.0625, 0.0625] #[0.0, 0.6, 0.0625, 0.0625] #
							lightmap_id = 0

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
						testing['Patches'].append(patch_json_obj)

				json.dump(testing, f)#, indent=2)

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
		return (io.importPatches or io.importSplines) and \
			(s.bx_PlatformChoice == 'XBX' or s.bx_PlatformChoice == 'NGC' or\
			s.bx_PlatformChoice == 'PS2' or s.bx_PlatformChoice == 'ICE')

	def __init__(self, json_patches=[]):
		self.json_patches = json_patches
		self.images = []

	def create_patches_json(self):
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
					pch_mat = set_patch_material(pch_mat_name)

				pch_mat.node_tree.nodes["Image Texture"].image = bpy.data.images.get(json_patch.texture_path)
				patch.data.materials.append(pch_mat)

				patch.ssx2_PatchProps.type = str(json_patch.type)
				patch.ssx2_PatchProps.showoffOnly = json_patch.showoff_only
				patch.ssx2_PatchProps.isControlGrid = True
				patch['index'] = i
				patch["offset"] = int(i * 720 + 160)
				patch['lightmap_uvs'] = json_patch.lightmap_uvs
				patch['lightmap_id']  = json_patch.lightmap_id

				patches_collection.objects.link(patch)

				if patch_grouping != 'NONE':
					to_group.append(patch)
		else:
			for i, json_patch in enumerate(self.json_patches): # IMPORT PATCH
				
				patch = bpy.data.objects.get(json_patch.name)
				if patch is None or patch.type != 'SURFACE':
					patch = set_patch_object(json_patch.points, json_patch.name)

				existing_patch_uv_idx = existing_patch_uvs(json_patch.uvs)

				# adjust_scale = False
				# if existing_patch_uv_idx is None:
				# 	existing_patch_uv_idx = existing_patch_uvs(round_uvs_for_check(pch_data[1]))
				# 	if existing_patch_uv_idx is not None:
				# 		adjust_scale = True

				if existing_patch_uv_idx is None:
					patch.ssx2_PatchProps.useManualUV = True
					patch.color = (0.76, 0.258, 0.96, 1.0) # to see which ones are manual
				else:
					patch.ssx2_PatchProps.useManualUV = False
					patch.ssx2_PatchProps.texMapPreset = str(existing_patch_uv_idx)
					# patch.ssx2_PatchProps.texMap = patch_tex_maps[existing_patch_uv_idx] # already set by preset

				short_texture_name = os.path.splitext(os.path.basename(json_patch.texture_path))[0] # no path no ext

				pch_mat_name = f"pch.{short_texture_name}"
				pch_mat = bpy.data.materials.get(pch_mat_name)
				if pch_mat is None:
					pch_mat = set_patch_material(pch_mat_name)

				pch_mat.node_tree.nodes["Image Texture"].image = bpy.data.images.get(json_patch.texture_path)
				patch.data.materials.append(pch_mat)

				patch.ssx2_PatchProps.type = str(json_patch.type)
				patch.ssx2_PatchProps.showoffOnly = json_patch.showoff_only
				patch.ssx2_PatchProps.manualUV0 = (json_patch.uvs[0][0], json_patch.uvs[0][1])
				patch.ssx2_PatchProps.manualUV1 = (json_patch.uvs[1][0], json_patch.uvs[1][1])
				patch.ssx2_PatchProps.manualUV2 = (json_patch.uvs[2][0], json_patch.uvs[2][1])
				patch.ssx2_PatchProps.manualUV3 = (json_patch.uvs[3][0], json_patch.uvs[3][1])
				patch['index'] = i
				patch["offset"] = int(i * 720 + 160)
				patch['lightmap_uvs'] = json_patch.lightmap_uvs
				patch['lightmap_id']  = json_patch.lightmap_id

				if patch_grouping != 'NONE':
					to_group.append(patch)


		if patch_grouping == 'BATCH':
			layer_collection = bpy.context.view_layer.layer_collection
			if patch_grouping == "BATCH":
				group_size = 700 # make it a scene prop?
				for i, patch in enumerate(to_group):
					new_col = collection_grouping(f"Patch_Group", patches_collection, group_size, i)
					new_col.objects.link(patch)
					patches_collection.objects.unlink(patch)

			for collection in patches_collection.children:
				layer_col = get_layer_collection(layer_collection, collection.name)
				layer_col.exclude = True
		if patch_grouping == 'TYPE':
			pass
			
	def import_icesaw(self):
		sc = bpy.context.scene
		scene_collection = sc.collection

		io = sc.ssx2_WorldImportExportProps
		#io.importNames
		#io.importTextures
		#io.patchImportGrouping

		folder_path = sc.ssx2_WorldImportExportProps.importPath
		if not os.path.exists(folder_path): #.isdir
			self.report({'ERROR'}, f"Import Path does not exist")
			return {'CANCELLED'}

		if io.importPatches: # PATCHES
			print("Importing Patches")

			if bpy.data.collections.get('Patches') is None:
				scene_collection.children.link(bpy.data.collections.new('Patches'))

			self.json_patches = get_patches_json(folder_path+'/Patches.json')
			self.images = get_images_from_folder(folder_path+'/Textures/')

			run_without_update(self.create_patches_json)


		if io.importSplines: # SPLINES
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
				self.report({'ERROR'}, f"File 'Splines.json' does not exist in 'Import Path'")
				return {'CANCELLED'}

			json_point_order = (1, 2, 3, 4) #(4, 3, 2, 1)
			with open(file_path, 'r') as f:
				data = json.load(f)

				for i, json_spline in enumerate(data["Splines"]):

					print("\nSpline", i)
					print(json_spline["SplineName"])
					
					merged_points = []
					for j, segment in enumerate(json_spline["Segments"]):

						points = []

						for k in json_point_order:

							if k == 1 and j > 0:
								continue

							x,y,z = segment[f"Point{k}"]
							if io.splineImportAsNURBS:
								merged_points.append((x/100, y/100, z/100, 1.0))
							else:
								merged_points.append((x/100, y/100, z/100))

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
						curve_obj.ssx2_SplineProps.type = json_spline["SplineStyle"]
						collection.objects.link(curve_obj)

					else:										# Bézier Spline Curve

						new_bezier_points = []
						for j in range(0, len_merged_points, 3):
							print(j)

							point_curr = Vector(merged_points[j]) # Current Point

							pt = {
								'co': point_curr,
								'left_co': None,
								'right_co': None,
								'left_type': 'FREE',
								'right_type': 'FREE'
							}

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
								print("				MIDDLE POINT", j)

								point_prev = Vector(merged_points[j-1])
								point_next = Vector(merged_points[j+1])

								# pt['right_type'] = 'ALIGNED'
								# pt['left_type'] = 'ALIGNED'
								pt['right_type'] = 'FREE'
								pt['left_type'] = 'FREE'
								
								pt['right_co'] = point_next
								pt['left_co'] = point_prev


							print("	left", pt['left_co'])
							print("	curr", pt['co'])
							print("	right", pt['right_co'])

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

			test = self.import_icesaw()

			self.report({'INFO'}, "Imported")

		return {'FINISHED'}

		#project_mode = s.ssx2_WorldProjectMode
		io_props = s.ssx2_WorldImportExportProps
		use_names = io_props.importNames
		import_textures = io_props.importTextures

		path = s.ssx2_WorldImportExportProps.importPath
		if not os.path.exists(path): #.isdir
			self.report({'ERROR'}, f"Import Path does not exist")
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
		
		if io_props.importPatches:
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

		io_props = context.scene.ssx2_WorldImportExportProps
		# if context.scene.ssx2_WorldProjectMode == 'BINARY':
		if context.scene.bx_PlatformChoice != 'ICE':
			prop_split(col, io_props, 'worldChoice', "World Choice")
			if io_props.worldChoice == 'CUSTOM':
				prop_split(col, io_props, 'worldChoiceCustom', 'Custom Choice')

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
		# make a drop down panel/box for each category

		# inst_row = col.row() # INSTANCES
		# inst_row.prop(context.scene, 'ssx2_ModelForAddInstance', text='')
		# inst_row.operator(SSX2_OP_AddInstance.bl_idname, icon='ADD')
		
		if bpy.data.collections.get('Patches') is None:
			col.operator(SSX2_OP_WorldInitiateProject.bl_idname, icon='ADD')

		spline_box = col.box()    # SPLINES
		spline_box.label(text="Splines")
		spl_box_row = spline_box.row()
		spl_box_row.operator(SSX2_OP_AddSplineNURBS.bl_idname, icon='ADD')
		spl_box_row.operator(SSX2_OP_AddSplineBezier.bl_idname, icon='ADD')

		patch_box = col.box()    # PATCHES
		#patch_box.scale_y = 0.8
		patch_box.label(text="Patches")
		patch_box_row = patch_box.row()
		patch_box_row.prop(context.scene.ssx2_WorldUIProps, 'patchMaterialChoice', text='')
		patch_box_row.prop(context.scene.ssx2_WorldUIProps, 'patchTypeChoice', text='')
		patch_box_row2 = patch_box.row()
		patch_box_row2.operator(SSX2_OP_AddControlGrid.bl_idname, icon='ADD')
		patch_box_row2.operator(SSX2_OP_AddPatch.bl_idname, icon='ADD')
		patch_box.operator(SSX2_OP_ToggleControlGrid.bl_idname)
		prop_split(patch_box, context.scene.ssx2_WorldUIProps, 'patchSelectByType', "Select by Type")


class SSX2_WorldImportPanel(SSX2_Panel):
	bl_idname = 'SSX2_PT_world_import'
	bl_label = 'World Import'
	bl_options = {'DEFAULT_CLOSED'}
	bl_parent_id = 'SSX2_PT_world'

	# @classmethod
	# def poll(self, context):
	# 	return True

	def draw(self, context):
		io_props = context.scene.ssx2_WorldImportExportProps
		col = self.layout.column()
		prop_split(col, io_props, 'importPath', "Import Path", spacing=0.4)

		# if context.scene.ssx2_WorldProjectMode == 'BINARY':
		if context.scene.bx_PlatformChoice != 'ICE':
			col_row = col.row()
			col_row.prop(io_props, "importNames")
			col_row.prop(io_props, "importTextures")

		#col.prop(io_props, "importSplines")
		splines_box = col.box()
		spl_box_col = splines_box.column()
		spl_header_row = spl_box_col.row(align=True)
		spl_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if io_props.expandImportSplines\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportSplines'
		spl_header_row.prop(io_props, "importSplines", text="Splines")
		if io_props.expandImportSplines:
			spl_box_col.prop(io_props, "splineImportAsNURBS", text="As NURBS")
			#prop_enum_horizontal(spl_box_col, io_props, 'patchImportGrouping', "Grouping", spacing=0.3)


		patches_box = col.box()
		pch_col_box = patches_box.column()
		pch_header_row = pch_col_box.row(align=True)
		pch_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if io_props.expandImportPatches\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportPatches'
		pch_header_row.prop(io_props, "importPatches", text="Patches")
		#pch_header_row.prop(io_props, "patchImportAsControlGrid", text="As Control Grid")
		if io_props.expandImportPatches:
			pch_col_box.prop(io_props, "patchImportAsControlGrid", text="As Control Grid")
			prop_enum_horizontal(pch_col_box, io_props, 'patchImportGrouping', "Grouping", spacing=0.3)
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
		io_props = context.scene.ssx2_WorldImportExportProps
		col = self.layout.column()
		prop_split(col, io_props, 'exportPath', 'Export Path', spacing=0.4)
		patches_row = col.row()
		patches_row.prop(io_props, "exportPatches", text="Patches")
		#patches_row.prop(io_props, "exportPatchesOverride", text="Override")
		splines_row = col.row()
		splines_row.prop(io_props, "exportSplines", text="Splines")
		splines_row.prop(io_props, "exportSplinesOverride", text="Override")

		col.operator(SSX2_OP_WorldExport.bl_idname)

class SSX2_WorldInstancePanel(SSX2_Panel):
	bl_label = "BX Model Instance"
	bl_idname = "OBJECT_PT_SSX2_Model_Instance"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"
	bl_options = {"HIDE_HEADER"}

	@classmethod
	def poll(cls, context):
		return context.scene.bx_GameChoice == 'SSX2' and \
		(context.object is not None and context.object.type == 'EMPTY')

	def draw(self, context):
		obj = context.object

		col = self.layout.column()
		prop_split(col, context.object, 'ssx2_ModelForInstance', "Model")
		row = col.row()
		row.prop(context.object, 'show_instancer_for_viewport', text='Show Instancer')
		row.prop(context.object, 'show_in_front')#, text='Show in Front')
		#prop_split(col, context.object, 'show_instancer_for_viewport', "Show Empty")


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

	SSX2_OP_BakeTest,

	SSX2_OP_AddSplineBezier,
	SSX2_OP_AddSplineNURBS,
	SSX2_OP_AddInstance,
	#SSX2_OP_BakeTest,
	SSX2_OP_WorldImport,
	SSX2_OP_WorldExport,
	SSX2_OP_WorldExpandUIBoxes,
	SSX2_OP_WorldInitiateProject,

	SSX2_WorldPanel,
	SSX2_WorldToolsPanel,
	SSX2_WorldImportPanel,
	SSX2_WorldExportPanel,
	SSX2_WorldInstancePanel, # properties panel
	SSX2_SplinePanel,

)

def ssx2_world_register():
	for c in classes:
		register_class(c)

	ssx2_world_patches_register()

	bpy.types.Scene.ssx2_WorldProjectMode = bpy.props.EnumProperty(name='Project Mode', items=enum_ssx2_world_project_mode, default='JSON')

	bpy.types.Scene.ssx2_WorldImportExportProps = bpy.props.PointerProperty(type=SSX2_WorldImportExportPropGroup)
	bpy.types.Scene.ssx2_WorldUIProps = bpy.props.PointerProperty(type=SSX2_WorldUIPropGroup)
	bpy.types.Object.ssx2_SplineProps = bpy.props.PointerProperty(type=SSX2_WorldSplinePropGroup)

	bpy.types.Object.ssx2_ModelForInstance   = bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_wmodel_for_inst, update=update_wmodel_for_inst)
	bpy.types.Scene.ssx2_ModelForAddInstance = bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_wmodel_for_inst)


def ssx2_world_unregister():
	ssx2_world_patches_unregister()

	del bpy.types.Object.ssx2_ModelForInstance
	del bpy.types.Scene.ssx2_ModelForAddInstance

	del bpy.types.Scene.ssx2_WorldImportExportProps
	del bpy.types.Scene.ssx2_WorldUIProps

	del bpy.types.Scene.ssx2_WorldProjectMode

	for c in classes:
		unregister_class(c)