import os
import json
import bpy

from bxtools.general.bx_utils import (
	BXT,
	adjust_path_points_linear,
)

def export_paths(bxt: BXT, indent: int) -> None | tuple:
	print("Exporting Paths")

	io = bpy.context.scene.ssx2_WorldImportExportProps

	if io.exportPathsGeneral:
		new_json = export_by_category(bxt, 'General')

		if new_json is None:
			return None

		json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath)) + '/AIP.json'

		with open(json_export_path, 'w') as f:
			json.dump(new_json, f, separators=(',', ':'), indent=indent)

	if io.exportPathsShowoff:
		new_json = export_by_category(bxt, 'Showoff')

		if new_json is None:
			return None

		json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath)) + '/SOP.json'

		with open(json_export_path, 'w') as f:
			json.dump(new_json, f, separators=(',', ':'), indent=indent)

	return ()

def export_by_category(bxt: BXT, category: str) -> None | tuple:
	collection_name = "Paths " + category

	new_json = {
		"StartPosList": [],
		"AIPaths": [],
		"RaceLines": []
	}
	objects_ai = []
	objects_element = []


	print(category, collection_name, 'AIP' if category == 'General' else 'SOP')

	col_main = bpy.data.collections.get(collection_name)
	if col_main is None:
		bxt.error(f"'{collection_name}' collection not found")
		return None

	for obj in col_main.all_objects:
		if obj.ssx2_CurveMode == 'PATH_AI':
			objects_ai.append(obj)
		elif obj.ssx2_CurveMode == 'PATH_ELEMENTS':
			objects_element.append(obj)

	if len(objects_ai) == 0 and len(objects_element) == 0:
		bxt.error(f"No paths found in '{collection_name}' collection")
		return None


	#
	# General paths
	#
	
	for j, obj in enumerate(objects_ai):
		path_props = obj.ssx2_PathProps
		m = obj.matrix_world
		spline_points = [(m @ p.co.to_3d()) * 100 for p in obj.data.splines[0].points] # WorldScale

		new_entry = {
			"Name": obj.name,
			"Type":  2,
			"U1": 100,
			"U2": 4,
			"U3": path_props.aipaths_u3,
			"U4": 101,
			"U5": 4,
			"Respawnable": int(path_props.reset),
			"PathPos": spline_points[0].to_tuple() ,
			"PathPoints": adjust_path_points_linear(spline_points),
			"PathEvents": [	
				{
				"EventType":event.type_custom if event.type_enum == 'CUSTOM' else int(event.type_enum),
				"EventValue":event.value,
				"EventStart":event.start * 100, # WorldScale
				"EventEnd":event.end * 100, # WorldScale
				} 
				for event in path_props.events
			],
		}

		if path_props.start:
			new_json["StartPosList"].append(j)

		new_json["AIPaths"].append(new_entry)


	#
	# Element paths
	#

	for j, obj in enumerate(objects_element):
		path_props = obj.ssx2_PathProps
		m = obj.matrix_world
		spline_points = [(m @ p.co.to_3d()) * 100 for p in obj.data.splines[0].points] # WorldScale

		new_entry = {
			"Name": obj.name,
			"Type":  1,
			"U0": 0,
			"U1": 4,
			"U2": path_props.eventpaths_u2 * 100, # WorldScale
			"PathPos": spline_points[0].to_tuple() ,
			"PathPoints": adjust_path_points_linear(spline_points),
			"PathEvents": [	
				{
				"EventType":event.type_custom if event.type_enum == 'CUSTOM' else int(event.type_enum),
				"EventValue":event.value,
				"EventStart":event.start * 100, # WorldScale
				"EventEnd":event.end * 100, # WorldScale
				} 
				for event in path_props.events
			],
		}

		new_json["RaceLines"].append(new_entry)

	return new_json