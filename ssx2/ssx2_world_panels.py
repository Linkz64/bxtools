import bpy
from bpy.utils import register_class, unregister_class

from ..panels import SSX2_Panel
from ..external.ex_utils import prop_split
from ..general.bx_utils import *

from .ssx2_world import (
    SSX2_OP_WorldInitiateProject,
    SSX2_OP_WorldReloadNodeTrees,
    SSX2_OP_AddSplineBezier,
    SSX2_OP_AddPath,
    SSX2_OP_AddPathChild,
    SSX2_OP_PathEventAdd,
    SSX2_OP_PathEventRemove,

    SSX2_OP_WorldImport,
    SSX2_OP_WorldExport,
)

from .ssx2_world_patches import (
    SSX2_OP_AddPatch,
    SSX2_OP_AddPatch,
    SSX2_OP_AddControlGrid,
    SSX2_OP_AddSplineCage,
    SSX2_OP_AddPatchMaterial,
    SSX2_OP_AddCageVGuide,
    SSX2_OP_SendMaterialToModifier,
    SSX2_OP_ToggleControlGrid,
    SSX2_OP_CageToPatch,
    SSX2_OP_FlipSplineOrder,
    SSX2_OP_PatchSplit4x4,
    SSX2_OP_SelectSplineCageU,
    SSX2_OP_SelectSplineCageV,
    SSX2_OP_CopyPatchUVsToSelected,
)


### Main Panels

class SSX2_WorldPanel(SSX2_Panel):
    bl_idname = 'SSX2_PT_world'
    bl_label = 'Worlds'

    def draw(self, context):
        col = self.layout.column()
        col.scale_y = 1.0
        prop_split(col, context.scene, "bx_WorldScale", "World Scale")

        io = context.scene.ssx2_WorldImportExportProps
        if context.scene.bx_PlatformChoice != 'ICE':
            prop_split(col, io, 'worldChoice', "World Choice")
            if io.worldChoice == 'CUSTOM':
                prop_split(col, io, 'worldChoiceCustom', 'Custom Choice')
                
        general_row = col.row()
        general_row.operator(SSX2_OP_WorldInitiateProject.bl_idname, icon='ADD')
        general_row.operator(SSX2_OP_WorldReloadNodeTrees.bl_idname, icon='FILE_REFRESH', text="Reload Appends")
        #col.operator("script.reload", text="⟳⟳⟳⟳⟳")

        col.menu(SSX2_WorldAddMenu.bl_idname, text="Add Object")

class SSX2_WorldImportPanel(SSX2_Panel):
    bl_idname = 'SSX2_PT_world_import'
    bl_label = 'World Import'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        io = context.scene.ssx2_WorldImportExportProps
        col = self.layout.column()
        prop_split(col, io, 'importFolderPath', "Import Folder", spacing=0.4)
        
        if context.scene.bx_PlatformChoice != 'ICE':
            col_row = col.row()
            col_row.prop(io, "importNames")
            col_row.prop(io, "importTextures")

        # PATCHES
        patches_box = col.box()
        pch_col_box = patches_box.column()
        pch_header_row = pch_col_box.row(align=True)
        pch_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
            icon='DISCLOSURE_TRI_DOWN' if io.expandImportPatches\
            else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportPatches'
        pch_header_row.prop(io, "importPatches", text="Patches")
        if io.expandImportPatches:
            pch_col_box.prop(io, "patchImportAsControlGrid", text="As Control Grid")
            prop_enum_horizontal(pch_col_box, io, 'patchImportGrouping', "Grouping", spacing=0.3)
            
        # SPLINES
        splines_box = col.box()
        spl_box_col = splines_box.column()
        spl_header_row = spl_box_col.row(align=True)
        spl_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
            icon='BLANK1' if io.expandImportSplines\
            else 'BLANK1',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportSplines'
        spl_header_row.prop(io, "importSplines", text="Splines")
        # if io.expandImportSplines:
        # 	spl_box_col.prop(io, "splineImportAsNURBS", text="As NURBS")
            #prop_enum_horizontal(spl_box_col, io, 'patchImportGrouping', "Grouping", spacing=0.3)
        
        # PATHS
        paths_box = col.box()
        pth_col_box = paths_box.column()
        pth_header_row = pth_col_box.row(align=True)
        pth_header_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
            icon='DISCLOSURE_TRI_DOWN' if io.expandImportPaths\
            else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportPaths'
        pth_header_row.prop(io, "importPaths", text="Paths")
        if io.expandImportPaths:
            pth_col_box.prop(io, "importPathsAsCurve", text="As Poly Curve")

        # IMPORT BUTTON
        col.operator(SSX2_OP_WorldImport.bl_idname)

class SSX2_WorldExportPanel(SSX2_Panel):
    bl_idname = 'SSX2_PT_world_export'
    bl_label = 'World Export'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        io = context.scene.ssx2_WorldImportExportProps
        col = self.layout.column()
        prop_split(col, io, 'exportFolderPath', 'Export Folder', spacing=0.4)
        
        patches_box = col.box()
        patches_box = patches_box.row()
        patches_box_split = patches_box.split(factor=0.3)
        patches_box_split.label(text="Patches")
        patches_box_split.prop(io, "exportPatches", text="Patches")
        patches_box_split.prop(io, "exportPatchesCages", text="Cages")

        splines_box = col.box()
        splines_box = splines_box.row()
        splines_box_split = splines_box.split(factor=0.3)
        splines_box_split.label(text="Splines")
        splines_box_split.prop(io, "exportSplines", text="Splines")
        splines_box_split.prop(io, "exportSplinesOverride", text="Override")

        paths_box = col.box()
        paths_box = paths_box.row()
        paths_box_split = paths_box.split(factor=0.3)
        paths_box_split.label(text="Paths")
        paths_box_split.prop(io, "exportPathsGeneral", text="General")
        paths_box_split.prop(io, "exportPathsShowoff", text="Showoff")

        col.operator(SSX2_OP_WorldExport.bl_idname)


### SubPanels

class SSX2_WorldPatchesSubPanel(bpy.types.Panel):
    bl_idname = 'BXT_PT_world_patches_panel'
    bl_label = 'Patches'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BXTools'
    bl_parent_id = 'SSX2_PT_world'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(text="", icon='SURFACE_NSURFACE')

    def draw(self, context):
        layout = self.layout

        obj = bpy.context.active_object
        if obj is not None:
            if obj.type == 'SURFACE':
                layout.operator(SSX2_OP_ToggleControlGrid.bl_idname, text="To Control Grid")
            elif obj.ssx2_PatchProps.isControlGrid:
                layout.operator(SSX2_OP_ToggleControlGrid.bl_idname, text="To Patch")
            else:
                layout.operator(SSX2_OP_ToggleControlGrid.bl_idname)
        else:
            layout.operator(SSX2_OP_ToggleControlGrid.bl_idname)

        layout.operator(SSX2_OP_PatchSplit4x4.bl_idname, text="Split to 4x4")
        layout.operator(SSX2_OP_CopyPatchUVsToSelected.bl_idname)

        #layout.label(text="Spline Cage")
        layout.separator()
        layout = layout
        layout.operator(SSX2_OP_CageToPatch.bl_idname, text="Patch from Cage")
        row2 = layout.row()
        row2.operator(SSX2_OP_FlipSplineOrder.bl_idname, text="Flip Spline Order")
        row2.operator("curve.switch_direction", text="Flip Point Order")
        row3 = layout.row()
        row3.operator(SSX2_OP_SelectSplineCageU.bl_idname, text="Select U")
        row3.operator(SSX2_OP_SelectSplineCageV.bl_idname, text="Select V")
        layout.operator(SSX2_OP_AddCageVGuide.bl_idname, text="Add V Guide", icon='ADD')
        
        #layout.label(text="Other")
        layout.separator()
        prop_split(layout, context.scene.ssx2_WorldUIProps, 'patchSelectByType', "Select by Type")

class SSX2_WorldSplinesSubPanel(bpy.types.Panel):
    bl_idname = 'BXT_PT_world_splines_panel'
    bl_label = 'Splines'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BXTools'
    bl_parent_id = 'SSX2_PT_world'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(text="", icon='CURVE_BEZCURVE')

    def draw(self, context):
        row = self.layout.row()
        #row.operator(SSX2_OP_AddSplineNURBS.bl_idname, icon='ADD')
        row.operator(SSX2_OP_AddSplineBezier.bl_idname, icon='ADD', text="Add Bezier Curve")

class SSX2_WorldPathsSubPanel(bpy.types.Panel):
    bl_idname = 'BXT_PT_world_paths_panel'
    bl_label = 'Paths'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BXTools'
    bl_parent_id = 'SSX2_PT_world'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(text="", icon='TRACKING')

    def draw(self, context):
        row = self.layout.row()
        row.operator(SSX2_OP_AddPath.bl_idname, icon='ADD')

        obj = bpy.context.active_object
        if obj:
            if obj.type == 'EMPTY': #if obj.ssx2_EmptyMode == 'PATH_AI':
                row.operator(SSX2_OP_AddPathChild.bl_idname, icon='ADD', text="Path Child")


### Properties

class SSX2_EmptyPropPanel(SSX2_Panel):
    bl_label = "BX Empty"
    bl_idname = "OBJECT_PT_SSX2_Empty"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return \
        context.scene.bx_GameChoice == 'SSX2' and \
        (context.object is not None) and \
        context.object.type == 'EMPTY'

    def draw(self, context):
        obj = context.object
        layout = self.layout#.column()
        prop_split(layout, obj, "ssx2_EmptyMode", "Empty Mode")

        empty_mode = obj.ssx2_EmptyMode

        if empty_mode == "PATH_AI" or empty_mode == "PATH_EVENT":
            path_props = obj.ssx2_PathProps
            events = path_props.events

            if empty_mode == "PATH_AI":
                layout.prop(path_props, "reset", text="Reset Target")
                layout.prop(path_props, "start", text="Start Point")
                prop_split(layout, path_props, "aipaths_u3", "Unknown 3")
            else:
                prop_split(layout, path_props, "eventpaths_u2", "Unknown 2")


            # layout.label(text="Path Mode: [Enum]")

            events_box = layout.box()
            evt_box_header = events_box.row(align=True)

            evt_box_header.label(text="Events")
            evt_box_header.operator(SSX2_OP_PathEventAdd.bl_idname, text="Add", icon="ADD")
            evt_box_header.operator(SSX2_OP_PathEventRemove.bl_idname, text="Remove", icon="REMOVE")

            for event in events:
                row = events_box.row(align=True)
                evt_header_row = row

                evt_header_row.prop(event, "checked") #text=event.name)

                split1 = evt_header_row.split(align=True, factor=0.45)
                split_name_ints = split1.split(align=True, factor=0.42)
                #split_name_ints.prop(event, "name", text="") # event.name

                #evt_ints = split_name_ints.row(align=True)
                split_name_ints.prop(event, "u0", text="")
                split_name_ints.prop(event, "u1", text="")

                evt_floats = split1.row(align=True)
                evt_floats.prop(event, "u2", text="")
                evt_floats.prop(event, "u3", text="")


        elif empty_mode == "INSTANCE":
            col = self.layout.column()
            prop_split(col, context.object, 'ssx2_ModelForInstance', "Model")
            row = col.row()
            row.prop(context.object, 'show_instancer_for_viewport', text='Show Instancer')
            row.prop(context.object, 'show_in_front')#, text='Show in Front')

class SSX2_CurvePropPanel(SSX2_Panel):
    bl_label = "BX Spline Curve"
    bl_idname = "OBJECT_PT_SSX2_Spline_Curve"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return context.scene.bx_GameChoice == 'SSX2' and \
        (context.object is not None) # and context.object.type == 'SURFACE')
        # context.ssx2_SplineProps.isControlGrid # this doesn't work

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj.type == 'CURVE':
            prop_split(layout, obj, "ssx2_CurveMode", "Curve Mode")

            if obj.ssx2_CurveMode == 'SPLINE':
                prop_split(layout, obj.ssx2_SplineProps, 'type', "Spline Type")

            elif obj.ssx2_CurveMode == 'PATH_AI' or obj.ssx2_CurveMode == 'PATH_EVENT':
                path_props = obj.ssx2_PathProps
                events = path_props.events

                if obj.ssx2_CurveMode == 'PATH_AI':
                    layout.prop(path_props, "reset", text="Reset Target")
                    layout.prop(path_props, "start", text="Start Point")
                    prop_split(layout, path_props, "aipaths_u3", "Unknown 3")
                else:
                    prop_split(layout, path_props, "eventpaths_u2", "Unknown 2")


                # layout.label(text="Path Mode: [Enum]")

                events_box = layout.box()
                evt_box_header = events_box.row(align=True)

                evt_box_header.label(text="Events")
                evt_box_header.operator(SSX2_OP_PathEventAdd.bl_idname, text="Add", icon="ADD")
                evt_box_header.operator(SSX2_OP_PathEventRemove.bl_idname, text="Remove", icon="REMOVE")

                for event in events:
                    row = events_box.row(align=True)
                    evt_header_row = row

                    evt_header_row.prop(event, "checked") #text=event.name)

                    split1 = evt_header_row.split(align=True, factor=0.45)
                    split_name_ints = split1.split(align=True, factor=0.42)

                    #split_name_ints.prop(event, "name", text="") # event.name

                    #evt_ints = split_name_ints.row(align=True)
                    split_name_ints.prop(event, "u0", text="")
                    split_name_ints.prop(event, "u1", text="")

                    evt_floats = split1.row(align=True)
                    evt_floats.prop(event, "u2", text="")
                    evt_floats.prop(event, "u3", text="")

class SSX2_MaterialPropPanel(SSX2_Panel):
    bl_label = "Test"
    bl_idname = "MATERIAL_PT_SSX2_material"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_options = {"HIDE_HEADER"}
    
    def draw(self, context):
        obj = context.object

        layout = self.layout
        row = layout.row()
        row.operator(SSX2_OP_AddPatchMaterial.bl_idname, text="New Patch Material", icon='ADD')

        if obj is not None:
            if obj.ssx2_CurveMode == 'CAGE':
                row.operator(SSX2_OP_SendMaterialToModifier.bl_idname, text="Send to Modifier")


### Menus

class SSX2_WorldAddMenu(bpy.types.Menu):
    bl_label = "BXTools"
    bl_idname = "SSX2_MT_add"

    def draw(self, context):
        layout = self.layout
        
        #layout.label(text="Patches")
        #layout.separator()
        layout.operator(SSX2_OP_AddPatch.bl_idname, icon='SURFACE_NSURFACE')
        layout.operator(SSX2_OP_AddControlGrid.bl_idname, icon='MESH_GRID')
        layout.operator(SSX2_OP_AddSplineCage.bl_idname, icon='SURFACE_DATA')
        layout.separator()
        layout.operator(SSX2_OP_AddSplineBezier.bl_idname, icon='CURVE_BEZCURVE')
        layout.separator()
        layout.operator(SSX2_OP_AddPath.bl_idname, icon='TRACKING', text="Path")


### Operators

class SSX2_OP_WorldExpandUIBoxes(bpy.types.Operator):
    bl_idname = "wm.ssx2_expand_ui_boxes"
    bl_label = ""
    bl_description = "Expand box"
    #bl_options = {'REGISTER'}#, 'UNDO'}

    prop: bpy.props.StringProperty()

    def execute(self, context):
        props_split = self.prop.split('.')
        props = getattr(bpy.context.scene, props_split[0])
        setattr(props, props_split[1], not getattr(props, props_split[1]))
        return {'FINISHED'}


### Functions

def menu_func(self, context):
    self.layout.menu(SSX2_WorldAddMenu.bl_idname)


classes = (
    SSX2_WorldPanel,
    SSX2_WorldPatchesSubPanel,
    SSX2_WorldSplinesSubPanel,
    SSX2_WorldPathsSubPanel,
    SSX2_WorldImportPanel,
    SSX2_WorldExportPanel,
    
    SSX2_EmptyPropPanel,
    SSX2_CurvePropPanel,
    SSX2_MaterialPropPanel,

    SSX2_WorldAddMenu,

    SSX2_OP_WorldExpandUIBoxes,
)


def ssx2_world_panels_register():
    for c in classes:
        register_class(c)
    bpy.types.VIEW3D_MT_add.append(menu_func)
        

def ssx2_world_panels_unregister():
    bpy.types.VIEW3D_MT_add.remove(menu_func)
    for c in classes:
        unregister_class(c)