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
		new_json = export_by_category(bxt, indent, 'General')
		json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath)) + '/AIP.json'

		with open(json_export_path, 'w') as f:
			json.dump(new_json, f, separators=(',', ':'), indent=indent)

	if io.exportPathsShowoff:
		new_json = export_by_category(bxt, indent, 'Showoff')
		json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath)) + '/SOP.json'

		with open(json_export_path, 'w') as f:
			json.dump(new_json, f, separators=(',', ':'), indent=indent)

	return ()

def export_by_category(bxt: BXT, indent: int, category: str) -> None | tuple:
	col_main_name = "Paths " + category

	new_json = {
		"StartPosList": [],
		"AIPaths": [],
		"RaceLines": []
	}
	objects_ai = []
	objects_element = []


	print(category, col_main_name, 'AIP' if category == 'General' else 'SOP')

	col_main = bpy.data.collections.get(col_main_name)
	if col_main is None:
		bxt.error(f"'{col_main_name}' collection not found")
		return {'CANCELLED'}

	all_objects = col_main.all_objects

	if len(all_objects) == 0:
		bxt.error(f"No objects found in '{col_main_name}' collection")
		return {'CANCELLED'}

	for obj in all_objects:
		if obj.ssx2_CurveMode == 'PATH_AI':
			objects_ai.append(obj)
		elif obj.ssx2_CurveMode == 'PATH_ELEMENTS':
			objects_element.append(obj)

	if len(objects_ai) == 0 and len(objects_element) == 0:
		bxt.error(f"No paths found in '{col_main_name}' collection")
		return {'CANCELLED'}


	# 
	# General paths
	# 
	
	for j, obj in enumerate(objects_ai):
		path_props = obj.ssx2_PathProps
		m = obj.matrix_world

		new_entry = {
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

		spline_points = [(m @ p.co.to_3d()) * 100 for p in obj.data.splines[0].points] # WorldScale
		new_entry["PathPos"] = spline_points[0].to_tuple() 
		new_entry["PathPoints"].extend(adjust_path_points_linear(spline_points))

		for event in path_props.events:
			temp_event = {
				"EventType":event.type_custom if event.type_enum == 'CUSTOM' else int(event.type_enum),
				"EventValue":event.value,
				"EventStart":event.start * 100, # WorldScale
				"EventEnd":event.end * 100, # WorldScale
			}
			new_entry["PathEvents"].append(temp_event)

		if path_props.start:
			new_json["StartPosList"].append(j)

		new_json["AIPaths"].append(new_entry)


	# 
	# Element paths
	# 

	for j, obj in enumerate(objects_element):
		path_props = obj.ssx2_PathProps
		m = obj.matrix_world

		new_entry = {
			"Name": obj.name,
			"Type":  1,
			"U0": 0,
			"U1": 4,
			"U2": path_props.eventpaths_u2 * 100, # WorldScale
			"PathPos": None,
			"PathPoints": [],
			"PathEvents": [],
		}

		spline_points = [(m @ p.co.to_3d()) * 100 for p in obj.data.splines[0].points] # WorldScale
		new_entry["PathPos"] = spline_points[0].to_tuple() 
		new_entry["PathPoints"].extend(adjust_path_points_linear(spline_points))

		for event in path_props.events:
			temp_event = {
				"EventType":event.type_custom if event.type_enum == 'CUSTOM' else int(event.type_enum),
				"EventValue":event.value,
				"EventStart":event.start * 100, # WorldScale
				"EventEnd":event.end * 100, # WorldScale
			}
			new_entry["PathEvents"].append(temp_event)

		new_json["RaceLines"].append(new_entry)

	return new_json