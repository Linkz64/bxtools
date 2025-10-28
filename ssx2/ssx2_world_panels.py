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

	SSX2_OP_SelectModel,
	SSX2_OP_ChooseMultitoolExe,
)

from .ssx2_world_patches import (
	SSX2_OP_AddPatch,
	SSX2_OP_AddPatch,
	SSX2_OP_AddControlGrid,
	SSX2_OP_AddSplineCage,
	SSX2_OP_AddPatchMaterial,
	SSX2_OP_AddCageVGuide,
	SSX2_OP_SendMaterialToModifier,
	SSX2_OP_Patch_Slide_V,
	SSX2_OP_ToggleControlGrid,
	SSX2_OP_CageToPatch,
	SSX2_OP_FlipSplineOrder,
	SSX2_OP_PatchSplit4x4,
	SSX2_OP_SelectSplineCageU,
	SSX2_OP_SelectSplineCageV,
	SSX2_OP_CopyPatchUVsToSelected,
	SSX2_OP_CopyMaterialToSelected,
	SSX2_OP_PatchUVEditor,
	SSX2_OP_PatchUVTransform,
	SSX2_OP_MergePatches,
)


### Main Panels

class SSX2_WorldPanel(SSX2_Panel):
	bl_idname = 'SSX2_PT_world'
	bl_label = 'Worlds'

	def draw(self, context):
		col = self.layout.column()
		col.scale_y = 1.0
		#prop_split(col, context.scene, "bx_WorldScale", "World Scale")

		io = context.scene.ssx2_WorldImportExportProps
		if context.scene.bx_PlatformChoice != 'ICE':
			prop_split(col, io, 'worldChoice', "World Choice")
			if io.worldChoice == 'CUSTOM':
				prop_split(col, io, 'worldChoiceCustom', 'Custom Choice')
				
		general_row = col.row(align=True)
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
		the_box = col.box()
		box_col = the_box.column()
		box_col_row = box_col.row(align=True)
		box_col_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if io.expandImportPatches\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportPatches'
		box_col_row.prop(io, "importPatches", text="Patches")
		if io.expandImportPatches:
			box_col.prop(io, "patchImportAsControlGrid", text="As Control Grid")
			prop_enum_horizontal(box_col, io, 'patchImportGrouping', "Grouping", spacing=0.3)
			
		# SPLINES
		the_box = col.box()
		box_col = the_box.column()
		box_col_row = box_col.row(align=True)
		box_col_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='BLANK1' if io.expandImportSplines\
			else 'BLANK1',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportSplines'
		box_col_row.prop(io, "importSplines", text="Splines")
		# if io.expandImportSplines:
		# 	box_col.prop(io, "splineImportAsNURBS", text="As NURBS")
			#prop_enum_horizontal(box_col, io, 'patchImportGrouping', "Grouping", spacing=0.3)
		
		# PATHS
		the_box = col.box()
		box_col = the_box.column()
		box_col_row = box_col.row(align=True)
		box_col_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if io.expandImportPaths\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportPaths'
		box_col_row.prop(io, "importPaths", text="Paths")
		if io.expandImportPaths:
			box_col.prop(io, "importPathsAsCurve", text="As Poly Curve")

		# MODELS
		the_box = col.box()
		box_row = the_box.row(align=True)
		box_row.operator(SSX2_OP_WorldExpandUIBoxes.bl_idname,\
			icon='DISCLOSURE_TRI_DOWN' if io.expandImportModel\
			else 'DISCLOSURE_TRI_RIGHT',emboss=False,text="").prop = 'ssx2_WorldImportExportProps.expandImportModel'
		box_row.prop(io, "importModels", text="Models (Experimental)")
		if io.expandImportModel:
			label_row = the_box.row()
			label_row.scale_y = 0.2
			label_row.label(text="Instances")
			prop_enum_horizontal(the_box, io, 'instanceImportGrouping', "Grouping", spacing=0.3)

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

		row = col.row().split(factor=0.36)
		row.prop(io, 'exportAutoBuild')
		if io.exportAutoBuild:
			row.operator(SSX2_OP_ChooseMultitoolExe.bl_idname, icon='FILEBROWSER')

			

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
		self.layout.label(icon='SURFACE_NSURFACE')

	def draw(self, context):
		# from .ssx2_world_patches import glob_obj_proxy
		col = self.layout.column()

		obj = bpy.context.active_object

		row = col.row(align=True)
		row.operator(SSX2_OP_CopyPatchUVsToSelected.bl_idname, text="Copy UVs to")
		row.operator(SSX2_OP_CopyMaterialToSelected.bl_idname, text="Copy Mat to")

		if obj is not None:
			if obj.type == 'SURFACE':
				col.operator(SSX2_OP_ToggleControlGrid.bl_idname, text="To Control Grid")
			elif obj.ssx2_PatchProps.isControlGrid:
				col.operator(SSX2_OP_ToggleControlGrid.bl_idname, text="To Patch")
			else:
				col.operator(SSX2_OP_ToggleControlGrid.bl_idname)
		else:
			col.operator(SSX2_OP_ToggleControlGrid.bl_idname)

		col.operator(SSX2_OP_PatchSplit4x4.bl_idname, text="Split to 4x4")
		col.operator(SSX2_OP_MergePatches.bl_idname)
		
		# if glob_obj_proxy is None:
		# 	col.operator(SSX2_OP_PatchUVEditor.bl_idname, text="UV Editor", icon='WINDOW')
		# else:
		# 	col.operator(SSX2_OP_PatchUVEditor.bl_idname, text="Apply UV Edits", icon='CHECKMARK')
			#col.label(text="")

		#col.label(text="Spline Cage")
		col.separator()
		col.operator(SSX2_OP_CageToPatch.bl_idname, text="Patch from Cage")

		col_b = col.column(align=True)
		row = col_b.row(align=True)
		row.operator("curve.switch_direction", text="Flip U Order")
		row.operator(SSX2_OP_FlipSplineOrder.bl_idname, text="Flip V Order")
		
		row = col_b.row(align=True)
		row.operator(SSX2_OP_SelectSplineCageU.bl_idname, text="Select U")
		row.operator(SSX2_OP_SelectSplineCageV.bl_idname, text="Select V")

		col.operator(SSX2_OP_AddCageVGuide.bl_idname, text="Add V Guide", icon='ADD')
		
		col.operator(SSX2_OP_Patch_Slide_V.bl_idname, text="Slide V", icon='ARROW_LEFTRIGHT')

		col.separator()
		box = col.box()
		box.label(text="UV Transform")
		col_b = box.column(align=True)
		row = col_b.row(align=True)
		row.operator(SSX2_OP_PatchUVTransform.bl_idname, text="Rotate -90", icon='LOOP_BACK').xform = 0
		row.operator(SSX2_OP_PatchUVTransform.bl_idname, text="Rotate 90", icon='LOOP_FORWARDS').xform = 1
		row = col_b.row(align=True)
		row.operator(SSX2_OP_PatchUVTransform.bl_idname, text="Flip U", icon='SORT_DESC').xform = 2
		row.operator(SSX2_OP_PatchUVTransform.bl_idname, text="Flip V", icon='FORWARD').xform = 3
		
		#layout.label(text="Other")
		col.separator()
		prop_split(col, context.scene.ssx2_WorldUIProps, 'patchSelectByType', "Select by Type")

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
			row = col.row(align=True)
			row.operator(SSX2_OP_SelectModel.bl_idname, text="Select Model").add_mode = False
			row.operator(SSX2_OP_SelectModel.bl_idname, text="Select Model (Add)").add_mode = True
			prop_split(col, context.object, 'ssx2_ModelForInstance', "Model", spacing=0.2)
			row = col.row()
			row.prop(context.object, 'show_instancer_for_viewport', text='Show Instancer', \
					icon="HIDE_OFF" if context.object.show_instancer_for_viewport else "HIDE_ON")
			row.prop(context.object, 'show_in_front', \
					icon="HIDE_OFF" if context.object.show_in_front else "HIDE_ON")

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

				for mod in context.active_object.modifiers:
					if mod.type == 'NODES' and mod.node_group:
						if mod.node_group.name.startswith("PathLinesAppend"):
							break

				row = layout.row()
				row.prop(mod, '["Input_2"]', text="Show Points", \
					icon="HIDE_OFF" if mod["Input_2"] else "HIDE_ON")
				row.prop(mod, '["Input_3"]', text="Show Event", \
					icon="HIDE_OFF" if mod["Input_3"] else "HIDE_ON")

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

				for event in path_props.events:
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

		col = self.layout.column()
		row = col.row(align=True)
		row.operator(SSX2_OP_AddPatchMaterial.bl_idname, text="New Patch Material", icon='ADD')

		if obj is not None:
			if obj.ssx2_CurveMode == 'CAGE':
				row.operator(SSX2_OP_SendMaterialToModifier.bl_idname, text="Send to Modifier", icon='MODIFIER_ON')

class SSX2_PatchPropPanel(SSX2_Panel):
	bl_label = "BX Surface Patch"
	bl_idname = "OBJECT_PT_SSX2_Surface_Patch"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"
	bl_options = {"HIDE_HEADER"}

	@classmethod
	def poll(cls, context):
		return context.scene.bx_GameChoice == 'SSX2' and \
		(context.object is not None)

	def draw(self, context):
		col = self.layout.column()
		obj = context.object
		
		if obj.type == 'SURFACE' or obj.ssx2_PatchProps.isControlGrid or obj.ssx2_CurveMode == 'CAGE':
			props = obj.ssx2_PatchProps
			prop_split(col, props, 'type', "Patch Type")
			col.prop(props, 'showoffOnly', text="Showoff Only")
			box = col.box()
			box.label(text="UV Mapping")
			row = box.row()
			row.prop(props, 'fixU', text="Fix U Seam")
			row.prop(props, 'fixV', text="Fix V Seam")
			box.prop(props, 'useManualUV', text="Use Manual UVs")
			if not props.useManualUV:
				prop_split(box, props, 'texMapPreset', "UV Preset", spacing=0.3)
				
			if props.useManualUV:
				col_split = box.split(factor=0.5)
				col_split.prop(props, "manualUV1", text="")
				col_split.prop(props, "manualUV3", text="")
				col_split = box.split(factor=0.5)
				col_split.prop(props, "manualUV0", text="")
				col_split.prop(props, "manualUV2", text="")
				# col.label(text="")
				# ali_col = col.column(align=True)
				# a = ali_col.split(factor=0.5, align=True)
				# a.prop(props, "manualUV1", text="")
				# a.prop(props, "manualUV3", text="")
				# a = ali_col.split(factor=0.5, align=True)
				# a.prop(props, "manualUV0", text="")
				# a.prop(props, "manualUV2", text="")
				# col.label(text="")
				# ali_col = col.column(align=True)
				# a = ali_col.row(align=True)
				# a.prop(props, "manualUV1", text="")
				# a.prop(props, "manualUV3", text="")
				# a = ali_col.row(align=True)
				# a.prop(props, "manualUV0", text="")
				# a.prop(props, "manualUV2", text="")


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
	SSX2_PatchPropPanel,

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