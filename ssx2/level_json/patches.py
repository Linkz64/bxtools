import os
import json
import bpy

from bxtools.general.bx_utils import (BXT)

def export_patches(bxt: BXT, indent: int) -> None | tuple:
	print("Exporting Patches")

	do_lightmaps = True
	to_create_for_lightmaps = [] # put the split cages here (4x4s)
	# then create the objects

	T_SURFACE_PATCH = 0
	T_CONTROL_GRID = 1
	T_SPLINE_CAGE = 2

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
						patch_objects.append((T_SPLINE_CAGE, sub_obj, obj))
					elif sub_obj.type == 'SURFACE':
						patch_objects.append((T_SURFACE_PATCH, sub_obj, obj))
					elif sub_obj.ssx2_PatchProps.isControlGrid:
						patch_objects.append((T_CONTROL_GRID, sub_obj, obj))
					# with parent (0/1/2 sub_obj, obj)
					# no parent (0/1/2, sub_obj, None) and do an is None check instead of == 3
		elif obj.ssx2_CurveMode == 'CAGE':
			patch_objects.append((T_SPLINE_CAGE, obj))
		elif obj.type == 'SURFACE':
			patch_objects.append((T_SURFACE_PATCH, obj))
		elif obj.ssx2_PatchProps.isControlGrid:
			patch_objects.append((T_CONTROL_GRID, obj))

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


	for obj_information in patch_objects:
		obj_type = obj_information[0]
		obj = obj_information[1]
		
		if len(obj_information) > 2: # blender asset
			inst_obj = obj_information[2]
			
			obj_name = inst_obj.name + '_' + obj.name

			# m = inst_obj.matrix_world # works alone but sub objects have to be applied
			col_off = inst_obj.instance_collection.instance_offset

			m_a = obj.matrix_world
			loc_a, rot_a, sca_a = m_a.decompose()
			loc_a = loc_a - col_off
			m_a = Matrix.LocRotScale(loc_a, rot_a, sca_a)

			m = inst_obj.matrix_world @ m_a
		else:
			obj_name = obj.name
			m = obj.matrix_world

		props = obj.ssx2_PatchProps
		print(obj_name)

		if obj_type == T_SPLINE_CAGE: # export spline cage
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

			tex = "0000.png"
			if mat is not None:
				img_node = mat.node_tree.nodes.get("Image Texture")
				if img_node is not None:
					img = img_node.image
					if img is not None:
						if img.file_format == 'PNG' and img.source == 'FILE':
							png_folder, tex = os.path.split(img.filepath_from_user())

							# print(img.filepath)
							# print(img.filepath_from_user())
							# print(img.filepath_raw)
						else:
							self.report({'WARNING'}, f"{img.name} is not a valid PNG")


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

				name = f"{obj_name}_{i}"

				patch_points = []
				for uh in patch:
					for p in uh:
						x, y, z = p
						patch_points.append((x, y, z))

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

				if do_lightmaps:
					to_create_for_lightmaps.append((obj, export_counts['patch_segments']))

				export_counts['patch_segments'] += 1









		elif obj_type == T_SURFACE_PATCH: # export surface patch

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
					img_node = mat.node_tree.nodes.get("Image Texture")
					if img_node is not None:
						img = img_node.image
						if img is not None:
							if img.file_format == 'PNG' and img.source == 'FILE':
								png_folder, tex = os.path.split(img.filepath_from_user())
							else:
								self.report({'WARNING'}, f"{img.name} is not a valid PNG")

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

		elif obj_type == T_CONTROL_GRID: # export control grid
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
					img_node = mat.node_tree.nodes.get("Image Texture")
					if img_node is not None:
						img = img_node.image
						if img is not None:
							if img.file_format == 'PNG' and img.source == 'FILE':
								png_folder, tex = os.path.split(img.filepath_from_user())
							else:
								self.report({'WARNING'}, f"{img.name} is not a valid PNG")

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

		else:
			print("oops")
			return {'CANCELLED'}






	










	with open(json_export_path, 'w') as f:
		if do_json_indend:
			json.dump(temp_json, f, indent=2)
		else:
			json.dump(temp_json, f)

	# ENDOF Export Patches