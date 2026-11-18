import json
import bpy

from bxtools.general.bx_utils import (
	BXT,
	adjust_path_points_linear,
)

def export_paths(bxt: BXT, indent: int) -> None | tuple:
	print("Exporting Paths")

	if io.exportPathsGeneral:
		export_paths_by_category(bxt, indent, 'General')
	if io.exportPathsShowoff:
		export_paths_by_category(bxt, indent, 'Showoff')


def export_paths_by_category(bxt: BXT, indent: int, category: str) -> None | tuple:
	col_main_name = "Paths " + category
	extension = 'AIP' if category == 'General' else 'SOP'

	print(category, col_main_name, extension)

	col_main = bpy.data.collections.get(col_main_name)
	if col_main is None:
		self.report({'ERROR'}, f"'{col_main_name}' collection not found")
		return {'CANCELLED'}

	all_objects = col_main.all_objects

	if len(all_objects) == 0:
		self.report({'ERROR'}, f"No objects found in '{col_main_name}' collection")
		return {'CANCELLED'}

	json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath)) + '/' + extension + '.json'

	objects_ai = []
	objects_element = []

	for obj in all_objects:
		if obj.ssx2_CurveMode == 'PATH_AI':
			objects_ai.append(obj)
		elif obj.ssx2_CurveMode == 'PATH_ELEMENTS':
			objects_element.append(obj)

	if len(objects_ai) == 0 and len(objects_element) == 0:
		self.report({'ERROR'}, f"No paths found in '{col_main_name}' collection")
		return {'CANCELLED'}

	temp_json = {
		"StartPosList": [],
		"AIPaths": [],
		"RaceLines": []
	}

	# 
	# General paths
	# 
	
	for j, obj in enumerate(objects_ai):
		path_props = obj.ssx2_PathProps
		m = obj.matrix_world

		new_data = {
			"Name": obj.name,
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

		if obj.type == "EMPTY":
			self.report({'ERROR'}, "Empties Not supported")
			return {'CANCELLED'}

			new_data["PathPos"] = tuple(post_transform_points), # WorldScale
			new_data["PathPoints"] = [tuple(child.location * 100) for child in obj.children_recursive], # WorldScale
		else:
			spline_points = obj.data.splines[0].points

			post_transform_points = []
			for p in spline_points:
				world_pos = m @ p.co.to_3d()
				post_transform_points.append(world_pos * 100)

			new_data["PathPos"] = post_transform_points[0].to_tuple() # WorldScale
			adjusted_points = adjust_path_points_linear(post_transform_points)
			new_data["PathPoints"].extend(adjusted_points)

		for event in path_props.events:
			temp_event = {
				"EventType":event.type_custom if event.type_enum == 'CUSTOM' else int(event.type_enum),
				"EventValue":event.value,
				"EventStart":event.start * 100, # WorldScale
				"EventEnd":event.end * 100, # WorldScale
			}
			new_data["PathEvents"].append(temp_event)

		if path_props.start:
			temp_json["StartPosList"].append(j)

		temp_json["AIPaths"].append(new_data)

	# 
	# Element paths
	# 

	for j, obj in enumerate(objects_element):
		path_props = obj.ssx2_PathProps
		m = obj.matrix_world

		new_data = {
			"Name": obj.name,
			"Type":  1,
			"U0": 0,
			"U1": 4,
			"U2": path_props.eventpaths_u2 * 100, # WorldScale
			"PathPos": None,
			"PathPoints": [],
			"PathEvents": [],
		}

		spline_points = obj.data.splines[0].points

		post_transform_points = []
		for p in spline_points:
			world_pos = m @ p.co.to_3d()
			post_transform_points.append(world_pos * 100)

		new_data["PathPos"] = post_transform_points[0].to_tuple() # WorldScale
		adjusted_points = adjust_path_points_linear(post_transform_points)
		new_data["PathPoints"].extend(adjusted_points)

		for event in path_props.events:
			temp_event = {
				"EventType":event.type_custom if event.type_enum == 'CUSTOM' else int(event.type_enum),
				"EventValue":event.value,
				"EventStart":event.start * 100, # WorldScale
				"EventEnd":event.end * 100, # WorldScale
			}
			new_data["PathEvents"].append(temp_event)

		temp_json["RaceLines"].append(new_data)

	with open(json_export_path, 'w') as f:
		if do_json_indend:
			json.dump(temp_json, f, indent=2)
		else:
			json.dump(temp_json, f, separators=(',', ':'))
