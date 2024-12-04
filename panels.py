import bpy

class SSX2_Panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category =  "BXTools"

    @classmethod
    def poll(cls, context):
        return context.scene.bx_GameChoice == 'SSX2'