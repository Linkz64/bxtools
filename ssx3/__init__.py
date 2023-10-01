import bpy
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ExportHelper

from .ssx3_model_pack import ssx3_set_mxf_data
from .ssx3_model_unpack import ssx3_get_mxf_data
from ..external.ex_utils import prop_split

import os



class SSX3_Panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category =  'SSX 3'

    @classmethod
    def poll(cls, context):
        print(context.scene.bx_GameChoice)
        return context.scene.bx_GameChoice == 'SSX3'



class SSX3_ModelPanel(SSX3_Panel):
    bl_idname = 'SSX3_PT_model'
    bl_label = 'Models'

    @classmethod
    def poll(self, context):
        return context.scene.bx_GameChoice == 'SSX3'

    def draw(self, context):
        col = self.layout.column()
        col.scale_y = 1.0

        #prop_split(col, context.scene, "bx_WorldScale", "World Scale")
        prop_split(col, context.scene, "bx_ModelScale", "Model Scale")
        prop_split(col, context.scene, "ssx3_ModelUnpackPath", "Original Model Path")


class SSX3_OP_Files_Select(bpy.types.Operator, ExportHelper): # for now I'm keeping it as a file name selector instead of full path+file
    bl_idname = "ssx3.select_files"
    bl_label = "Select File Names"
    bl_description = "Select files by file name"
    files: bpy.props.CollectionProperty( # this can be accessed with Window Manager but I went with the Scene StringProperty approach instead
            name="File Path",
            type=bpy.types.OperatorFileListElement,
            )
    directory: bpy.props.StringProperty(
            subtype='DIR_PATH',
            )
    filter_glob: bpy.props.StringProperty(
        default="*.mxf;*.mnf",
        options={'HIDDEN'}, # Hide other file extensions
        maxlen=255,  # Max name length
    )

    check_extension = True
    filename_ext = ''

    def execute(self, context):

        context.scene.ssx3_ImportModelChoices = '' # clear string property
        seperator = ', '
        
        directory = self.directory

        for i, file_elem in enumerate(self.files):
            #filepath = os.path.join(directory, file_elem.name)
            if i == len(self.files)-1:
                seperator = ''

            context.scene.ssx3_ImportModelChoices += str(file_elem.name).replace('.mxf', '').replace('.mnf', '') + seperator
        print(context.scene.ssx3_ImportModelChoices)
        if len(context.scene.ssx3_ModelUnpackPath) == 0:
            context.scene.ssx3_ModelUnpackPath = directory
        return {'FINISHED'}


class SSX3_OP_Import_Model(bpy.types.Operator):
    """Import models from .mxf or .mnf files"""
    bl_idname = "object.ssx3_import_model"
    bl_label = "Import"
    bl_options = {'UNDO'}

    def execute(self, context):

        if context.scene.bx_platformChoice == 'XBX':
            file_ext = '.mxf'
        elif context.scene.bx_platformChoice == 'NGC':
            file_ext = '.mnf'
        else:
            file_ext = 'aaaa'

        active_collec = bpy.context.collection
        importEmptyMesh = context.scene.ssx3_ImportEmptyMesh
        importFileCollections = context.scene.ssx3_ImportFileCollections
        boxesChecked = importEmptyMesh or importFileCollections


        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        
        if len(context.scene.ssx3_ModelUnpackPath) != 0:
            unpack_folder_path = context.scene.ssx3_ModelUnpackPath
        else:
            self.report({'ERROR'}, "'Original Model Path' is not set")
            return {'CANCELLED'}

        files_to_unpack = context.scene.ssx3_ImportModelChoices.replace(' ', '').split(',')
        if len(context.scene.ssx3_ImportModelChoices) != 0 and boxesChecked:

            files_to_unpack = context.scene.ssx3_ImportModelChoices.replace(' ', '').split(',')
            for file in files_to_unpack:

                models = ssx3_get_mxf_data(unpack_folder_path+file+file_ext)[0] # 0 = model headers, 1 = model data
                col_name = file.replace('_deco', '')

                if importFileCollections:
                    if bpy.data.collections.get(col_name) is None:
                        bpy.data.collections.new(col_name)

                    if col_name not in active_collec.children:
                        active_collec.children.link(bpy.data.collections.get(col_name))
                
                if importEmptyMesh:
                    for mdl in models:
                        mdl_name = mdl['modelName']
                        obj = bpy.data.objects.new(mdl_name, bpy.data.meshes.new(mdl_name))
                        if importFileCollections:
                            bpy.data.collections.get(col_name).objects.link(obj)
                        else:
                            active_collec.objects.link(obj)
            
                        obj["Skeleton ID"] = mdl['skeletonID']
        elif boxesChecked == False:
            self.report({'ERROR'}, "No boxes checked.")
            return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "No file names specified.")
            return {'CANCELLED'}

        self.report({'INFO'}, "Import finished!")
        return {'FINISHED'}


class SSX3_OP_Export_Model(bpy.types.Operator):
    """Export models to .mxf or .mnf files"""
    bl_idname = "object.ssx3_export_model"
    bl_label = "Export"

    def execute(self, context):

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        if context.scene.bx_platformChoice == 'XBX':
            export = ssx3_set_mxf_data()
        elif context.scene.bx_platformChoice == 'NGC':
            export = ssx3_set_mnf_data() # doesn't exist yet
        else:
            pass

        if export[0] == True:
            self.report({'INFO'}, export[1])
            return {'FINISHED'}
        elif export[0] == False:
            self.report({'ERROR'}, export[1])
        elif export[0] == None:
            self.report({'WARNING'}, export[1])
        else:
            # it should display and print the error anyway:
            self.report({'ERROR'}, "Unexpected error")
        print('Packing Failed')
        return {'CANCELLED'}

        



class SSX3_ImportModelPanel(SSX3_Panel): # not sure if this should be 'SSX3_Panel' or 'bpy.types.Panel'
    bl_idname = 'SSX3_PT_import_model'
    bl_label = 'Model Import'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = 'SSX3_PT_model'

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        col = self.layout.column()

        row = col.row()
        row.prop(context.scene, 'ssx3_ImportFileCollections')
        #row.prop(context.scene, 'ssx3_ImportSkeleton')
        row.prop(context.scene, 'ssx3_ImportEmptyMesh')


        col.prop(context.scene, 'ssx3_ImportModelChoices')
        col.operator('ssx3.select_files')
        col.operator('object.ssx3_import_model')



class SSX3_ExportModelPanel(SSX3_Panel):
    bl_idname = 'SSX3_PT_export_model'
    bl_label = 'Model Export'
    bl_parent_id = 'SSX3_PT_model'

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        colbox = box.column()
        colbox.label(text='Copy from Original')
        colrow = box.row()
        colrow.prop(context.scene, 'ssx3_CopyBones')
        colrow.prop(context.scene, 'ssx3_CopySkelID')

        #colrow = box.row()
        #colrow.prop(context.scene, 'ssx3_CopySkelID')

        col = layout.column()
        prop_split(col, context.scene, "ssx3_ModelPackPath", "Export Path")
        prop_split(col, context.scene, "ssx3_CustomModelCollec", "Collection")
        prop_split(col, context.scene, "ssx3_CustomModelFile", "File Prefix")
        col.operator('object.ssx3_export_model')


classes = (
    SSX3_ModelPanel, # Settings

    SSX3_OP_Files_Select,
    SSX3_ImportModelPanel, # Model Import/Export
    SSX3_OP_Import_Model,
    SSX3_OP_Export_Model,
    SSX3_ExportModelPanel,

)

def ssx3_register():

    #ssx3_model_pack_register()

    for c in classes:
        register_class(c)

    bpy.types.Scene.ssx3_ModelUnpackPath    = bpy.props.StringProperty(name="", default="", subtype='DIR_PATH', maxlen=1024,
        description="Folder that contains the original model file")
    bpy.types.Scene.ssx3_ModelPackPath      = bpy.props.StringProperty(name="", default="", subtype='DIR_PATH', maxlen=1024,
        description="Output folder")
    bpy.types.Scene.ssx3_CustomModelFile    = bpy.props.StringProperty(name="", default="board", maxlen=16,
        description="Name of the output file (e.g board or mac)")
    bpy.types.Scene.ssx3_ImportModelChoices = bpy.props.StringProperty(name="",
        description="Names of files separated by commas.\nExample:\nbrodi_Boots, brodi_HeadA\n\nRequires 'Original Model Path' to be set.")

    #bpy.types.Scene.ssx3_ImportSkeleton       = bpy.props.BoolProperty(name="Skeleton", default=True, options={'HIDDEN'})
    #bpy.types.Scene.ssx3_ImportMesh           = bpy.props.BoolProperty(name="Mesh", default=True)
    bpy.types.Scene.ssx3_ImportEmptyMesh       = bpy.props.BoolProperty(name="Empty Mesh", default=True,
        description="Import model/mesh object with no mesh data.\nOnly Skeleton ID")
    bpy.types.Scene.ssx3_ImportFileCollections = bpy.props.BoolProperty(name="Collections", default=True,
        description="Import file names and create collections in the outliner")

    bpy.types.Scene.ssx3_CustomModelCollec = bpy.props.PointerProperty(type=bpy.types.Collection)
    bpy.types.Scene.ssx3_CopyBones  = bpy.props.BoolProperty(name="Bones", default=True,
        description="Copy Bone data from original model file")
    bpy.types.Scene.ssx3_CopySkelID = bpy.props.BoolProperty(name="Skel ID", default=True, 
        description="Copy Skeleton ID from original model file")



def ssx3_unregister():

    #ssx3_model_pack_unregister()

    del bpy.types.Scene.ssx3_ModelUnpackPath
    del bpy.types.Scene.ssx3_ModelPackPath

    del bpy.types.Scene.ssx3_ImportModelChoices
    #del bpy.types.Scene.ssx3_ImportSkeleton
    #del bpy.types.Scene.ssx3_ImportMesh
    del bpy.types.Scene.ssx3_ImportEmptyMesh
    del bpy.types.Scene.ssx3_ImportFileCollections

    del bpy.types.Scene.ssx3_CustomModelCollec
    del bpy.types.Scene.ssx3_CustomModelFile
    del bpy.types.Scene.ssx3_CopyBones
    del bpy.types.Scene.ssx3_CopySkelID

    for c in classes:
        unregister_class(c)