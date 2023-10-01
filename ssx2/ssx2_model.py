import bpy
from bpy.utils import register_class, unregister_class

from .ssx2_model_pack import ssx2_set_mxf_data
from ..panels import SSX2_Panel
from ..external.ex_utils import prop_split
from ..general.bx_utils import getset_instance_collection

from ..general import blender_get_data


## Operators

class SSX2_OP_Export_Model(bpy.types.Operator):
    """Export models to .mxf or .mnf files"""
    bl_idname = "object.ssx2_export_model"
    bl_label = "Export"

    def execute(self, context):

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        if bpy.types.Scene.ssx2_CopyBones and len(context.scene.ssx2_ModelUnpackPath) == 0:
            self.report({'ERROR'}, "'Original Model Path' is not set")
            return {'CANCELLED'}

        export = ssx2_set_mxf_data()
        if export[0] == True:
            self.report({'INFO'}, export[1])
            return {'FINISHED'}
        elif export[0] == False:
            self.report({'ERROR'}, export[1])
        elif export[0] == None:
            self.report({'WARNING'}, export[1])
        else:# it should display and print the error anyway:
            self.report({'ERROR'}, "Unexpected error")
        print('Packing Failed')
        return {'CANCELLED'}

class SSX2_OP_Test(bpy.types.Operator):
    bl_idname = "object.ssx2_test"
    bl_label = "Test"

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        a = blender_get_data.get_shape_keys(bpy.context.active_object)
        print('Finished', a)
        self.report({'INFO'}, "Test finished!")
        return {'FINISHED'}


## Panels

class SSX2_ModelPanel(SSX2_Panel):
    bl_idname = 'SSX2_PT_model'
    bl_label = 'Models'
    #bl_category =  'SSX 3'
    #bl_space_type = 'VIEW_3D'
    #bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.bx_GameChoice == 'SSX2' and context.scene.bx_PlatformChoice == 'XBX'

    def draw(self, context):
        col = self.layout.column()
        col.scale_y = 1.0

        prop_split(col, context.scene, "bx_ModelScale", "Model Scale")
        prop_split(col, context.scene, "ssx2_ModelUnpackPath", "Original Model Path", spacing=0.4)
        col.operator('object.ssx2_test')


class SSX2_ExportModelPanel(SSX2_Panel):
    bl_idname = 'SSX2_PT_export_model'
    bl_label = 'Model Export'
    #bl_category =  'SSX Tricky'
    #bl_space_type = 'VIEW_3D'
    #bl_region_type = 'UI'
    bl_parent_id = 'SSX2_PT_model'

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        col = self.layout.column()

        box = col.box()
        colbox = box.column()
        colbox.label(text='Copy from Original')
        colrow = box.row()
        colrow.prop(context.scene, 'ssx2_CopyBones')
        #colrow.prop(context.scene, 'ssx2_CopySkelID')
        colrow.prop(context.scene, 'ssx2_OverrideBoneLoc')

        prop_split(col, context.scene, "ssx2_ModelPackPath",     "Export Path", spacing=0.4)
        prop_split(col, context.scene, "ssx2_CustomModelCollec", "Collection")
        prop_split(col, context.scene, "ssx2_CustomModelFile",   "File Prefix")
        col.operator('object.ssx2_export_model')


def update_bone_override(self, context):
    if self.ssx2_CopyBones == False and self.ssx2_OverrideBoneLoc == True:
        self.ssx2_OverrideBoneLoc = False

classes = (
    SSX2_OP_Export_Model,
    SSX2_OP_Test,

    SSX2_ModelPanel,
    #SSX2_ImportModelPanel,
    SSX2_ExportModelPanel,
)

def ssx2_model_register():

    for c in classes:
        register_class(c)

    bpy.types.Scene.ssx2_ModelUnpackPath = bpy.props.StringProperty(name="", default="", maxlen=1024, subtype='DIR_PATH',
        description="Folder that contains the original model file")
    bpy.types.Scene.ssx2_ModelPackPath   = bpy.props.StringProperty(name="", default="", maxlen=1024, subtype='DIR_PATH',
        description="Output folder")
    bpy.types.Scene.ssx2_CustomModelFile   = bpy.props.StringProperty(name="", default="board", maxlen=16, subtype='NONE',
        description="Name of the output file (e.g board or marisol)")
    bpy.types.Scene.ssx2_CustomModelCollec = bpy.props.PointerProperty(type=bpy.types.Collection)

    bpy.types.Scene.ssx2_CopyBones  = bpy.props.BoolProperty(name="Bones", default=True, update=update_bone_override,
        description="Copy Bone data from original model file")
    # bpy.types.Scene.ssx2_CopySkelID = bpy.props.BoolProperty(name="Skel ID", default=True, 
    #     description="Copy Skeleton ID from original model file")
    bpy.types.Scene.ssx2_OverrideBoneLoc = bpy.props.BoolProperty(name="Override Loc", default=False, update=update_bone_override,
        description="Override the copied bone location with your custom bone location.")

def ssx2_model_unregister():

    del bpy.types.Scene.ssx2_ModelUnpackPath
    del bpy.types.Scene.ssx2_ModelPackPath
    del bpy.types.Scene.ssx2_CustomModelFile
    del bpy.types.Scene.ssx2_CustomModelCollec
    del bpy.types.Scene.ssx2_CopyBones
    #del bpy.types.Scene.ssx2_CopySkelID
    del bpy.types.Scene.ssx2_OverrideBoneLoc

    for c in classes:
        unregister_class(c)