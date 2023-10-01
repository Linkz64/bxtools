import bpy

class SSX2_Panel(bpy.types.Panel):
    #bl_idname = 'SSX2_PT_main' # not required
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category =  "BXT SSX"#'SSX Tricky'
    #bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        # whether or not this panel is enabled (this doesn't work here idk why)
        return context.scene.bx_GameChoice == 'SSX2'