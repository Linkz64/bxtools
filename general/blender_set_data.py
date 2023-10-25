import bpy, bmesh
from mathutils import Vector
import struct
import os

from .bx_utils import interpolate_patch_uvs

from ..ssx2.ssx2_constants import indices_for_control_grid

mdl_data = dict(
    texture_list = ["_board_alpha_test.png", "kaori1_boot.284.png"],
    index_group_list  = [[(0, 1, 2), (2, 1, 3)], [(4, 5, 6), (6, 5, 7)]],
    vertex_list = [(-1, 0, -1), (1, 0, -1), (-1, 0, 1), (1, 0, 1), (-1, 0, 1), (1, 0, 1), (-1, 0, 3), (1, 0, 3)],
    normal_list = [(1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
    uv_list     = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)],
)

def set_mesh_data(obj_name, mdl_data, textures_path='', collection=None):
    """
    Generates a mesh.

    obj_name = Name of new Blender object
    mdl_data = Dictionary containing mesh data:
        dict(
            texture_list = ["suit.png", "boot.png"],
            index_group_list  = [[(0, 1, 2), (2, 1, 3)], [(4, 5, 6), (6, 5, 7)]],
            vertex_list = [(-1, 0, -1), (1, 0, -1), (-1, 0, 1), (1, 0, 1), (-1, 0, 1), (1, 0, 1), (-1, 0, 3), (1, 0, 3)],
            normal_list = [(1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
            uv_list     = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)],
        )
    textures_path = Folder path for texture files
    collection = Active collection in the outliner (Optional)
    """

    mesh = bpy.data.meshes.new(obj_name)
    obj = bpy.data.objects.new(obj_name, mesh)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_map = bm.loops.layers.uv.new()
    collection.objects.link(obj)

    
    textures_path = "X:/BXTest/Textures/"
    collection = bpy.context.collection

    for i in range(len(mdl_data['vertex_list'])):
        vtx = bm.verts.new(mdl_data['vertex_list'][i])
        vtx.normal = Vector(mdl_data['normal_list'][i])
    bm.verts.ensure_lookup_table()


    for i, tex_file in enumerate(mdl_data['texture_list']):
        cur_tex_path = textures_path + tex_file
        mat_name = os.path.splitext(tex_file)[0]

        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
    
            mat_node_bsdf = mat.node_tree.nodes["Principled BSDF"]
            mat_node_mix  = mat.node_tree.nodes.new(type='ShaderNodeMixShader')
            mat_node_tran = mat.node_tree.nodes.new(type='ShaderNodeBsdfTransparent')
            mat_node_out  = mat.node_tree.nodes["Material Output"]

            if tex_file in bpy.data.textures: # it's supposed to be .images not .textures
                mat_node_tex = mat.texture_slots.add()
                mat_node_tex.texture = bpy.data.textures[tex_file]
            elif os.path.isfile(cur_tex_path):
                mat_node_tex = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
                mat_node_tex.image = bpy.data.images.load(cur_tex_path)
            else:
                mat_node_tex = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
                print(f"Main texture not loaded for {mat.name} {tex_file}")

            mat_node_tran.location = (-200, 300)
            mat_node_bsdf.location = (-200, 200)
            mat_node_tex.location  = (-500, 300)
            mat_node_mix.location  = ( 100, 300)
            mat.node_tree.links.new(mat_node_bsdf.inputs[0], mat_node_tex.outputs[0])  # Base Color <- Color
            mat.node_tree.links.new(mat_node_mix.inputs[0],  mat_node_tex.outputs[1])  # Factor <- Alpha
            mat.node_tree.links.new(mat_node_mix.inputs[1],  mat_node_tran.outputs[0]) # Shader <- BSDF # I think older versions
            mat.node_tree.links.new(mat_node_mix.inputs[2],  mat_node_bsdf.outputs[0]) # Shader <- BSDF # have these swapped
            mat.node_tree.links.new(mat_node_out.inputs[0],  mat_node_mix.outputs[0])  # Surface < Shader

        try:
            mat.node_tree.nodes["Principled BSDF"].inputs['Roughness'].default_value = 1 # inputs[7]
        except:
            try:
                mat.node_tree.nodes["Diffuse BSDF"].inputs['Roughness'].default_value = 1
            except:
                print(f"No BSDF shader on material: {mat.name}")
        
        mat.blend_method = 'BLEND' # 'HASHED' 'OPAQUE'

        obj.data.materials.append(mat)

        for j in mdl_data['index_group_list'][i]:
            poly = bm.faces.new((bm.verts[j[0]], bm.verts[j[1]], bm.verts[j[2]]))
            poly.material_index = i
            poly.smooth = True
            
            for k in range(3):
                poly.loops[k][uv_map].uv = mdl_data['uv_list'][j[k]]

        
        bm.to_mesh(mesh)

    bm.free()
#set_model_data("Model", mdl_data)


def set_patch_object(patch_points, name, collection='Patches'):
    """
    patch_points: 16 xyzw values
    name: of patch object
    """
    surface_data = bpy.data.curves.new(name, 'SURFACE')
    if surface_data is None:
        surface_data = bpy.data.curves.new(name, 'SURFACE')

    surface_data.dimensions = '3D'
    for i in range(4):
        spline = surface_data.splines.new(type='NURBS')
        spline.points.add(3) # one point already exists, added 3 more
        for point in spline.points:
            point.select = True

    surface_data.resolution_u = 2
    surface_data.resolution_v = 2

    surface_object = bpy.data.objects.new(name, surface_data)
    bpy.data.collections[collection].objects.link(surface_object)
    
    splines = surface_data.splines # this every internal island/surface, not splines

    bpy.context.view_layer.objects.active = surface_object
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.curve.make_segment()
    splines[0].order_u = 4
    splines[0].order_v = 4
    splines[0].use_endpoint_u = True
    splines[0].use_endpoint_v = True
    splines[0].use_bezier_u = True
    splines[0].use_bezier_v = True

    for s in splines:
        for i, p in enumerate(s.points):
            p.co = patch_points[i]

    bpy.ops.object.mode_set(mode = 'OBJECT')
    bpy.context.active_object.select_set(False)
    return surface_object

def set_patch_control_grid(mesh, patch_points, patch_uvs):
    """Creates control grid mesh data to be used by an object"""
    
    #uv_square = [(uv[0], -uv[1]) for uv in patch_uvs]
    uv_grid = interpolate_patch_uvs(patch_uvs, 4)
    
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.verify()

    for j in range(len(patch_points)):
        vtx = bm.verts.new((patch_points[j][0], patch_points[j][1], patch_points[j][2]))
    bm.verts.ensure_lookup_table()

    for j, idx in enumerate(indices_for_control_grid):
        face = bm.faces.new((bm.verts[idx[0]], bm.verts[idx[1]], bm.verts[idx[2]], bm.verts[idx[3]]))

        face.loops[0][uv_layer].uv = uv_grid[indices_for_control_grid[j][0]]
        face.loops[1][uv_layer].uv = uv_grid[indices_for_control_grid[j][1]]
        face.loops[2][uv_layer].uv = uv_grid[indices_for_control_grid[j][2]]
        face.loops[3][uv_layer].uv = uv_grid[indices_for_control_grid[j][3]]

    #bm.faces.ensure_lookup_table()

    bm.to_mesh(mesh)
    bm.free()

    return mesh

def set_patch_material(name):
    # handle texture after return?
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True

    mat_node_out = mat.node_tree.nodes["Material Output"] # existing node
    mat_node_bsd = mat.node_tree.nodes["Principled BSDF"] # existing node (delete and replace with diffuse?)
    #mat_node_mix = mat.node_tree.nodes.new(type='ShaderNodeMixShader')# remove if no transparency in ssx patches
    #mat_node_trn = mat.node_tree.nodes.new(type='ShaderNodeBsdfTransparent')# remove if no transparency

    mat_node_tex = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    mat_node_lit = mat.node_tree.nodes.new(type='ShaderNodeTexImage',) # for LightMap (not connected to anything)
    mat_node_map = mat.node_tree.nodes.new(type='ShaderNodeMapping')
    mat_node_tco = mat.node_tree.nodes.new(type='ShaderNodeUVMap')#mat.node_tree.nodes.new(type='ShaderNodeTexCoord')
    mat_node_obj = mat.node_tree.nodes.new(type='ShaderNodeAttribute')#'ShaderNodeObjectInfo') # or use Attribute instead

    mat_node_lit.name = "Bake"

    #mat_node_mix.location = ( 100, 300)
    #mat_node_trn.location = (-200, 300)
    mat_node_bsd.location = (-200, 300)#mat_node_bsd.location = (-200, 200)
    #mat_node_lit.location = (-500, -20) # not connected to anything
    mat_node_tex.location = (-500, 300)
    mat_node_map.location = (-700, 300)
    mat_node_tco.location = (-900, 300)
    mat_node_obj.location = (-900, 100)
    mat.node_tree.links.new(mat_node_map.inputs[2], mat_node_obj.outputs[1]) # Rotation <- Vector #Rotation <- Color
    mat.node_tree.links.new(mat_node_map.inputs[0], mat_node_tco.outputs[0]) # Vector <- UV #mat.node_tree.links.new(mat_node_map.inputs[0], mat_node_tco.outputs[2]) # Vector <- UV
    mat.node_tree.links.new(mat_node_tex.inputs[0], mat_node_map.outputs[0]) # Vector <- Vector
    mat.node_tree.links.new(mat_node_bsd.inputs[0], mat_node_tex.outputs[0]) # Base Color <- Color
    mat.node_tree.links.new(mat_node_out.inputs[0], mat_node_bsd.outputs[0]) # Suface <- BSDF
    #mat.node_tree.links.new(mat_node_mix.inputs[0], mat_node_tex.outputs[1]) # Factor <- Alpha
    #mat.node_tree.links.new(mat_node_mix.inputs[1], mat_node_trn.outputs[0]) # Shader <- BSDF # I think older versions
    #mat.node_tree.links.new(mat_node_mix.inputs[2], mat_node_bsd.outputs[0]) # Shader <- BSDF # have these swapped
    #mat.node_tree.links.new(mat_node_out.inputs[0], mat_node_mix.outputs[0]) # Surface < Shader

    #mat_node_mix.inputs[0].show_expanded = True
    mat_node_bsd.inputs[0].show_expanded = True
    mat_node_obj.attribute_type = 'OBJECT'
    mat_node_obj.attribute_name = 'ssx2_PatchProps.texMap'

    mat.preview_render_type = "FLAT"

    try:
        mat.node_tree.nodes["Principled BSDF"].inputs['Roughness'].default_value = 1 # inputs[7]
    except:
        try:
            mat.node_tree.nodes["Diffuse BSDF"].inputs['Roughness'].default_value = 1
        except:
            print(f"No BSDF shader on material: {mat.name}")
    return mat