import os
import json
import bpy

from bxtools.general.bx_utils import calc_coefficients

def export_splines(bxt, indent: int) -> None | tuple:
	print("Exporting Splines")

	io = bpy.context.scene.ssx2_WorldImportExportProps
	scale = bpy.context.scene.bx_WorldScale

	json_export_path = os.path.abspath(bpy.path.abspath(io.exportFolderPath))+'/Splines.json'

	spline_collection = bpy.data.collections.get("Splines")
	if spline_collection is None:
		bxt.error("'Splines' collection not found")
		return None
	
	if not os.path.isfile(json_export_path):
		bxt.error(f"'Splines.json' not found.\n{json_export_path}")
		return None

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
			bxt.error("'Splines' collection is empty. Disable 'Splines' \
export or enable 'Override' to delete the JSON content")

	else:
		final_splines = []
		names = []

		for obj in spline_objects:

			props = obj.ssx2_SplineProps
			m = obj.matrix_world

			print("\n    ", obj.name)

			all_spline_islands = []

			get_name = False
			for i, s in enumerate(obj.data.splines):
				current_points = []

				if s.type != 'BEZIER':
					continue

				if len(s.bezier_points) < 2:
					bxt.error(f"Not enough points in object '{obj.name}'. Spline index {i}")
					bpy.ops.object.select_all(action='DESELECT')
					obj.select_set(True)
					set_active(obj)
					return None


				# first bezier point
				p = s.bezier_points[0]
				current_points.append( (m @ p.co)           * scale )
				current_points.append( (m @ p.handle_right) * scale )

				# inbetween bezier points
				for j in range(1, len(s.bezier_points) - 1):
					p = s.bezier_points[j]
					current_points.append( (m @ p.handle_left)  * scale )
					current_points.append( (m @ p.co)           * scale )
					current_points.append( (m @ p.handle_right) * scale )

				# last bezier point
				p = s.bezier_points[-1]
				current_points.append( (m @ p.handle_left) * scale )
				current_points.append( (m @ p.co)          * scale )


				if len(current_points) != 0:
					all_spline_islands.append(current_points)
					get_name = True
				else:
					print(f"No points in {obj.name} spline {i}")

			if get_name:
				names.append(obj.name)

			for _si, spline_island in enumerate(all_spline_islands):
				segments = [] # split to segments of 4 points

				for i in range(0, len(spline_island), 3):
					segment_points = spline_island[i:i + 4]

					if i == len(spline_island) - 1:
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
					"SplineName": obj.name + '.' + str(_si),
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
						bxt.warn("BXT Error occurred. Skipping.")

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

				# export_counts['splines'] = len(final_splines)
	
	with open(json_export_path, 'w') as f:
		json.dump(new_json, f, separators=(',', ':'), indent=indent)

	return ()

