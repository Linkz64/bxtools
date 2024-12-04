print("\n\nBXTools Plugin Initiating\n")

"""
Force reload other local modules when plugin is toggled or when "Reload Scripts" is pressed.
This is done because Blender only reloads the main __init__.py (this one)
Note: lines in *_register() functions do not get reloaded.
"""

import sys
import importlib

module_names = ( # for reloading
    'general.blender_get_data',
    'general.blender_set_data',
    'general.bx_utils',

    'ssx2.__init__',
    'ssx2.ssx2_world',
    'ssx2.ssx2_world_io_in',
    'ssx2.ssx2_world_patches',
    'ssx2.ssx2_world_panels',
    'ssx2.ssx2_constants',
)

if 'bpy' in locals():
    print("BXTools Reloading:")

    for name in module_names:
        full_name = (f"{__name__}.{name}")
        importlib.reload(sys.modules[full_name])
        print(f"    {full_name}")

else:
    import bpy
    from bpy.utils import register_class, unregister_class

    from .ssx2 import ssx2_register, ssx2_unregister
    from .ssx3 import ssx3_register, ssx3_unregister
    from .external.ex_utils import prop_split
    from .panels import *
    #from .general.bx_utils import BXT

    for name in module_names: # for reload
        full_name = (f"{__name__}.{name}")
        locals()[full_name] = importlib.import_module(full_name) # or globals()

    from .ssx2.ssx2_world_lightmaps import SSX2_OP_BakeTest

bl_info = {
    'name': 'BXTools',
    'blender': (3, 6, 0), # minimum version
    "category": "Import-Export",
    'author': 'Linkz64',
    'description': 'Plugin for importing and exporting SSX game data',
}

enum_game = (
    # ('SSX1', "SSX OG", "SSX (2000)"),
    ('SSX2', "SSX Tricky", "SSX Tricky (2001)"),
    # ('SSX3', "SSX 3", "SSX 3 (2003)"),
)

enum_platform = (
    # ('PS2', "PS2", "Sony PlayStation 2"),
    ('XBX', "Xbox", "Microsoft Xbox"),
    # ('NGC', "GameCube", "Nintendo GameCube"),
    ('ICE', "JSON", "GlitcherOG's Level files"), # Level only
)


class BXT_Panel(bpy.types.Panel):
    bl_idname = 'BXT_PT_main'
    bl_label = 'BXTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BXTools'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context): 
        col = self.layout.column()
        col.scale_y = 1.1
        prop_split(col, context.scene, 'bx_GameChoice', "Game")
        prop_split(col, context.scene, 'bx_PlatformChoice', "Platform")
        extras_box = col.box()
        extras_box.label(text="Extras")
        extras_box.operator(SSX2_OP_BakeTest.bl_idname, text="Lightmap Bake Test")

class BXT_PanelInProperties(bpy.types.Panel):
    bl_label = "BXTools"
    bl_idname = "SCENE_PT_BXT_panel_in_properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        col = self.layout.column()
        #context.active_object
        col.scale_y = 1.0
        #col.label(text='BXTools') #,icon='SOLO_ON')MODIFIER_ON
        prop_split(col, context.scene, 'bx_GameChoice', "Game")
        prop_split(col, context.scene, 'bx_PlatformChoice', "Mode")#"Platform")


def update_choice(self, context):
    global enum_platform
    game = self.bx_GameChoice
    plat = self.bx_PlatformChoice
    """
    if game == "SSX1" and plat != "PS2":
        #self.bx_PlatformChoice = "PS2"
        self.bx_GameChoice = "SSX2"
        #BXT.popup("Not available")
    # elif game == "SSX2" and (plat != "XBX" and plat != 'NGC'):
    #     self.bx_PlatformChoice = "XBX"
    elif game == "SSX3":# and plat != "XBX":
        #self.bx_PlatformChoice = "XBX"
        self.bx_GameChoice = "SSX2"
        #BXT.popup("Not available")
    """

classes = (
    BXT_Panel,
    BXT_PanelInProperties
)






addon_keymaps = []

def register_keymaps():
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name="Curve", space_type="EMPTY")

    kmi = km.keymap_items.new("curve.select_spline_cage_along_v", 'R', 'PRESS', ctrl=True, shift=True)
    # kmi.properties.operator = "Translate"
    addon_keymaps.append((km, kmi))

    print("BXT Keymap 'Select Along V' added to 'Keymap > 3D View > Curve (Global)'")

def unregister_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)

    addon_keymaps.clear()


def register():
    ssx2_register()
    ssx3_register()

    for c in classes:
        register_class(c)

    bpy.types.Scene.bx_GameChoice     = bpy.props.EnumProperty(name=    'Game', default='SSX2', items=enum_game, update=update_choice)
    bpy.types.Scene.bx_PlatformChoice = bpy.props.EnumProperty(name='Platform', default='ICE', items=enum_platform, update=update_choice)

    # soft min/max allows the user to input custom manual scale
    bpy.types.Scene.bx_WorldScale = bpy.props.FloatProperty(name="World Scale", default=100.0, soft_min=1.0, soft_max=1000.0,
        description="World Scale\nDefault: 100.0")
    bpy.types.Scene.bx_ModelScale = bpy.props.FloatProperty(name="Model Scale", default=100.0, soft_min=1.0, soft_max=1000.0,
        description="Model Scale\nDefault: 100.0")

    register_keymaps()

def unregister():
    ssx2_unregister()
    ssx3_unregister()

    del bpy.types.Scene.bx_GameChoice
    del bpy.types.Scene.bx_PlatformChoice

    del bpy.types.Scene.bx_WorldScale
    del bpy.types.Scene.bx_ModelScale

    unregister_keymaps()

    for c in classes:
        unregister_class(c)

print("\nBXTools Done Inititaing")