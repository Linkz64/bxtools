import struct
import json
#from ..general import bx_struct as s
import bpy


def ssx2_get_map_info(map_path):
	"""
	Returns a dictionary with all the entries in .map
	Not including file header (i.e version, compile date or project path)

	Possible entries/keys:
		MODELS, PARTICLE MODELS, PATCHES, INTERNAL INSTANCES, 
		PLAYER STARTS, PARTICLE INSTANCES, SPLINES, MATERIALS,
		LIGHTS, MATERIALS, CONTEXT BLOCKS, CAMERAS, TEXTURES, LIGHTMAPS
	Format:
		All:                         (Name, UID, Ref, HashValue)
		Internal/Particle Instances: (SCROLL)
	"""
	
	out = {}

	def convert_to_py(input_list):
		for i, item in enumerate(input_list):
			if i > 0:
				try:
					input_list[i] = int(input_list[i])
				except:
					continue
		return input_list

	with open(map_path, 'r') as f:
		current_key = None
		for i, line in enumerate(f):
			if line.startswith("###"):
				if 'BEGIN' in line:
					current_key = line.strip('### ').replace(' BEGIN\n','').replace('\n','')
					out[current_key] = []
				elif 'END' in line:
					current_key = None
			if current_key is not None and line.startswith('#') is False: # line[0] != '#'
				if line != '\n':
					if line.startswith("NO NAME"):
						line = line.replace("NO NAME", 'NONE')
					new_list = " ".join(line.split()).split(' ')
					convert_to_py(new_list)
					if len(new_list) > 0:
						out[current_key].append(new_list)
	return out


class SSX2_WorldGetData:
	def __init__(self, file_path):
		self.splines = []
		self.spline_segments = []




class SSX2_PatchMainData:
	def __init__(self):
		self.points   = []
		self.lightmap = []
		self.uvs      = []
		self.type     = []
		self.texture_id   = []
		self.showoff_only = []
		self.lightmap_uvs = []
		self.lightmap_id  = []

		self.name = "" # JSON Only
		self.texture_path = [] # JSON only

def get_patches_json(file_path):
	
	scale = bpy.context.scene.bx_WorldScale
	patches = []

	with open(file_path, 'r') as f:
		data = json.load(f)
		for patch in data["Patches"]:
			main = SSX2_PatchMainData()

			points = []
			for point in patch["Points"]:
				x, y, z = point
				points.append((x / scale, y / scale, z / scale, 1.0))

			main.points   = points
			main.lightmap = patch["LightMapPoint"]
			main.uvs    = patch["UVPoints"]
			main.type   = patch["PatchStyle"]
			main.texture_path = patch["TexturePath"]
			main.lightmap_uvs = patch["LightMapPoint"]
			main.lightmap_id  = patch["LightmapID"]
			main.showoff_only = patch["TrickOnlyPatch"] # Showoff only
			main.name = patch["PatchName"]
			patches.append(main)

	return patches

def get_patches_xbd():

	scale = bpy.context.scene.bx_WorldScale

	patches = []
	with open(file_path, 'rb') as f:
		f.seek(0x8, 0)
		num_patches = struct.unpack('i', f.read(4))[0]
		f.seek(0x50, 0)
		off_patches = struct.unpack('i', f.read(4))[0]
		f.seek(0x54, 0)
		off_raw_patches  = struct.unpack('i', f.read(4))[0]

		f.seek(off_raw_patches)
		
		for i in range(num_patches): # go through patches
			points = []
			for j in range(16): # unpack points
				x, y, z = struct.unpack('fff', f.read(12))
				f.seek(8, 1)
				points.append((x / scale, y / scale, z / scale, 1.0))
			points.append(points)

		f.seek(off_patches)
		
		for i in range(num_patches):
			lightmap = struct.unpack('ffff', f.read(16))

			for j in range(4):
				uvs.append(struct.unpack('ff', f.read(8)))
				f.seek(8, 1)

			f.seek(0x118, 1) # skip processed points temp
			"""
			points = []
			for j in range(16): # unpack points
				x, y, z = struct.unpack('fff', f.read(12))
				f.seek(4, 1)
				points.append( Vector((x / scale, y / scale, z / scale) ))
			points.append(decode_points(points))
			"""

			patch_type = struct.unpack('i', f.read(4))[0]
			f.seek(16, 1)
			unk = struct.unpack('i', f.read(4))[0]
			f.seek(0x40, 1)
			texture_id = struct.unpack('h', f.read(2))[0]
			unk1 = struct.unpack('h', f.read(2))[0]
			lightmap_id = struct.unpack('h', f.read(2))[0]
			f.seek(0x105, 1)
			showoff_only = True if struct.unpack('B', f.read(1))[0] == 128 else False
			# alternatively uint32 and >> 31
			f.seek(0x4, 1) # skip to start of next patch