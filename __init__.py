print("\n\nBXTools Plugin Initiating\n")

"""
Force reload other local modules when plugin is toggled or when "Reload Scripts" is pressed.
This is done because Blender only reloads the main __init__.py (this one)
Note: lines in *_register() functions do not get reloaded.
"""

import os
import sys
import time
import requests
import importlib
import functools
import zipfile
import shutil

import addon_utils


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

bxt_update_last_press_time = 0


def install_and_reload(output_path):
    try:
        bpy.ops.preferences.addon_install(filepath=output_path[0], overwrite=True)
        bpy.ops.script.reload()
    except Exception as e:
        print(e)

def zip_directory(folder_path, zip_path):
    folder_path = os.path.abspath(folder_path)
    root_folder_name = os.path.basename(folder_path)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join(root_folder_name, os.path.relpath(file_path, folder_path))
                zipf.write(file_path, arcname)

    print(f"BXT Zipped '{folder_path}' to '{zip_path}' with root folder '{root_folder_name}'")




### Operators

class BXT_OP_Update(bpy.types.Operator):
    bl_idname = 'preferences.bxtools_update'
    bl_label = "Update"
    bl_description = "Updates the addon"

    def execute(self, context):
        global bxt_update_last_press_time
        current_time = time.time()

        print("\n\n\n")
        seconds_difference = current_time - bxt_update_last_press_time
        print(seconds_difference)

        if seconds_difference <= 10:
            self.report({'WARNING'}, f"Wait {round(10 - seconds_difference, 2)} seconds before trying again.")
            return {"CANCELLED"}
        bxt_update_last_press_time = time.time()
        # ^ does this even work after update?
        #
        #
        #
        #
        #
        #
        
        bxt_name = bl_info.get("name")
        for mod in addon_utils.modules():
            name = mod.bl_info.get("name")
            if name == bxt_name:
                bxt_folder_path = os.path.split(mod.__file__)[0]
                break

        blender_scripts_dir = bpy.utils.user_resource('SCRIPTS')
        blender_addons_dir, bxt_folder_name = os.path.split(bxt_folder_path)

        
        # print(bxt_folder_name)

        url = "https://github.com/Linkz64/bxtools/archive/refs/heads/main.zip"
        output_path = os.path.join(blender_scripts_dir, bxt_folder_name)
        output_path += ".zip"

        response = requests.get(url, stream=True)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Downloaded zip file. Path:\n{output_path}\n")
        else:
            print(f"Failed to download zip file. Status code: {response.status_code}")
            self.report({'ERROR'}, f"Failed to download zip file. See info window. {response.status_code}")
            return {"CANCELLED"}


        with zipfile.ZipFile(output_path, 'r') as zip_ref:
            main_zip_content = zip_ref.namelist()[0]
            main_zip_content = main_zip_content.replace('/', '')

            if main_zip_content != bxt_folder_name:
                zip_ref.extractall(blender_scripts_dir)
                
        if main_zip_content != bxt_folder_name:
            # os.remove(output_path)
            new_temp_folder = os.path.join(blender_scripts_dir, bxt_folder_name)

            os.rename(
                os.path.join(blender_scripts_dir, main_zip_content),
                new_temp_folder
            )

            print(new_temp_folder)
            
            zip_directory(new_temp_folder, output_path)

        shutil.rmtree(new_temp_folder)

        bpy.app.timers.register(functools.partial(install_and_reload, [output_path]), first_interval=0.5)
        return {"FINISHED"}




### Panels

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
        col.operator(BXT_OP_Update.bl_idname, icon='IMPORT')
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
    BXT_OP_Update,

    BXT_Panel,
    BXT_PanelInProperties
)






addon_keymaps = []

def register_keymaps():
    wm = bpy.context.window_manager

    km = wm.keyconfigs.addon.keymaps.new(name="Curve", space_type="EMPTY")
    kmi = km.keymap_items.new("curve.select_spline_cage_along_u", 'E', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

    print("BXT Keymap 'Select Along U' added to 'Keymap > 3D View > Curve > Curve (Global)'")


    km = wm.keyconfigs.addon.keymaps.new(name="Curve", space_type="EMPTY")
    kmi = km.keymap_items.new("curve.select_spline_cage_along_v", 'R', 'PRESS', ctrl=True, shift=True)
    # kmi.properties.operator = "Translate"
    addon_keymaps.append((km, kmi))

    print("BXT Keymap 'Select Along V' added to 'Keymap > 3D View > Curve > Curve (Global)'")

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