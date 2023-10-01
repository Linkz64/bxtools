#import bpy

pie = 3.14159265359
sli = 1.570796326795

"""
self.report types
	'DEBUG'
	'INFO'
	'OPERATOR'
	'PROPERTY'
	'WARNING'
	'ERROR'
	'ERROR_INVALID_INPUT'
	'ERROR_INVALID_CONTEXT'
	'ERROR_OUT_OF_MEMORY'
"""


## WORLDS

enum_ssx2_world_project_mode = (
	('BINARY', "Binary", "Original game files"),
	('JSON',   "JSON",   "IceSaw project files"),
)

enum_ssx2_world = ( # alphabetical order
	('CUSTOM',  "Custom",                 ""),
	('alaska',  "Alaska",                 ""),
	('aloha',   "Aloha",                  ""),
	('elysium', "Elysium Alps",           ""),
	('gari',    "Garibaldi",              ""),
	('megaple', "Tokyo Megaplex",         ""),
	('merquer', "Merquery City Meltdown", ""),
	('mesa',    "Mesablanca",             ""),
	('pipe',    "Pipedream",              ""),
	('snow',    "Snowdream",              ""),
	('ssxfe',   "SSX Front End (Menu)",   ""),
	('trick',   "Trick Tutorial",         ""),
	('untrack', "Untracked",              ""),
)

enum_ssx2_surface_type = ( # ? = to be checked # used by patches and splines
	('0', "Reset",             "Resets the player position back to the nearest path point", 'FILE_REFRESH',           0),
	('1', "Snow Main",         "Track Snow",                                                'FREEZE',                 1),
	('2', "Snow Side",         "Snow Particles",                                            'FREEZE',                 2), # very faint sound, mainly on entry. i think
	('3', "Snow Powder",       "Many Snow Particles, Player Sinks Slightly",                'VOLUME_DATA',            3),
	('4', "Snow Powder Heavy", "Many Snow Particles, Player Sinks, Speed Decrease",         'OUTLINER_OB_VOLUME',     4), #BOIDS
	('5', "Ice",               "Speed Increase, Slippery",                                  'META_CUBE',              5),
	('6', "Rebound",           "Unrideable. Causes the player to bounce off",               'INDIRECT_ONLY_ON',       6),
	('7', "Ice/Water",         "No Trail",                                                  'MOD_FLUIDSIM',           7), # MOD_FLUIDSIM MOD_OCEAN
	('8', "Snow 5",            "Many Snow Particles",                                       'FREEZE',                 8),
	('9', "Rock",              "Speed Decrease, Spark Particles. Rock Grinding Sounds",     'RNDCURVE',               9),
	('10', "Rebound Rock",     "Unrideable. Causes the player to bounce off",               'INDIRECT_ONLY_ON',       10),
	('11', "Unknown",          "No Trail, Ice Scraping Sound",                              'QUESTION',               11), # ?
	('12', "Wood",             "No Trail, Wood Sounds?",                                    'SEQ_STRIP_DUPLICATE',    12),
	('13', "Metal",            "Slippery, Speed Decrease, Metal Sounds, Spark Particles",   'OUTLINER_OB_LIGHTPROBE', 13),
	('14', "Unknown 2",        "No Trail, Speed Increase, Scraping Sound",                  'QUESTION',               14),
	('15', "Snow 6",           "Like standard snow?",                                       'FREEZE',                 15),
	('16', "Sand",             "Standard Sand",                                             'SPHERECURVE',            16),
	('17', "No Collision",     "Player passes through",                                     'GIZMO',                  17), # GIZMO GHOST_ENABLED # ghost confuses with invis
	('18', "Metal/Ramp",       "Metal Sounds",                                              'OUTLINER_OB_LIGHTPROBE', 18),
	('19', "Metal/Ramp 2",     "Metal Sounds",                                              'OUTLINER_OB_LIGHTPROBE', 19),
)
enum_ssx2_surface_type_spline = enum_ssx2_surface_type + (\
	('-1', "[None]",           "None", 'X', -1), ) # BLANK1

# enum_ssx2_surface_type_extended = (
# 	('50', "[BEZIER PATCH]","NURBS/Bézier patch", 'SURFACE_NSURFACE', 50), \
# 	('51', "[CONTROL GRID]","Control Grid", 'MESH_GRID',        51)
# 	)  # MESH_GRID GRID LIGHTPROBE_GRID

enum_ssx2_surface_type_extended = enum_ssx2_surface_type + (\
	('50', "[BEZIER PATCH]","NURBS/Bézier patch", 'SURFACE_NSURFACE', 50), \
	('51', "[CONTROL GRID]","Control Grid", 'MESH_GRID',        51), )  # MESH_GRID GRID LIGHTPROBE_GRID
	# for selecting by type # Icould give these custom enum id but whatever

enum_ssx2_patch_group = (
	('NONE', "None", "No grouping"),
	('TYPE', "Type", "Group into collections by type"),
	('BATCH', "Batch", "Group into collections by a set amount"),
	#('MATERIAL', "Material", "Group into collections by material")
)

enum_ssx2_patch_uv_preset = ( # I can use bool instead and an update function (if x and y: map=(3.14, 0, 0))
	('0', "Flip Y"           , "Flip Y"           ), # these don't follow patch_tex_maps
	('7', "Flip X"           , "Flip X"           ),
	('1', "Rot 180"          , "Rot 180"          ),
	('2', "Default"          , "Default"          ), # Y+ ?
	('3', "Rot Left"         , "Rot Left"         ),
	('4', "Rot Right"        , "Rot Right"        ),
	('5', "Rot Right, Flip X", "Rot Right, Flip X"),
	('6', "Rot Right, Flip Y", "Rot Right, Flip Y"),
)

patch_known_uvs = (
	[( 1.0,  0.0), ( 1.0, -1.0), (1.0,  0.0), ( 1.0, -1.0)], # 0
	[( 0.0, -1.0), ( 0.0,  0.0), (1.0, -1.0), ( 1.0,  0.0)], # 1
	[( 1.0,  0.0), ( 1.0, -1.0), (0.0,  0.0), ( 0.0, -1.0)], # 2
	[( 0.0,  0.0), ( 1.0,  0.0), (0.0, -1.0), ( 1.0, -1.0)], # 3
	[( 1.0,  0.0), ( 1.0, -1.0), (2.0,  0.0), ( 2.0, -1.0)], # 0 # above 1.99
	[( 1.0, -1.0), ( 0.0, -1.0), (1.0,  0.0), ( 0.0,  0.0)], # 4
	[( 0.0,  0.0), ( 1.0,  0.0), (0.0,  1.0), ( 1.0,  1.0)], # 5
	[( 0.0, -1.0), ( 1.0, -1.0), (0.0, -2.0), ( 1.0, -2.0)], # 3
	[( 0.0,  0.0), ( 2.0,  0.0), (0.0, -2.0), ( 2.0, -2.0)], # 6
	[( 0.0,  0.0), (-1.0,  0.0), (0.0, -1.0), (-1.0, -1.0)], # 6
	[( 0.0,  0.0), (-1.0,  0.0), (0.0,  1.0), (-1.0,  1.0)], # 4
	[( 0.0,  0.0), ( 0.0, -1.0), (1.0,  0.0), ( 1.0, -1.0)], # not from world import
	[( 0.0,  0.0), ( 0.0,  1.0), (1.0,  0.0), ( 1.0,  1.0)], # not from world import
)
patch_tex_maps = ( # maybe return the values in the func instead of having this list
	(0.0, 0.0, 0.0),
	(pie, 0.0, 0.0),
	(0.0, pie, 0.0), # Y+ ?
	(pie, 0.0, sli),
	(0.0, pie, sli), # (pie, 0.0, -sli)
	(pie, pie, sli),
	(0.0, 0.0, sli),
	(pie, pie, 0.0)
)
patch_uv_equiv_tex_maps = [0, 1, 2, 3, 0, 4, 5, 3, 6, 6, 4]
patch_tex_map_equiv_uvs = [0, 1, 2, 3, 5, 6, 8]

indices_for_control_grid = [ # 4x4 grid (3x3 faces)
	(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3),
	(4, 8, 9, 5), (5, 9, 10, 6), (6, 10, 11, 7),
	(8, 12, 13, 9), (9, 13, 14, 10), (10, 14, 15, 11),
]