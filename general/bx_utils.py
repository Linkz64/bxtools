import bpy
import struct
import numpy as np
from os import path

templates_append_path = path.dirname(__file__)[:-7]+"general/templates.blend"

if __name__ == '__main__': # for DXT texture testing
	def get_string(f, x):
		a = f.read(x)
		return a.decode('utf-8').strip('\x00')
	import sys
	#import os; root = os.path.abspath(os.curdir).replace("general", "external")
	sys.path.append(sys.path[0].replace("general", "external"))
	from DXTDecompress import DXTBuffer
	from PIL import Image

else:
	from .bx_struct import get_string
	from ..external.DXTDecompress import DXTBuffer


### UI

def bx_report(string, title="Error", icon='ERROR'):
	"""
	Popup Menu
	string = text/description
	title = "Error"
	icon = 'ERROR'
	"""
	def report(self, context):
		self.layout.label(text=string)

	bpy.context.window_manager.popup_menu(report, title=title, icon=icon)

def prop_enum_horizontal(layout, data, field, label, spacing=0.5, **prop_kwargs):
	split = layout.split(factor=spacing)
	split.label(text=label)
	split_row = split.row()
	split_row.prop(data, field, expand=True)



### Blender Internal

def run_without_update(func):
	# run without view layer update
	from bpy.ops import _BPyOpsSubModOp
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


### Math

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



def patch_points_decode(encoded):

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

def patch_points_encode(raw):

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

	mid_table = [vec((0.0, 0.0, 0.0))]*16
	encoded   = [vec((0.0, 0.0, 0.0))]*16

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