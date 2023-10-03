import bpy
#from bpy_extras import mesh_utils
from mathutils import Vector
#import bmesh

from ..general import bx_utils
from ..general.bx_utils import normalize

import os



def get_images_from_folder(folder_path, extension='.png'):
    if not os.path.isdir(folder_path):
        return None

    images = []

    contents = os.listdir(folder_path)
    folder_path = folder_path+"/"

    for i, item in enumerate(contents):
        if item[-4:len(item)] == extension:
            img = bpy.data.images.get(item)
            if img is None:
                img = bpy.data.images.load(folder_path+item, check_existing=False)
            images.append(img)

    return images

def get_shape_keys(obj, indexed=True, include_unused=False, include_names=False):
    """
    indexed: if True, return coordinate and vertex index in the main list
    include_unused: if True, coordinates with a value of (0.0, 0.0, 0.0) will be allowed
        in the main list
    include_names: if True, returns a tuple (shape_keys, names) with the names being at index 1
    """
    zero = (0.0, 0.0, 0.0)
    basis = [v.co for v in obj.data.vertices]
    shape_keys_list = []
    shape_keys_names = []
    final_shape_keys = []
    final_names = []

    if obj.type == 'MESH' and obj.data.shape_keys:
        shape_key_blocks = obj.data.shape_keys.key_blocks
        for block in shape_key_blocks:
            if block.name == 'Basis':
                continue
            else:
                temp_coords = []
                for data in block.data:
                    temp_coords.append(data.co)
                shape_keys_list.append(temp_coords)
                if include_names:
                    shape_keys_names.append(block.name)

    for i, shape_key in enumerate(shape_keys_list): # format to SSX
        temp_shape_key = []
        for j, co in enumerate(shape_key):
            x = co.x - basis[j].x
            y = co.y - basis[j].y
            z = co.z - basis[j].z
            is_used = (x, y, z) != zero
            if indexed and is_used:
                temp_shape_key.append([(x, y, z), j])
            elif indexed == False and is_used:
                temp_shape_key.append((x, y, z))
            else:
                pass
        if len(temp_shape_key) == 0 and include_unused:
            final_shape_keys.append([zero, i])
            if include_names:
                final_names.append(shape_keys_names[i])
        elif len(temp_shape_key) > 0:
            final_shape_keys.append(temp_shape_key)
            if include_names:
                final_names.append(shape_keys_names[i])
    if include_names:
        return (final_shape_keys, final_names)
    else:
        return final_shape_keys


def get_polygons_by_material(obj, include_materials=True):
    """
    include_materials: if True, returns a tuple including polygons and materials
    Unused material slots are ignored
    """
    used_mat_slot_indices = [] # indices of used material slots

    for poly in obj.data.polygons:
        if poly.material_index not in used_mat_slot_indices:
            used_mat_slot_indices.append(poly.material_index)

    polys_by_mats = [[] for i in range(len(used_mat_slot_indices))]

    for poly in obj.data.polygons:
        current_list = polys_by_mats[used_mat_slot_indices.index(poly.material_index)]
        temp_poly = []

        for vert_idx in poly.vertices:
            temp_poly.append(vert_idx)

        if len(poly.vertices) == 3:
            current_list.append(temp_poly)
        elif len(poly.vertices) == 4:
            current_list.append(bx_utils.quad_to_2_triangles(temp_poly)[0])
            current_list.append(bx_utils.quad_to_2_triangles(temp_poly)[1])
        else:
            print(f"Ngon detected on {poly}, skipping.")
    
    if include_materials:
        mats = [obj.data.materials[mat_index] for mat_index in used_mat_slot_indices]
        return (polys_by_mats, mats)
    else:
        return polys_by_mats

def get_vertices(obj):
    return [(v.co.x, v.co.y, v.co.z) for v in obj.data.vertices]

def get_vertex_normals(obj):
    return [(v.normal.x, v.normal.y, v.normal.z) for v in obj.data.vertices]

def get_tangent_normals(obj):
    obj.data.calc_tangents()
    tangent_normals = [(0.0, 0.0, 0.0)] * len(obj.data.vertices)
    for poly in obj.data.polygons:
        for loop in [obj.data.loops[i] for i in poly.loop_indices]:
            # add to list in order of vertex index
            tangent_normals[loop.vertex_index] = (loop.tangent[0], loop.tangent[1], loop.tangent[2])
    return tangent_normals

def get_uvs(obj): # RENAME THIS.
    uv_list = [(0.0, 0.0)] * len(obj.data.uv_layers[0].data)
    for poly in obj.data.polygons:
        for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
            uv_coords = obj.data.uv_layers[0].data[loop_idx].uv
            uv_list[vert_idx] = (uv_coords[0], -uv_coords[1] + 1.0) # add to list in order of vertex index
    return uv_list

def get_uvs_per_verts(obj):
    uv_list = [(0.0, 0.0)] * len(obj.data.uv_layers[0].data)
    for poly in obj.data.polygons:
        for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
            uv_coords = obj.data.uv_layers[0].data[loop_idx].uv
            uv_list[vert_idx] = (uv_coords[0], uv_coords[1]) # add to list in order of vertex index
    return uv_list

def get_skeleton(obj):
    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE":
            if modifier.object is not None:
                return modifier.object
    if obj.parent is not None:
        if obj.parent.type == 'ARMATURE':
            return obj.parent
        else:
            print(f"Cannot find parent Armature/Skeleton for {obj.name}")
            return None
    else:
        print(f"{obj.name} is not parented/assigned to an Armature")
        return None

def get_bones_used(obj, skel=None, threshold=0.009, include_indices=False, sort_type='outliner'):
    """
    skel: (optional) obj's parent skeleton
    threshold: the minimum weight (float) for appending the bone
        Default: 0.0
    include_indices: if True, returns a tuple including bone names list and group indices list
        Default: False
    sort_type:
        - None = do not sort
        - 'name' sort by name
        - 'index' sort by order of indices (same order as the 'Vertex Groups' menu)
        - 'outliner' sort by order of bone hierarchy (parenting)
    
    Returns a list of bone names used by the object
    Note that if the object is parented to a bone then indices will not be included,
        only a list with a single bone name.
    """
    if skel is None:
        skel = get_skeleton(obj).data
        if skel is None:
            return None
    skel = skel.data
    bone_keys = skel.bones.keys()
    all_groups = obj.vertex_groups
    used_bones = []
    groups_indices = []
    
    if obj.parent_type == 'BONE': # and len(all_groups) == 0:
        return [obj.parent_bone]

    for v in obj.data.vertices:
        for v_group in v.groups: # v_group is the group object/element, .group is the index
            index = v_group.group
            name = all_groups[index].name
            if v_group.weight > threshold and name not in used_bones:
                if name in bone_keys:
                    used_bones.append(name)
                    groups_indices.append(index)
    if sort_type == 'index':
        used_bones.sort(key=lambda temp_key: temp_key[1]) # sort by groups_indices
    elif sort_type == 'outliner':
        used_bones = [bone for bone in bone_keys if bone in used_bones]
    elif sort_type == 'name':
        used_bones = sorted(used_bones)
    elif sort_type == None:
        pass
    else:
        raise Exception("Invalid sort_type for get_bones_used(). Run print(help(get_used_bones)) for available types.")
        return None
    if include_indices:
        return (used_bones, groups_indices)
    else:
        return used_bones

def get_vertices_and_weights(obj, threshold=0.009, used_bones=None, skel=None):

    final_weights = [] # format should be (weight%, bone_index, parent_skel_id) # parent will be obtained by actual parent of the skeleton, it should have a custom id if it's from template.blend, if none then an ID will be required
    vertices = []

    if used_bones is None:
        used_bones = get_bones_used(obj)

    if skel is None:
        skel = get_skeleton(obj).data
        if skel is None:
            return None, f"No Skeleton on {obj.name}"
    else:
        skel = skel.data
    bone_keys = skel.bones.keys()

    if obj.parent_type == 'BONE': # and len(all_groups) == 0:
        final_weights.append([(100, 0, 0)]) # (weight, bone_index?, parent_skel_id?)
        for v in obj.data.vertices:
            vtx = obj.matrix_world @ v.co
            vertices.append(((vtx.x, vtx.y, vtx.z), 0))
        return (vertices, final_weights)

    for v in obj.data.vertices:
        groups = v.groups

        # if len(groups) > 3:
        #     print(f"BXWarn: More than 3 weights on vertex {v.index}")
        if len(groups) == 0:
            return False, f"Vertex {v.index} on object {obj.name} is not weighted to any bones."

        temp_v_group = []

        for v_group in groups: # v_group is group object, .group is index
            group_index = v_group.group
            group_name = obj.vertex_groups[group_index].name
            weight = v_group.weight
            try:
                skel_id = skel.bones[group_name]['Skeleton ID'] # also add check for skeleton's properties
            except:
                print(f"BXWarn: Skeleton ID not set on bone {group_name}. ID falling back to 0.")
                skel_id = 0
            
            if weight >= threshold and group_name in used_bones:
                temp_v_group.append([weight*100, bone_keys.index(group_name), 0])
            else:
                print(f"BXWarn: Weight of {threshold} or less on vertex {v.index}. Skipping.") #print(f"Problem on Vertex {v.index}, Vertex Group {v_group.group}, Bone {group_name}, Weight float {round(v_group.weight, 3)}, Weight int {weight}")
                # or should I have 2 ifs for 0 and threshold, then threshold one will be rounded up to 0.1 aka 10?
                # also there needs to be a print when a group is used but it's not in used_bones/bone_keys
                continue # skip to next loop

        # Sort the weights in order of bone_index. temp_key refers to index of bone_index inside temp_v_group
        temp_v_group.sort(key=lambda temp_key: temp_key[1])

        temp_v_group = normalize(temp_v_group, key=0)

        new_temp_v_group = []
        for j in range(len(temp_v_group)):
            rounded = int(round(temp_v_group[j][0], -1))
            if rounded > 0:
                new_temp_v_group.append((rounded, temp_v_group[j][1], temp_v_group[j][2]))
            else:
                print(f"BXWarn: Optimized vertex {v.index} to weight of 0. Skipping.")
        if len(new_temp_v_group) > 3:
            return False, f"{obj.name} has too many weights on vertex {v.index}."

        vtx = obj.matrix_world @ v.co # calculate world/global position

        if len(new_temp_v_group) > 0:
            if new_temp_v_group in final_weights: # check duplicates
                vertices.append(((vtx.x, vtx.y, vtx.z), final_weights.index(new_temp_v_group))) # i can also do v.co.xyz im p sure
            else:
                final_weights.append(new_temp_v_group)
                vertices.append(((vtx.x, vtx.y, vtx.z), len(final_weights)-1)) # add vertex xyz and index of last item in weight list
        else:
            print(f"BXWarn: No weights assigned on vertex {v.index}.")
            #vertices.append(((vtx.x, vtx.y, vtx.z), 0))
    return (vertices, final_weights)




def get_mesh_data(obj, skel):
    """
    obj = Blender Mesh Object, e.g bpy.context.active_object, bpy.data.objects['Body3000'] or bpy.data.meshes['Body3000']
    skel = Blender Armature Object, e.g bpy.data.objects['Armature'], bpy.data.armatures['Armature']
    """

    # if the input type is an object then the data is accessed with obj.data, otherwise it's accessed directly
    # input.data.polygons or input.polygons. input.data.bones or input.bones.


    if type(skel) == bpy.types.Armature:
        b_skel_data = skel
    elif type(skel) == bpy.types.Object:
        b_skel_data = skel.data
    else:
        return "BxError: Skeleton is not an armature object."

    if type(obj) == bpy.types.Mesh:
        b_mesh_data = obj
    elif type(obj) == bpy.types.Object:
        b_mesh_data = obj.data
    else:
        return "BxError: Model is not a mesh object."



    #print(obj.type)
    if len(b_mesh_data.polygons) == 0:
        return "BXError: Object does not have any polygons."


    #out = [] # last return list
    #weight_list = [ [(int(0), int(0))] ] # vertex groups

    vertex_list = []
    uv_list = [(0.0, 0.0)] * len(b_mesh_data.uv_layers.active.data) # number of uv points
    weight_list = [] # vertex groups
    vertex_normal_list = [] # vertex normals not poly/face normals
    tangent_normal_list = [(0.0, 0.0, 0.0)] * len(b_mesh_data.vertices)
    polygons_by_material_list = []
    material_list = []
    bone_list = []

    b_mesh_data.calc_tangents() # precalculate tangents of 'b_mesh_data'


    ### Polygons, UVs and Tangents

    if len(b_mesh_data.polygons) > 0 and len(obj.material_slots) > 0:


        temp_polygons_list = []

        for i in range(len(obj.material_slots)):
            temp_polygons_list.append([])
            material_list.append(obj.material_slots[i].material.name)


        for poly in b_mesh_data.polygons: # Loops per poly

            # Get Tangents
            for loop in [b_mesh_data.loops[i] for i in poly.loop_indices]:
                tangent_normal_list[loop.vertex_index] = (loop.tangent[0], loop.tangent[1], loop.tangent[2])


            #print("poly", poly.index, "mat idx:", poly.material_index)
            #slot = obj.material_slots[poly.material_index]
            #mat = slot.material
            #mat_name = mat.name


            temp_poly = []

            for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):

                uv_coords = b_mesh_data.uv_layers.active.data[loop_idx].uv # active refers to which UVMap is selected in object data properties tab

                temp_poly.append( vert_idx )
                uv_list[vert_idx] = (uv_coords[0], uv_coords[1]) # add to list in order of vertex index


            if len(poly.vertices) == 3:
                temp_polygons_list[poly.material_index].append(temp_poly)
            elif len(poly.vertices) == 4:
                #temp_polygons_list[poly.material_index].append(temp_poly)
                #temp_polygons_list[poly.material_index].append(bx_utils.quad_to_strip(temp_poly))
                temp_polygons_list[poly.material_index].append(bx_utils.quad_to_2_triangles(temp_poly)[0])
                temp_polygons_list[poly.material_index].append(bx_utils.quad_to_2_triangles(temp_poly)[1])
            else:
                return f"BXError: Unable to generate tristrip. Possibly due to an Ngon.\n(Polygon:{poly.index}, Vertex count:{len(poly.vertices)})"

        for polys in temp_polygons_list:
            polygons_by_material_list.append(polys)
    else:
        return f"No polygons or materials found."




    ### Vertices, Weights, Vertex Normals, Bones

    objVtxGrp = obj.vertex_groups # this is for all vertex groups in an object. for per-vertex use: b_mesh_data.vertices.groups

    for group in objVtxGrp:
        corresBone = b_skel_data.bones[group.name] # corresponding bone

        if corresBone.parent is not None:
            skelParent = corresBone.parent['Skeleton ID']
            boneParent = corresBone.parent['Bone Index']
        else:
            skelParent = -1 # root bone (hips) will have this
            boneParent = -1 # ^

        if bpy.context.scene.bx_gameChoice == 'SSX2':
            try:
                bone_list.append((
                    group.name, 
                    skelParent, #corresBone['Skeleton ID'],
                    boneParent, #corresBone['Bone Index'], 
                    corresBone['Unknown ID'],
                    corresBone['Unknown Bone ID'], # might be boneID 
                    bx_utils.bone_rel_loc(corresBone),
                    bx_utils.get_custom_vec(corresBone, 'a) Bone Rotation'),
                    bx_utils.get_custom_vec(corresBone, 'b) Bone Rotation1'),
                    bx_utils.get_custom_vec(corresBone, 'c) Bone Unknown'),
                    bx_utils.get_custom_vec(corresBone, 'd) Bone Unknown1')
                ))
            except:
                return f"BXError: Error on bone '{group.name}'.\n    Make sure bones have the correct custom properties set."




    if len(b_mesh_data.vertices) > 0: # Vertices, Weights and Vertex Normals

        for v in b_mesh_data.vertices:
            numGroups = len(v.groups)

            if numGroups > 3: 
                print(f"BXWarn: More than 3 weights on vertex {v.index}")
            #elif numGroups < 1: print(f"BXWarn: 0 weights on vertex {v.index}")

            temp_vGroup = []



            for j in range(numGroups):

                vGroup = v.groups[j]

                vGroupName = objVtxGrp[vGroup.group].name

                vGroupWeight = int(round(vGroup.weight*100)) # Weight Percentage

                if vGroupWeight > 0 and vGroupWeight < 90: # just do if weight less than 90
                    vGroupWeight = int(round(vGroupWeight+5.1, -1)) # round to next 10
                elif vGroupWeight > 90:
                    vGroupWeight = int(100)


                try:
                    currentBone = b_skel_data.bones[f"{vGroupName}"]

                    vGroupIndex = currentBone['Bone Index'] # or vGroup.group
                    vGroupParent = currentBone['Skeleton ID']
                    
                    if vGroupWeight > 0:
                        temp_vGroup.append((vGroupWeight, vGroupIndex, vGroupParent)) # in game struct I have it as (weight, boneIndex, skelParentID)
                    else:
                        #print(f"Problem on Vertex {v.index}, Vertex Group {vGroup.group}, Bone {vGroupName}, Weight float {round(vGroup.weight, 3)}, Weight int {vGroupWeight}")
                        print(f"BXWarn: Weight of 0% on vertex {v.index}. Skipping.")
                        continue # skip to next loop

                except:
                    print(f"BXError: Error on bone '{vGroupName}'.\n    Make sure bones have the correct custom properties set.")


            temp_vGroup.sort(key=lambda tempkey: tempkey[1]) # Sort the weights in order of boneID. tempkey refers to index of boneID inside temp_vGroup


            vtx = obj.matrix_world @ v.co # calculate world/global position


            if len(temp_vGroup) > 0:

                if temp_vGroup in weight_list: # check duplicates
                    vertex_list.append(((vtx.x, vtx.y, vtx.z), weight_list.index(temp_vGroup))) # i can also do v.co.xyz im p sure

                else:
                    weight_list.append(temp_vGroup)
                    vertex_list.append(((vtx.x, vtx.y, vtx.z), len(weight_list)-1)) # add vertex xyz and index of last item in weight list
            else:
                print(f"BXWarn: No weights assigned on vertex {v.index}.")
                #vertex_list.append(((vtx.x, vtx.y, vtx.z), 0))


            vertex_normal_list.append((v.normal.x, v.normal.y, v.normal.z)) # Vertex Normal


    out = dict(
        vertices = vertex_list,
        polygons_by_material = polygons_by_material_list,
        uvs = uv_list,
        vertex_normals = vertex_normal_list,
        tangent_normals = tangent_normal_list,
        weights = weight_list,
        bones = bone_list,
        materials = material_list
    )

    return out



def get_mesh_data_for_3(obj, skel, original_data=None):
    """
    obj = Blender Mesh Object, e.g bpy.context.active_object, bpy.data.objects['Body3000'] or bpy.data.meshes['Body3000']
    skel = Blender Armature Object, e.g bpy.data.objects['Armature'], bpy.data.armatures['Armature']
    """

    # if the input type is an object then the data is accessed with obj.data, otherwise it's accessed directly
    # input.data.polygons or input.polygons. input.data.bones or input.bones.


    if type(skel) == bpy.types.Armature:
        b_skel_data = skel
    elif type(skel) == bpy.types.Object:
        b_skel_data = skel.data
    else:
        return "BxError: Skeleton is not an armature object."

    if type(obj) == bpy.types.Mesh:
        b_mesh_data = obj
    elif type(obj) == bpy.types.Object:
        b_mesh_data = obj.data
    else:
        return "BxError: Model is not a mesh object."



    #print(obj.type)
    if len(b_mesh_data.polygons) == 0:
        return "BXError: Object does not have any polygons."


    #out = [] # last return list
    #weight_list = [ [(int(0), int(0))] ] # vertex groups

    vertex_list = []
    uv_list = [(0.0, 0.0)] * len(b_mesh_data.uv_layers.active.data) # number of uv points
    weight_list = [] # vertex groups
    vertex_normal_list = [] # vertex normals not poly/face normals
    tangent_normal_list = [(0.0, 0.0, 0.0)] * len(b_mesh_data.vertices)
    polygons_by_material_list = []
    material_list = []
    bone_list = []

    b_mesh_data.calc_tangents() # precalculate tangents of 'b_mesh_data'


    ### Polygons, UVs and Tangents

    if len(b_mesh_data.polygons) > 0 and len(obj.material_slots) > 0:


        temp_polygons_list = []

        for i in range(len(obj.material_slots)):
            temp_polygons_list.append([])
            material_list.append(obj.material_slots[i].material.name)


        for poly in b_mesh_data.polygons: # Loops per poly

            # Get Tangents
            for loop in [b_mesh_data.loops[i] for i in poly.loop_indices]:
                tangent_normal_list[loop.vertex_index] = (loop.tangent[0], loop.tangent[1], loop.tangent[2])


            #print("poly", poly.index, "mat idx:", poly.material_index)
            #slot = obj.material_slots[poly.material_index]
            #mat = slot.material
            #mat_name = mat.name


            temp_poly = []

            for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):

                uv_coords = b_mesh_data.uv_layers.active.data[loop_idx].uv # active refers to which UVMap is selected in object data properties tab

                temp_poly.append( vert_idx )
                uv_list[vert_idx] = (uv_coords[0], uv_coords[1]) # add to list in order of vertex index


            if len(poly.vertices) == 3:
                temp_polygons_list[poly.material_index].append(temp_poly)
            elif len(poly.vertices) == 4:
                #temp_polygons_list[poly.material_index].append(temp_poly)
                #temp_polygons_list[poly.material_index].append(bx_utils.quad_to_strip(temp_poly))
                temp_polygons_list[poly.material_index].append(bx_utils.quad_to_2_triangles(temp_poly)[0])
                temp_polygons_list[poly.material_index].append(bx_utils.quad_to_2_triangles(temp_poly)[1])
            else:
                return f"BXError: Unable to generate tristrip. Possibly due to an Ngon.\n(Polygon:{poly.index}, Vertex count:{len(poly.vertices)})"

        for polys in temp_polygons_list:
            polygons_by_material_list.append(polys)
    else:
        return f"No polygons or materials found."




    ### Vertices, Weights, Vertex Normals, Bones

    objVtxGrp = obj.vertex_groups # this is for all vertex groups in an object. for per-vertex use: b_mesh_data.vertices.groups

    for group in objVtxGrp:
        corresBone = b_skel_data.bones[group.name] # corresponding bone

        if bpy.context.scene.bx_gameChoice == 'SSX2':

            if corresBone.parent is not None:
                skelParent = corresBone.parent['Skeleton ID']
                boneParent = corresBone.parent['Bone Index']
            else:
                skelParent = -1 # root bone (hips) will have this
                boneParent = -1 # ^

            try:
                bone_list.append((
                    group.name, 
                    skelParent, #corresBone['Skeleton ID'],
                    boneParent, #corresBone['Bone Index'], 
                    corresBone['Unknown ID'],
                    corresBone['Unknown Bone ID'], # might be boneID 
                    bx_utils.bone_rel_loc(corresBone),
                    bx_utils.get_custom_vec(corresBone, 'a) Bone Rotation'),
                    bx_utils.get_custom_vec(corresBone, 'b) Bone Rotation1'),
                    bx_utils.get_custom_vec(corresBone, 'c) Bone Unknown'),
                    bx_utils.get_custom_vec(corresBone, 'd) Bone Unknown1')
                ))
            except:
                return f"BXError: Error on bone '{group.name}'.\n    Make sure bones have the correct custom properties set."




    if len(b_mesh_data.vertices) > 0: # Vertices, Weights and Vertex Normals

        for v in b_mesh_data.vertices:
            numGroups = len(v.groups)

            if numGroups > 3: 
                print(f"BXWarn: More than 3 weights on vertex {v.index}")
            #elif numGroups < 1: print(f"BXWarn: 0 weights on vertex {v.index}")

            temp_vGroup = []



            for j in range(numGroups):

                vGroup = v.groups[j]

                vGroupName = objVtxGrp[vGroup.group].name

                vGroupWeight = int(round(vGroup.weight*100)) # Weight Percentage

                if vGroupWeight > 0 and vGroupWeight < 90:
                    vGroupWeight = int(round(vGroupWeight+5.1, -1)) # round to next 10
                elif vGroupWeight > 90:
                    vGroupWeight = int(100)

                if bpy.context.scene.bx_gameChoice == 'SSX2':
                    try:
                        currentBone = b_skel_data.bones[f"{vGroupName}"]
    
                        vGroupIndex = currentBone['Bone Index'] # or vGroup.group
                        vGroupParent = currentBone['Skeleton ID']
                        
                        if vGroupWeight > 0:
                            temp_vGroup.append((vGroupWeight, vGroupIndex, vGroupParent)) # in game struct I have it as (weight, boneIndex, skelParentID)
                        else:
                            #print(f"Problem on Vertex {v.index}, Vertex Group {vGroup.group}, Bone {vGroupName}, Weight float {round(vGroup.weight, 3)}, Weight int {vGroupWeight}")
                            print(f"BXWarn: Weight of 0% on vertex {v.index}. Skipping.")
                            continue # skip to next loop
    
                    except:
                        print(f"BXError: Error on bone '{vGroupName}'.\n    Make sure bones have the correct custom properties set.")
                
                elif bpy.context.scene.bx_gameChoice == 'SSX3':
                   #currentBone = b_skel_data.bones[f"{vGroupName}"].name
                   
                   if vGroupWeight > 0:
                       temp_vGroup.append((vGroupWeight, vGroupName, None)) # in game struct I have it as (weight, boneIndex, skelParentID)
                   else:
                       #print(f"Problem on Vertex {v.index}, Vertex Group {vGroup.group}, Bone {vGroupName}, Weight float {round(vGroup.weight, 3)}, Weight int {vGroupWeight}")
                       print(f"BXWarn: Weight of 0% on vertex {v.index}. Skipping.")
                       continue # skip to next loop
                else:
                    return 'Sup'

            temp_vGroup.sort(key=lambda tempkey: tempkey[1]) # Sort the weights in order of boneID. tempkey refers to index of boneID inside temp_vGroup



            vtx = obj.matrix_world @ v.co # calculate world/global position


            if len(temp_vGroup) > 0:

                if temp_vGroup in weight_list: # check duplicates
                    vertex_list.append(((vtx.x, vtx.y, vtx.z), weight_list.index(temp_vGroup))) # i can also do v.co.xyz im p sure

                else:
                    weight_list.append(temp_vGroup)
                    vertex_list.append(((vtx.x, vtx.y, vtx.z), len(weight_list)-1)) # add vertex xyz and index of last item in weight list
            else:
                print(f"BXWarn: No weights assigned on vertex {v.index}.")
                #vertex_list.append(((vtx.x, vtx.y, vtx.z), 0))


            vertex_normal_list.append((v.normal.x, v.normal.y, v.normal.z)) # Vertex Normal


    out = dict(
        vertices = vertex_list,
        polygons_by_material = polygons_by_material_list,
        uvs = uv_list,
        vertex_normals = vertex_normal_list,
        tangent_normals = tangent_normal_list,
        weights = weight_list,
        bones = bone_list,
        materials = material_list
    )

    return out