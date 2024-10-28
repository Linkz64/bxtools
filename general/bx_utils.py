import bpy
from bpy.ops import _BPyOpsSubModOp
from mathutils import Vector
import struct
import numpy as np
from os import path
from math import ceil

from .bx_struct import get_string
from ..external.DXTDecompress import DXTBuffer

templates_append_path = path.dirname(__file__)[:-7]+"general/templates.blend"

class BXT:
	def __init__(self, bpyself, context):
		print(bpyself, context)
	def info(bpyself, string):
		bpyself.report({'INFO'}, string)
	def warn(bpyself, string):
		bpyself.report({'WARNING'}, string)
	def error(bpyself, string):
		bpyself.report({'ERROR'}, string)

	def popup(string, title="Error", icon='ERROR'):
		def report(self, context):
			self.layout.label(text=string)
		bpy.context.window_manager.popup_menu(report, title=title, icon=icon)


### UI

def prop_enum_horizontal(layout, data, field, label, spacing=0.5, **prop_kwargs):
	split = layout.split(factor=spacing)
	split.label(text=label)
	split_row = split.row()
	split_row.prop(data, field, expand=True)


### Blender Internal

def set_active(obj):
	#bpy.ops.object.select_all(action='DESELECT')
	bpy.context.view_layer.objects.active = obj
	obj.select_set(True)

def run_without_update(func):
	# run without view layer update
	view_layer_update = _BPyOpsSubModOp._view_layer_update
	def dummy_view_layer_update(context):
		pass
	try:
		_BPyOpsSubModOp._view_layer_update = dummy_view_layer_update
		func()
	finally:
		_BPyOpsSubModOp._view_layer_update = view_layer_update

def get_layer_collection(layer_col, col_name):
	"""Get matching collection from the outliner"""
	found = None
	if layer_col.name == col_name:
		return layer_col
	for layer in layer_col.children:
		#print("layer", layer)
		found = get_layer_collection(layer, col_name)
		if found:
			return found

def collection_grouping(name, parent_col, group_size, increment):
	#collection name/prefix, parent collection, grouping size, increment
	col_name = f"{name}.{int(increment / group_size)+1}"
	new_col = bpy.data.collections.get(col_name)
	if new_col is None:
		new_col = bpy.data.collections.new(col_name)
	if not bpy.context.scene.user_of_id(new_col): # if not in scene/layer bring it
		parent_col.children.link(new_col)
	return new_col


def getset_collection_to_target(name, target_collection): # move=False
	"""Gets or Creates collection and parents it to target collection"""
	col = bpy.data.collections.get(name)
	if col is None:
		col = bpy.data.collections.new(name)
		target_collection.children.link(col)
	# elif col.name != name:
	# 	col = bpy.data.collections.new(name)
	# 	target_collection.children.link(col)
	# if target_collection.children.get(name) is None:
	# 	target_collection.children.link(col)
	return col

def getset_collection(name):
	"""Creates/Gets collection"""
	col = bpy.data.collections.get(name)
	if col is None:
		col = bpy.data.collections.new(name)
	return col


def getset_instance_collection(model, name):
	"""Checks if Instance Collection exists, creates it if it doesn't, then return the name of the Instance Collection
	model = Chosen mesh/model object
	name = Name of existing/new instance collection"""

	col = bpy.data.collections.get(name)
	if col is None:
		bpy.data.collections.new(name)

	if col not in model.users_collection:
		bpy.data.collections[name].objects.link(model)

	for obj in model.children:
		if obj.type != 'MESH':
			continue
		if col not in obj.users_collection:
			bpy.data.collections[name].objects.link(obj)
	return name

def append_geonodes(node_tree_name):
	if not path.isfile(templates_append_path):
		print(f"Failed to find {templates_append_path}")
		return None

	with bpy.data.libraries.load(templates_append_path, link=False) as (data_from, data_to):
		if node_tree_name in data_from.node_groups:
			data_to.node_groups = [node_tree_name]
		else:
			print(f"Failed to append geonodes from {templates_append_path}")
			return None

	node_tree = bpy.data.node_groups.get(node_tree_name)
	if node_tree is None:
		print(f"Failed to append geonodes from {templates_append_path}")
		return None
	return node_tree

def append_material(mat_name):
	if not path.isfile(templates_append_path):
		print(f"Failed to find {templates_append_path}")
		return None

	with bpy.data.libraries.load(templates_append_path, link=False) as (data_from, data_to):
		if mat_name in data_from.materials:
			data_to.materials = [mat_name]
		else:
			print(f"Failed to append material from {templates_append_path}")
			return None

	mat = bpy.data.materials.get(mat_name)
	if mat is None:
		print(f"Failed to append material from {templates_append_path}")
		return None
	return mat


### Math

def midpoint(p1, p2):
	return (p1 + p2) / 2

def normalize(input_list, sum_target=100, key=None):
	"""
	Normalizes values in a list to add up to sum_target (100 by default)
	"""
	length = len(input_list)
	if key is None:
		a = sum(input_list) - sum_target
		b = a / length
		return [i - b for i in input_list]
	elif key is not None and type(key) is int and len(input_list[0]) > 1:
		a = sum([i[key] for i in input_list]) - sum_target
		b = a / length
		for i in range(length):
			input_list[i][key] = input_list[i][key] - b
	else:
		return None # or raise
	return input_list

def bone_rel_loc(bone): # do the opposite of this for 3 skel import? # forgot what i meant by this
	"""Get bone location relative to parent """
	if bone.parent == None:
		relative_bone = bone.matrix_local
	else:
		relative_bone = bone.parent.matrix_local.inverted() @ bone.matrix_local # relative to parent bone
	return (relative_bone[1][3], relative_bone[2][3], relative_bone[0][3])

def get_custom_prop_vec3(item, key):
	"""
	Get first 3 values from a float array custom property
	item = object or bone (eg bpy.data.objects['Cube'])
	key = name of custom property (eg 'Extra Location')
	"""
	return (item[key][0], item[key][1], item[key][2])

def get_custom_prop_vec4(item, key):
	"""
	Get first 4 values from a float array custom property
	item = object or bone (eg bpy.data.objects['Cube'])
	key = name of custom property (eg 'Extra Bone Quaternion')
	"""
	return (item[key][0], item[key][1], item[key][2], item[key][3])


def interpolate_patch_uvs(uv_points, divisions): # gen
	"""Turns a uv square (4 points) into a grid of 16 points"""
	new_uv_points = []
	for i in range(divisions):
		for j in range(divisions):
			u = i / (divisions - 1)
			v = j / (divisions - 1)
			interpolated_uv = (
				(1 - u) * (1 - v) * uv_points[0][0] + u * (1 - v) * uv_points[1][0] +
				(1 - u) * v * uv_points[2][0] + u * v * uv_points[3][0],
				(1 - u) * (1 - v) * uv_points[0][1] + u * (1 - v) * uv_points[1][1] +
				(1 - u) * v * uv_points[2][1] + u * v * uv_points[3][1]
			)
			new_uv_points.append(interpolated_uv)
	return new_uv_points

def lerp_uv(uv0, uv1, amount): # aka linear interpolate vector2
	uv0u = uv0[0]
	uv0v = uv0[1]
	uv1u = uv1[0]
	uv1v = uv1[1]

	new_u = uv0u + (uv1u - uv0u) * amount
	new_v = uv0v + (uv1v - uv0v) * amount
	return (new_u, new_v)

def fix_uvs_u(uvs, factor=0.01):
	uv0 = Vector(uvs[0])
	uv1 = Vector(uvs[1])
	uv2 = Vector(uvs[2])
	uv3 = Vector(uvs[3])

	uvs[0] = lerp_uv(uv0, uv1, factor)
	uvs[1] = lerp_uv(uv1, uv0, factor)
	uvs[2] = lerp_uv(uv2, uv3, factor)
	uvs[3] = lerp_uv(uv3, uv2, factor)
def fix_uvs_v(uvs, factor=0.01):
	uv0 = Vector(uvs[0])
	uv1 = Vector(uvs[1])
	uv2 = Vector(uvs[2])
	uv3 = Vector(uvs[3])

	uvs[0] = lerp_uv(uv0, uv2, factor)
	uvs[2] = lerp_uv(uv2, uv0, factor)
	uvs[1] = lerp_uv(uv1, uv3, factor)
	uvs[3] = lerp_uv(uv3, uv1, factor)

def enc_to_mid_eq1(a, b,                      encoded, mid_table):
	return encoded[a] / 3 + mid_table[b]
def enc_to_mid_eq2(a, b, mid_a,               encoded, mid_table):
	return (encoded[a] + encoded[b]) / 3 + mid_table[mid_a]
def enc_to_mid_eq3(a,    mid_a, mid_b, mid_c, encoded, mid_table):
	return encoded[a] + encoded[mid_a] + encoded[mid_b] + encoded[mid_c]
def mid_to_raw_eq1(a, b,                    mid_table, raw):
	return mid_table[a] / 3 + raw[b]
def mid_to_raw_eq2(a, b, mid_a,             mid_table, raw):
	return (mid_table[a] + mid_table[b]) / 3 + raw[mid_a]
def mid_to_raw_eq3(a,    mid_a, mid_b, mid_c, mid_table):
	return mid_table[a] + mid_table[mid_a] + mid_table[mid_b] + mid_table[mid_c]

def patch_points_decode(encoded):
	mid_table = [Vector((0.0, 0.0, 0.0))]*16
	raw       = [Vector((0.0, 0.0, 0.0))]*16

	for i in range(0, 16, 4): # makes this list: [0, 4, 8, 12]
		mid_table[i  ] = encoded[i]
		mid_table[i+1] = enc_to_mid_eq1( i+1, i,            encoded, mid_table)
		mid_table[i+2] = enc_to_mid_eq2( i+2, i+1, i+1,     encoded, mid_table)
		mid_table[i+3] = enc_to_mid_eq3( i+3, i+2, i+1,  i, encoded, mid_table)

	raw[ 0] = mid_table[0]
	raw[ 1] = mid_table[1]
	raw[ 2] = mid_table[2]
	raw[ 3] = mid_table[3]

	raw[ 4] = mid_to_raw_eq1( 4,  0,         mid_table, raw)
	raw[ 5] = mid_to_raw_eq1( 5,  1,         mid_table, raw)
	raw[ 6] = mid_to_raw_eq1( 6,  2,         mid_table, raw)
	raw[ 7] = mid_to_raw_eq1( 7,  3,         mid_table, raw)

	raw[ 8] = mid_to_raw_eq2( 8,  4,  4,     mid_table, raw)
	raw[ 9] = mid_to_raw_eq2( 9,  5,  5,     mid_table, raw)
	raw[10] = mid_to_raw_eq2(10,  6,  6,     mid_table, raw)
	raw[11] = mid_to_raw_eq2(11,  7,  7,     mid_table, raw)

	raw[12] = mid_to_raw_eq3(12,  8,  4,  0, mid_table)
	raw[13] = mid_to_raw_eq3(13,  9,  5,  1, mid_table)
	raw[14] = mid_to_raw_eq3(14, 10,  6,  2, mid_table)
	raw[15] = mid_to_raw_eq3(15, 11,  7,  3, mid_table)

	for i in range(16):
		raw[i] = Vector((raw[i][0], raw[i][1], raw[i][2], 1.0))

	return raw

def raw_to_mid_eq1(a, b, raw):
	return (raw[a] - raw[b]) * 3
def raw_to_mid_eq2(a, b, mid_a, raw, mid_table):
	return (raw[a] - raw[b]) * 3 - mid_table[mid_a]
def raw_to_mid_eq3(a,    mid_a, mid_b, mid_c, raw, mid_table):
	return raw[a] - mid_table[mid_a] - mid_table[mid_b] - mid_table[mid_c]
def mid_to_enc_eq1(a, b, mid_table):
	return (mid_table[a] - mid_table[b]) * 3
def mid_to_enc_eq2(a, b, end_a, mid_table, encoded):
	return (mid_table[a] - mid_table[b]) * 3 - encoded[end_a]
def mid_to_enc_eq3(a,         mid_a, mid_b, mid_c, mid_table, encoded):
	return mid_table[a] - encoded[mid_a] - encoded[mid_b] - encoded[mid_c]

def patch_points_encode(raw):
	mid_table = [Vector((0.0, 0.0, 0.0))]*16
	encoded   = [Vector((0.0, 0.0, 0.0))]*16

	for i in range(0, 16, 4): # makes this list: [0, 4, 8, 12]
		mid_table[i  ] = raw[i]
		mid_table[i+1] = raw_to_mid_eq1(i+1, i, raw)
		mid_table[i+2] = raw_to_mid_eq2(i+2, i+1, i+1, raw, mid_table)
		mid_table[i+3] = raw_to_mid_eq3(i+3, i+2, i+1, i, raw, mid_table)

	encoded[ 0] = mid_table[0]
	encoded[ 1] = mid_table[1]
	encoded[ 2] = mid_table[2]
	encoded[ 3] = mid_table[3]

	encoded[ 4] = mid_to_enc_eq1(4, 0, mid_table)
	encoded[ 5] = mid_to_enc_eq1(5, 1, mid_table)
	encoded[ 6] = mid_to_enc_eq1(6, 2, mid_table)
	encoded[ 7] = mid_to_enc_eq1(7, 3, mid_table)

	encoded[ 8] = mid_to_enc_eq2( 8, 4, 4, mid_table, encoded)
	encoded[ 9] = mid_to_enc_eq2( 9, 5, 5, mid_table, encoded)
	encoded[10] = mid_to_enc_eq2(10, 6, 6, mid_table, encoded)
	encoded[11] = mid_to_enc_eq2(11, 7, 7, mid_table, encoded)

	encoded[12] = mid_to_enc_eq3(12,  8, 4, 0, mid_table, encoded)
	encoded[13] = mid_to_enc_eq3(13,  9, 5, 1, mid_table, encoded)
	encoded[14] = mid_to_enc_eq3(14, 10, 6, 2, mid_table, encoded)
	encoded[15] = mid_to_enc_eq3(15, 11, 7, 3, mid_table, encoded)

	#encoded.reverse() # does this round the floats?
	encoded = list(reversed(encoded))

	return encoded

## Splines

def calc_spline_segments(num_points): # segments of 4
	return ceil((num_points - 1) / 3)

def segment_spline(all_splines): # segments into groups of 4
	expected_segments = ceil((len(all_splines[0]) - 1) / 3)
	segments = [[] for i in range(expected_segments)]
	for points in all_splines:
		for i in range(0, len(points), 3):
			segment_points = points[i:i + 4]
			if i == len(points) - 1:
				break
			segments[i // 3].append(segment_points)
	return segments

def bezier_to_raw(bezier_points, m, scale): # aka bezier to poly or nurbs
	bez_points_compare = len(bezier_points)-1
	spline = []
	for i, p in enumerate(bezier_points):
		points = []

		if (i != 0) and (i != bez_points_compare): # mid points
			points.append(scale * (m @ p.handle_left))
			points.append(scale * (m @ p.co))
			points.append(scale * (m @ p.handle_right))
		elif i == 0: # first point
			points.append(scale * (m @ p.co))
			points.append(scale * (m @ p.handle_right))
		elif i == bez_points_compare: # last point
			points.append(scale * (m @ p.handle_left))
			points.append(scale * (m @ p.co))

		spline += points
	return spline

def bezier_to_raw_old(obj, m=None, count=4):
	scale = bpy.context.scene.bx_WorldScale
	if m is None:
		m = obj.matrix_world
	splines = obj.data.splines
	all_splines = []
	for i in range(count):
		s = splines[i]
		current_spline = []

		if s.type != 'BEZIER':
			self.report({'WARNING'}, f"{obj} Splines must be bezier type (with handles)")
			return None
		if len(s.bezier_points) < 2:
			self.report({'WARNING'}, f"Not enough points in spline {i+1}")
			return None

		for j, p in enumerate(s.bezier_points):
			current_points = []

			if j == 0: # first
				current_points.append(scale * (m @ p.co))
				current_points.append(scale * (m @ p.handle_right))
			elif j == len(s.bezier_points)-1: # last
				current_points.append(scale * (m @ p.handle_left))
				current_points.append(scale * (m @ p.co))
			elif (j != 0) and (j != len(s.bezier_points)-1): # mids
				current_points.append(scale * (m @ p.handle_left))
				current_points.append(scale * (m @ p.co))
				current_points.append(scale * (m @ p.handle_right))

			current_spline += current_points

		all_splines.append(current_spline)

	row1_length = len(current_spline)
	if row1_length * count != sum([len(i) for i in all_splines]):
		print(f"{obj.name} Failed! Number of points must match on all splines")
		return None

	return all_splines


def double_quad_cage(raw): # essentially subdivides along v but only on 4 splines
	temp_strip1 = [[] for i in range(4)]
	temp_strip2 = [[] for i in range(4)]

	for i in range(len(raw[0])):
		og1 = raw[0][i]
		og2 = raw[1][i]
		og3 = raw[2][i]
		og4 = raw[3][i]

		new2 = midpoint(og1, og2) # handles scaled down to half
		new6 = midpoint(og3, og4)
		mid_a = midpoint(og2, og3) # middle of opposite handles
		mid_b = midpoint(new2, new6)

		new4 = midpoint(mid_a, mid_b) # middle point of the 2 patch strips

		new3 = midpoint(mid_a, new2)
		new5 = midpoint(mid_a, new6)

		temp_strip1[0].append(og1)
		temp_strip1[1].append(new2)
		temp_strip1[2].append(new3)
		temp_strip1[3].append(new4)

		temp_strip2[0].append(new4)
		temp_strip2[1].append(new5)
		temp_strip2[2].append(new6)
		temp_strip2[3].append(og4)

	yield temp_strip1
	yield temp_strip2


def adjust_path_points(spline_points):
	adjusted_points = [Vector(spline_points[1].co[:3]) - Vector(spline_points[0].co[:3])]

	for j in range(2, len(spline_points)):
		p = Vector(spline_points[j].co[:3])
		prev = Vector(spline_points[j - 1].co[:3])

		new_point = p - prev
		adjusted_points.append(new_point)

	return adjusted_points


### Mesh

def stitch_tristrips(polys):
	"""
	Connects every polygon/strip with a zero-area face and forms the final tristrip
	(Not recommended as a standalone tristripper but it is possible)

	example input: [[0, 1, 2], [6, 7, 8]] 
	output: [0, 1, 2, 2, 6, 6, 7, 8]

	example input: [[0, 1, 2, 3, 4, 5, 6, 7], [24, 22, 23, 25, 26, 27], [4, 8, 9, 10]]
	output: [0, 1, 2, 3, 4, 5, 6, 7, 7, 24, 24, 22, 23, 25, 26, 27, 27, 4, 4, 8, 9, 10]
	"""

	out = []
	out += polys[0] # add first list/poly
	out.append(polys[0][-1]) # duplicate last index of first list/poly

	for i in range(1, len(polys)): # go from index 1 (second list/poly) to last 

		out.append(polys[i][0])  # duplicate first index
		out += polys[i]          # add the indices of poly
		out.append(polys[i][-1]) # duplicate last index

	return out[:-1] # [:-1] remove the last index


def quad_to_strip(q):
	"""Swaps last 2 indices to make a zigzag for tristrip"""
	return [q[0], q[1], q[3], q[2]]

def quad_to_2_triangles(q):
	"""Swaps last 2 indices to make a zigzag and return 2 triangles"""
	#return [(q[0], q[1], q[3]), (q[1], q[3], q[2])]
	return [(q[0], q[1], q[3]), (q[3], q[1], q[2])]




### Bytes

def pack_string(v, x):
	"""v = value (name/string) x = max length
	pack string into bytes"""
	vLen = len(v)
	s = bytes(v, 'utf-8')

	if vLen < x:
		add_nulls = b'\00' * (x - vLen)
		s += add_nulls
	if vLen > x:
		s = s[:x]

	return s

def calc_padding_bytes(length, len_row):
	"""length = number of bytes (e.g 212)
	len_row = number of bytes in a row (e.g 16)"""
	return -(length % -len_row)

def padding_bytes(b, pad_byte=b'\xFF', num_rows=0, len_row=16):
	"""
	b=buffer
	pad_byte=b'\xFF'
	num_rows=0 (extra rows, not total rows)
	len_row=16 (how many bytes long a row is)"""
	padding_skip = calc_padding_bytes(len(b), len_row)#-(len(b) % -len_row)
	# len(b) can be though of as 'current offset'

	return bytearray(pad_byte)*padding_skip + bytearray(pad_byte)*len_row*num_rows # FF padding + FF extra row padding



def ssx2_get_xsh_texture(file_path):
	"""
	this format has compressed blocks which are 4x4 pixels
	the color intensity/index is stored in as 2-bit
	00 = 0, 01 = 1, 10 = 2, 11 = 3
	00 is max for color 0, 11 is max for color 1
	"""
	with open(file_path, 'rb') as f:
		magic = get_string(f, 4)

		if magic != 'SHPX':
			return None

		len_file = struct.unpack('i', f.read(4))[0]
		num_textures = struct.unpack('i', f.read(4))[0]
		ver_gimex = get_string(f, 4) # gimex version/format

		texture_names = []
		texture_offsets = []
		for i in range(num_textures):
			nam_texture = get_string(f, 4)
			off_texture = struct.unpack('i', f.read(4))[0]
			texture_names.append(nam_texture)
			texture_offsets.append(off_texture)

		textures = []
		widths_heights = []
		for i in range(num_textures):
			if i == 1:
				pass#break
			texture = []
			off_cursor = f.tell()

			f.seek(texture_offsets[i])

			matrix = struct.unpack('b', f.read(1))[0]
			off_next_chunk = struct.unpack('i', f.read(3)+b'\x00')[0]
			width  = struct.unpack('h', f.read(2))[0]
			height = struct.unpack('h', f.read(2))[0]
			f.seek(8, 1)

			widths_heights.append((width, height))
			
			if matrix == 125 or matrix == 96 or matrix == 120:
				_buffer = DXTBuffer(width, height)
				_buffer = _buffer.DXT1Decompress(f) # bytes object
				if __name__ == '__main__':
					new_image = Image.frombuffer('RGBA', (width, height), _buffer, 'raw', 'RGBA', 0 ,1)
					new_image.save(f"sample{i}.png")

				new_image = [pixel / 255 for pixel in _buffer]
				new_image = np.array(new_image[:])
				new_image = new_image.reshape((height, width, 4))
				new_image = np.rot90(new_image, 1, (0, 1))
				#new_image = np.flip(new_image, axis=1)
				new_image = new_image.ravel() #new_image = new_image.flatten().tolist()

				textures.append(new_image)
			elif matrix == 97:
				_buffer = DXTBuffer(width, height)
				_buffer = _buffer.DXT5Decompress(f) # maybe not the exact same
				
				if __name__ == '__main__':
					new_image = Image.frombuffer('RGBA', (width, height), _buffer, 'raw', 'RGBA', 0 ,1)
					new_image.save(f"sample{i}.png")

				new_image = [pixel / 255 for pixel in _buffer]
				new_image = np.array(new_image[:])
				new_image = new_image.reshape((height, width, 4))
				new_image = np.rot90(new_image, 1, (0, 1))
				new_image = new_image.ravel()

				textures.append(new_image)
			elif matrix == 112: # long name
				pass
			else:
				print("NEW MATRIX TYPE", matrix, f.tell())
				return None
	return (texture_names, textures, widths_heights)
			

if __name__ == '__main__':
	ssx2_get_xsh_texture("X:/Downloads/bx_test/DXT_Test/trick.xsh")