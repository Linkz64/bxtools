import bpy
from bpy.utils import register_class, unregister_class

from ..general import bx_utils
from ..general.bx_utils import *
from ..general import blender_get_data
from ..external import msh_model_triangle_strips
from .ssx2_model_unpack import ssx2_get_mxf_data

import os
import struct


"""
vertices
tristrip_groups
uvs
vertex_normals
tangent_normals # Xbox mxf only
weights
bones
materials
"""

def ssx2_set_mxf_data():

    out_path = os.path.abspath(bpy.path.abspath(bpy.context.scene.ssx2_ModelPackPath))+'/'
    mdl_file = bpy.context.scene.ssx2_CustomModelFile.lower()
    collection = bpy.context.scene.ssx2_CustomModelCollec
    copy_bones = bpy.context.scene.ssx2_CopyBones
    copy_used = copy_bones # or copy_skel_id
    bone_override_loc = bpy.context.scene.ssx2_OverrideBoneLoc
    mxf_in_path = bpy.context.scene.ssx2_ModelUnpackPath#os.path.abspath(bpy.path.abspath(bpy.context.scene.ssx2_ModelUnpackPath))+'/'

    files_to_export = dict(
        body = [],
        head = [],
        board = []
    )
    objects_found = False
    if collection != None and len(collection.children) > 0:
        for collec in collection.children:
            if 'body' in collec.name or 'Body' in collec.name: # and 'board' not in mdl_file.lower()
                files_to_export['body'] = collec.all_objects
                if len(collec.all_objects) > 0:
                    objects_found = True
            elif 'head' in collec.name or 'Head' in collec.name:
                files_to_export['head'] = collec.all_objects
                if len(collec.all_objects) > 0:
                    objects_found = True
            elif 'board' in mdl_file and 'board' in collec.name: # maybe this should be first
                files_to_export['board'] = collec.all_objects
                if len(collec.all_objects) > 0:
                    objects_found = True
        if objects_found is False:
            return False, f"Model objects not found in subcollections."
    elif len(collection.children) == 0:
        return False, f"No subcollections."
    else:
        return print(f"BxError: No objects in export collection.")

    bytes_00 = b'\x00\x00\x00\x00'
    bytes_ff = b'\xFF\xFF\xFF\xFF'

    pad_seperator = True    # within model data
    num_pad_seperator_rows = 1 # extra padding rows
    pad_after_mdl_data = False  # after a whole model data
    pad_after_header_list = False

    use_temp_morphs = False
    use_temp_last_data = False
    use_temp_unknown_data = False

    threshold = 0.005 # threshold for getting used bone and getting weighted group

    all_skeletons = [[] for i in range(len(files_to_export))]
    all_used_bones = [[] for i in range(len(files_to_export))]
    for i, file_type in enumerate(files_to_export):
        if len(files_to_export[file_type]) > 0:

            for obj in files_to_export[file_type]:
                if obj.type == 'EMPTY' or 'shdw' in obj.name.lower():
                    continue
                skel = blender_get_data.get_skeleton(obj)
                all_skeletons[i].append(skel)
                if skel is not None:
                    #all_used_bones[i or obj.name] = get_bones...
                    all_used_bones[i].append(blender_get_data.get_bones_used(obj, skel=skel, sort_type='outliner', threshold=threshold))
                else:
                    return False, f"{obj.name} is not parented/assigned to an Armature."
            continue
        else:
            continue

    debug_stop = 0 # None or a number

    for i, file_type in enumerate(files_to_export):

        if len(files_to_export[file_type]) == 0:
            continue
        else:
            file = files_to_export[file_type]


        if copy_used and len(mxf_in_path) > 0:
            copy_path = mxf_in_path+mdl_file+'_'+file_type+'.mxf'
            print(copy_path)
            if os.path.exists(copy_path):
                original_mxf = ssx2_get_mxf_data(copy_path)
            else:
                return False, f"Copy failed. Original .mxf file not found.\nEnsure names are correct"

            original_model_names = []
            for og_mdl in original_mxf[0]:
                original_model_names.append(og_mdl['modelName'])

        elif copy_used and len(mxf_in_path) == 0:
            return False, f"Copy failed. Original model path is empty." # this is handled in the operator 




        len_file_header = 12 # custom file header length (12 or 16)

        len_headers = len_file_header + 396 * len(file) # file header + model headers
        len_headers_remainder = bx_utils.calc_padding_bytes(len_headers, 16) #-(len_headers % -16) # remainder bytes for 16 byte alignment


        buff_file_header = b''
        buff_file_header += b'\x04\x00\x00\x00'                              # Version maybe
        buff_file_header += struct.pack('h', len(file))                      # numModels
        buff_file_header += struct.pack('h', len_file_header)                  # offset to model header list
        buff_file_header += struct.pack('i', len_headers)#+len_headers_remainder) # offset to model data list
        #buff_file_header += bytes_ff



        buff_headers_list = b''
        buff_models_list = b''



        for j, obj in enumerate(file):

            # Model Name

            try:
                mdl_name = obj['Name']
            except:
                mdl_name = obj.name

            if copy_used:
                if mdl_name in original_model_names:
                    original_index = original_model_names.index(mdl_name)
                else:
                    print(f"'{mdl_name}' model not found in original .mxf file:\n{original_model_names}")
                    return None, f"'{mdl_name}' model not found in original .mxf file: {original_model_names}"
            


            print(f"Packing: {mdl_name:16} {obj.name:25}")

            try:
                skel_id = int(obj['Skeleton ID'])
            except:
                if 'Body' in mdl_name:
                    skel_id = 0
                elif 'Head' in mdl_name:
                    skel_id = 2
                elif 'Eyes' in mdl_name:
                    skel_id = 5
                elif 'Face' in mdl_name:
                    skel_id = 10
                elif 'Goggles30' in mdl_name:
                    skel_id = 6
                elif 'Goggles23' in mdl_name:
                    skel_id = 9
                elif 'Pack' in mdl_name:
                    skel_id = 12
                elif 'Hair' in mdl_name and 'psymon' in mdl_file:
                    skel_id = 4
                elif 'Hair' in mdl_name and 'luther' in mdl_file:
                    skel_id = 7
                elif 'Hair' in mdl_name and 'eddie' in mdl_file:
                    skel_id = 8
                elif 'Hair' in mdl_name and 'kaori' in mdl_file:
                    skel_id = 11
                elif 'Hair' in mdl_name and 'brodi' in mdl_file:
                    skel_id = 13
                elif 'Hair' in mdl_name and 'marisol' in mdl_file:
                    skel_id = 14
                elif 'Hair' in mdl_name and 'jp' in mdl_file:
                    skel_id = 15
                else:
                    print("Either model or file name does not match required format or custom property 'Skeleton ID' is not set.")





            if obj.type == 'EMPTY':
                buff_header = b'' # Model Header (For shadows)
                buff_header += bx_utils.pack_string(mdl_name, 16)  # model name
                buff_header += struct.pack('i', len(buff_models_list))#69420)
                buff_header += b'\x00'*80
                buff_header += bytes_ff
                buff_header += b'\x00'*286
                buff_header += struct.pack('h', skel_id)
                buff_header += bytes_00

                buff_headers_list += buff_header

                if debug_stop is not None and j == debug_stop:
                    return None, f"Skipped"
                else:
                    continue
                continue # skip to next loop


            
            ## Model

            off_model = len(buff_models_list)
            buff_model = b''

            #mdl_data = blender_get_data.get_mesh_data(obj=obj, skel=custom_skel_object)#bpy.data.objects[custom_skel_object])
            if len(obj.data.materials) > 0:
                polygons, materials = blender_get_data.get_polygons_by_material(obj, include_materials=True)
            else:
                return False, f"{obj.name} is missing materials."
            
            used_skel = all_skeletons[i][j]
            used_bones = all_used_bones[i][j]

            shape_keys, shape_keys_names = blender_get_data.get_shape_keys(obj, indexed=True, include_unused=True, include_names=True)
            vertices, weights = blender_get_data.get_vertices_and_weights(obj, threshold=threshold, used_bones=used_bones, skel=used_skel)
            if type(vertices) is not list:
                return vertices, weights
            uvs = blender_get_data.get_uvs(obj)
            vnormals = blender_get_data.get_vertex_normals(obj)
            tnormals = blender_get_data.get_tangent_normals(obj)
            


            off_materials = len(buff_model) # Materials
            num_materials = len(materials)

            buff_mats = b''

            for material in materials:
                mat = material.name

                if '_b' in mat:
                    slot2 = bx_utils.pack_string(mat[mat.index('_b')-2:mat.index('_b')+2], 4)
                    #bytes(mat[0]+mat[3], 'ascii') + b'_b'
                else:
                    slot2 = bytes(mat[0]+mat[3], 'ascii') + b'_b'
                if '_g' in mat:
                    slot3 = bx_utils.pack_string(mat[mat.index('_g')-2:mat.index('_g')+2], 4)
                    #bytes(mat[0]+mat[3], 'ascii') + b'_g'
                else:
                    slot3 = bytes(mat[0]+mat[3], 'ascii') + b'_g'
                if 'envr' in mat:
                    slot4 = b'envr'
                else:
                    slot4 = bytes_00

                buff_mats += bx_utils.pack_string(mat, 4) # slot0: main texture name
                buff_mats += bytes_00                     # slot1: unknown
                buff_mats += slot2                        # slot2: bump texture           '**_b'
                buff_mats += slot3                        # slot3: gloss texture          '**_g'
                buff_mats += slot4                        # slot4: environment reflection 'envr'
                buff_mats += bytes_00
                buff_mats += bytes_00
                buff_mats += bytes_00

            if file_type != 'board':
                bytes_00_x7 = bytes_00 * 7
    
                mats_placeholder = b'' # These extra materials are required to be included. Otherwise going into another heat in World Circuit freezes the game.
                if b'boot' not in buff_mats:
                    mats_placeholder += b'boot' + bytes_00_x7
                if b'suit' not in buff_mats:
                    mats_placeholder += b'suit' + bytes_00_x7
                if b'helm' not in buff_mats:
                    mats_placeholder += b'helm' + bytes_00_x7
                if b'head' not in buff_mats:
                    mats_placeholder += b'head' + bytes_00_x7
    
                num_materials += 4
    
                buff_model += buff_mats + mats_placeholder
            else:
                buff_model += buff_mats





            off_bones = len(buff_model) # Bones

            if mdl_name not in ['Face3000', 'Head3000', 'Head1500', 'Head750']:

                if copy_bones:
                    copied_bones = original_mxf[1][original_index]['bones']

                    num_bones = len(copied_bones)

                    buff_bones = b'' #b'\00' * 0x54 * len(mdl_data['bones'])

                    for j, bone in enumerate(copied_bones):
                        buff_bones += bx_utils.pack_string(bone['boneName'], 16) # bone name
                        buff_bones += struct.pack('h', bone['skelParentID'])
                        buff_bones += struct.pack('h', bone['boneParentID'])
                        buff_bones += struct.pack('h', bone['unknownID'])
                        buff_bones += struct.pack('h', bone['boneID'])

                        if bone_override_loc and bone['boneName'] in used_bones:
                            override_bone = used_skel.data.bones[used_bones[used_bones.index(bone['boneName'])]]
                            buff_bones += struct.pack('fff', *bone_rel_loc(override_bone))
                        else:
                            buff_bones += struct.pack('fff', *bone['boneLoc'])
                        buff_bones += struct.pack('fff', *bone['boneRot'])
                        buff_bones += struct.pack('fff', *bone['boneRot1'])
                        buff_bones += struct.pack('fff', *bone['boneUnk'])
                        buff_bones += struct.pack('fff', *bone['boneUnk1'])
                else:
                    num_bones = len(used_bones)

                    buff_bones = b'' #b'\00' * 0x54 * num_bones

                    for k, bone in enumerate(used_bones):
                        cur_bone = used_skel.data.bones[bone]

                        if cur_bone.parent is not None:
                            try:
                                bone_parent_skel = cur_bone.parent['Skeleton ID']
                                bone_parent_index = cur_bone.parent['Bone Index']
                            except:
                                return False, f"{cur_bone.parent.name} is missing custom properties."
                        else:
                            bone_parent_skel = -1
                            bone_parent_index = -1

                        try:
                            buff_bones += bx_utils.pack_string(bone, 16) # bone name
                            buff_bones += struct.pack('h', bone_parent_skel)
                            buff_bones += struct.pack('h', bone_parent_index)
                            buff_bones += struct.pack('h', cur_bone['Unknown ID'])
                            buff_bones += struct.pack('h', cur_bone['Unknown Bone ID'])
                            buff_bones += struct.pack('fff', *bone_rel_loc(cur_bone)) # location
                            buff_bones += struct.pack('fff', *get_custom_vec(cur_bone, 'a) Bone Rotation')) # rotation
                            buff_bones += struct.pack('fff', *get_custom_vec(cur_bone, 'b) Bone Rotation1')) # rotation1
                            buff_bones += struct.pack('fff', *get_custom_vec(cur_bone, 'c) Bone Unknown')) # unknown
                            buff_bones += struct.pack('fff', *get_custom_vec(cur_bone, 'd) Bone Unknown1')) # unknown1
                        except:
                            return False, f"{bone} is missing custom properties."
                buff_model += buff_bones
            else:
                num_bones = 0

            if pad_seperator:
                buff_model += bx_utils.padding_bytes(buff_model, num_rows=num_pad_seperator_rows) # Separator padding




            off_iks = len(buff_model) # IK points
            num_iks = 0
            if file_type == 'board' and len(obj.children) > 0:
                buff_iks = b''
                for c in obj.children:
                    if c.type == 'EMPTY':
                        buff_iks += struct.pack('fff', c.location)
                        num_iks += 1




            off_morphs = len(buff_model) # Morphs
            num_morphs = 0
            if mdl_name == "Face3000":

                if use_temp_morphs:
                    num_morphs = 23
                    num_affected_verts = 5
                    padding_after_morph_headers = bx_utils.calc_padding_bytes(8 * num_morphs + off_morphs, 16)
                    off_shapes = 8 * num_morphs + off_morphs + padding_after_morph_headers
                    temp_offsets = [off_shapes]
                    buff_morphs = b''
                    for k in range(num_morphs):
                        buff_morphs += struct.pack('i', num_affected_verts) # affected vertices count
                        buff_morphs += struct.pack('i', temp_offsets[-1]) # shape offset
                        off_shapes += num_affected_verts*16 # or is it *16
                        temp_offsets.append(off_shapes)
                    buff_morphs += b'\xFF'*padding_after_morph_headers # Padding
                    for k in range(num_morphs):
                        for l in range(num_affected_verts):
                            buff_morphs += struct.pack('fff', 0, 0, 0) # vertex translate (for adding with vertex xyz)
                            buff_morphs += struct.pack('h', k)   # vertex index
                            buff_morphs += struct.pack('b', 16)  # unknown
                            buff_morphs += struct.pack('b', 16)  # unknown
                else:
                    num_morphs = len(shape_keys)
                    padding_after_morph_headers = bx_utils.calc_padding_bytes(8 * num_morphs + off_morphs, 16)
                    off_shapes = 8 * num_morphs + off_morphs + padding_after_morph_headers
                    temp_offsets = [off_shapes]
                    buff_morphs = b''
                    for shape in shape_keys: # headers
                        buff_morphs += struct.pack('i', len(shape)) # affected vertices count
                        buff_morphs += struct.pack('i', temp_offsets[-1]) # shape offset
                        off_shapes += len(shape)*16
                        temp_offsets.append(off_shapes)
                    buff_morphs += b'\xFF'*padding_after_morph_headers # Padding
                    for shape in shape_keys:
                        for l in range(len(shape)):
                            buff_morphs += struct.pack('fff', *shape[k][0])
                            #print(shape[k][0])

                buff_model += buff_morphs

            if pad_seperator:
                buff_model += bx_utils.padding_bytes(buff_model, num_rows=num_pad_seperator_rows) # Separator padding




            off_skinning = len(buff_model) # Skinning (Weights)

            if len(weights) > 256: # The limit depends on both tristrips and weights but still it should be less.
                print("Skinning Count exceeded 256! Weights have to be optimized.")

            off_weights = 12 * len(weights) + off_skinning
            buff_skinning = b''

            for skin in weights:
                buff_skinning += struct.pack('i', len(skin))       # weight count
                buff_skinning += struct.pack('i', off_weights) # weight list offset
                buff_skinning += b'\x00\x00\x13\x00' # 0, 0, 19, 0
                off_weights += len(skin)*4

            for skin in weights:
                for weight in skin:
                    buff_skinning += struct.pack('h', int(weight[0])) # weight percentage
                    buff_skinning += struct.pack('b', weight[1])      # bone index
                    buff_skinning += struct.pack('b', weight[2])      # parent skeleton ID
            buff_model += buff_skinning

            if pad_seperator:
                buff_model += bx_utils.padding_bytes(buff_model, num_rows=num_pad_seperator_rows) # Separator padding




            off_tristrips = len(buff_model) # Triangle Strip Groups (grouped by material)

            tristrip_groups = []
            for k in range(len(polygons)):
                
                new_strips = msh_model_triangle_strips.create_triangle_strips(polygons[k])
                tristrip_groups.append(bx_utils.stitch_tristrips(new_strips))

            off_strips = 16 * len(tristrip_groups) + off_tristrips

            temp_offsets = [off_strips]

            buff_tristrips = b''

            for k, strip in enumerate(tristrip_groups): # strip headers
                buff_tristrips += struct.pack('i', temp_offsets[-1])
                buff_tristrips += struct.pack('h', len(strip))
                buff_tristrips += struct.pack('h', k)
                buff_tristrips += struct.pack('h', k)
                buff_tristrips += struct.pack('h', k) # _b bump map texture index
                buff_tristrips += struct.pack('h', k) # _g gloss/specular texture index
                buff_tristrips += struct.pack('h', k)

                off_strips += len(strip)*2 + 2 # adding 2 to allow space for FFFF
                temp_offsets.append(off_strips)

            for strip in tristrip_groups: # indices
                for k, idx in enumerate(strip):
                    buff_tristrips += struct.pack('h', idx)

                    if k == len(strip) - 1:
                        buff_tristrips += b'\xFF\xFF'

            buff_model += buff_tristrips

            buff_model += bx_utils.padding_bytes(buff_model, num_rows=num_pad_seperator_rows) # Separator padding




            off_vertices = len(buff_model) # Vertex Data (Vertices, UVs, etc)

            buff_vertex_data = b''

            for k, vtx in enumerate(vertices):
                buff_vertex_data += struct.pack('fff', *vtx[0]) # Vertex
                buff_vertex_data += struct.pack('f', 1.0)
                buff_vertex_data += struct.pack('fff', *vnormals[k]) # Vertex normal?
                buff_vertex_data += struct.pack('f', 0.0)
                buff_vertex_data += struct.pack('fff', *tnormals[k]) # Tangent normal?
                buff_vertex_data += struct.pack('f', 1.0)
                buff_vertex_data += struct.pack('ff', *uvs[k]) # UV
                buff_vertex_data += bytes_ff # FFFFFFFF
                buff_vertex_data += struct.pack('i', vtx[1]) # Skinning index

            buff_model += buff_vertex_data
            buff_model += buff_vertex_data # yes there's a duplicate of vertex block in mxf


            


            off_last_data = len(buff_model)    # Last Data
            num_last_data = 0
            num_unk0 = 0 # idk if this is related but im leaving it here
            # if use_temp_last_data:
            #     buff_last_data = b'\x00\x00\x10\x00 \x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x04\x00\x00\x00\x10\x000\x00 \x00\x10\x00\x06\x00\x00\x00\x08\x00\x00\x00\x03\x00\x00\x00 \x000\x00@\x00 \x00\t\x00\x00\x00\n\x00\x00\x00\x0c\x00\x00\x000\x00P\x00@\x000\x00\x0e\x00\x00\x00\x10\x00\x00\x00\x0b\x00\x00\x00@\x00P\x00`\x00@\x00\x11\x00\x00\x00\x12\x00\x00\x00\x14\x00\x00\x00P\x00p\x00`\x00P\x00\x16\x00\x00\x00\x18\x00\x00\x00\x13\x00\x00\x00P\x00\x80\x00p\x00P\x00\x1a\x00\x00\x00\x1c\x00\x00\x00\x17\x00\x00\x00\x80\x00\x90\x00p\x00\x80\x00\x1e\x00\x00\x00 \x00\x00\x00\x1d\x00\x00\x00p\x00\x90\x00\xa0\x00p\x00!\x00\x00\x00"\x00\x00\x00$\x00\x00\x00\x90\x00\xb0\x00\xa0\x00\x90\x00&\x00\x00\x00(\x00\x00\x00#\x00\x00\x00\xa0\x00\xb0\x00\xc0\x00\xa0\x00)\x00\x00\x00*\x00\x00\x00,\x00\x00\x00\xb0\x00\xd0\x00\xc0\x00\xb0\x00.\x00\x00\x000\x00\x00\x00+\x00\x00\x00\xb0\x00\xe0\x00\xd0\x00\xb0\x002\x00\x00\x004\x00\x00\x00/\x00\x00\x00\xe0\x00\xf0\x00\xd0\x00\xe0\x006\x00\x00\x008\x00\x00\x005\x00\x00\x00\xe0\x00\x00\x01\xf0\x00\xe0\x00:\x00\x00\x00<\x00\x00\x007\x00\x00\x00\x00\x01\x10\x01\xf0\x00\x00\x01>\x00\x00\x00@\x00\x00\x00=\x00\x00\x00\xf0\x00\x10\x01 \x01\xf0\x00A\x00\x00\x00B\x00\x00\x00D\x00\x00\x00\x10\x010\x01 \x01\x10\x01F\x00\x00\x00H\x00\x00\x00C\x00\x00\x00 \x010\x01@\x01 \x01I\x00\x00\x00J\x00\x00\x00L\x00\x00\x000\x01P\x01@\x010\x01N\x00\x00\x00P\x00\x00\x00K\x00\x00\x000\x01`\x01P\x010\x01R\x00\x00\x00T\x00\x00\x00O\x00\x00\x00P\x01`\x01p\x01P\x01U\x00\x00\x00V\x00\x00\x00X\x00\x00\x00`\x01\x80\x01p\x01`\x01Z\x00\x00\x00\\\x00\x00\x00W\x00\x00\x00p\x01\x80\x01\x90\x01p\x01]\x00\x00\x00^\x00\x00\x00`\x00\x00\x00\xa0\x01\xc0\x01\xb0\x01\xa0\x01b\x00\x00\x00d\x00\x00\x00f\x00\x00\x00\xb0\x01\xc0\x01\xd0\x01\xb0\x01e\x00\x00\x00h\x00\x00\x00j\x00\x00\x00\xc0\x01\xe0\x01\xd0\x01\xc0\x01l\x00\x00\x00n\x00\x00\x00i\x00\x00\x00\xd0\x01\xe0\x01\x90\x01\xd0\x01o\x00\x00\x00p\x00\x00\x00r\x00\x00\x00\xe0\x01\xf0\x01\x90\x01\xe0\x01t\x00\x00\x00v\x00\x00\x00q\x00\x00\x00\x90\x01\xf0\x01p\x01\x90\x01w\x00\x00\x00x\x00\x00\x00a\x00\x00\x00\x00\x02 \x02\x10\x02\x00\x02z\x00\x00\x00|\x00\x00\x00~\x00\x00\x00\x10\x02 \x020\x02\x10\x02}\x00\x00\x00\x80\x00\x00\x00\x82\x00\x00\x00 \x02@\x020\x02 \x02\x84\x00\x00\x00\x86\x00\x00\x00\x81\x00\x00\x000\x02@\x02P\x020\x02\x87\x00\x00\x00\x88\x00\x00\x00\x8a\x00\x00\x00@\x02`\x02P\x02@\x02\x8c\x00\x00\x00\x8e\x00\x00\x00\x89\x00\x00\x00P\x02`\x02p\x02P\x02\x8f\x00\x00\x00\x90\x00\x00\x00\x92\x00\x00\x00`\x02\x80\x02p\x02`\x02\x94\x00\x00\x00\x96\x00\x00\x00\x91\x00\x00\x00p\x02\x80\x02\x90\x02p\x02\x97\x00\x00\x00\x98\x00\x00\x00\x9a\x00\x00\x00\x80\x02\xa0\x02\x90\x02\x80\x02\x9c\x00\x00\x00\x9e\x00\x00\x00\x99\x00\x00\x00\x90\x02\xa0\x02\xb0\x02\x90\x02\x9f\x00\x00\x00\xa0\x00\x00\x00\xa2\x00\x00\x00\xa0\x02\xc0\x02\xb0\x02\xa0\x02\xa4\x00\x00\x00\xa6\x00\x00\x00\xa1\x00\x00\x00\xb0\x02\xc0\x02\xd0\x02\xb0\x02\xa7\x00\x00\x00\xa8\x00\x00\x00\xaa\x00\x00\x00\xc0\x02\xe0\x02\xd0\x02\xc0\x02\xac\x00\x00\x00\xae\x00\x00\x00\xa9\x00\x00\x00\xd0\x02\xe0\x02\xf0\x02\xd0\x02\xaf\x00\x00\x00\xb0\x00\x00\x00\xb2\x00\x00\x00\xe0\x02\x00\x03\xf0\x02\xe0\x02\xb4\x00\x00\x00\xb6\x00\x00\x00\xb1\x00\x00\x00\x10\x020\x02\x10\x03\x10\x02\x83\x00\x00\x00\xb8\x00\x00\x00\xba\x00\x00\x000\x02 \x03\x10\x030\x02\xbc\x00\x00\x00\xbe\x00\x00\x00\xb9\x00\x00\x00\x10\x03 \x030\x03\x10\x03\xbf\x00\x00\x00\xc0\x00\x00\x00\xc2\x00\x00\x00\x10\x030\x03@\x03\x10\x03\xc3\x00\x00\x00\xc4\x00\x00\x00\xc6\x00\x00\x00@\x030\x03P\x03@\x03\xc5\x00\x00\x00\xc8\x00\x00\x00\xca\x00\x00\x000\x03`\x03P\x030\x03\xcc\x00\x00\x00\xce\x00\x00\x00\xc9\x00\x00\x00P\x03`\x03p\x03P\x03\xcf\x00\x00\x00\xd0\x00\x00\x00\xd2\x00\x00\x00`\x03\x80\x03p\x03`\x03\xd4\x00\x00\x00\xd6\x00\x00\x00\xd1\x00\x00\x00p\x03\x80\x03\x90\x03p\x03\xd7\x00\x00\x00\xd8\x00\x00\x00\xda\x00\x00\x00p\x03\x90\x03\xa0\x03p\x03\xdb\x00\x00\x00\xdc\x00\x00\x00\xde\x00\x00\x00\xa0\x03\x90\x03\xb0\x03\xa0\x03\xdd\x00\x00\x00\xe0\x00\x00\x00\xe2\x00\x00\x00\xa0\x03\xb0\x03\xc0\x03\xa0\x03\xe3\x00\x00\x00\xe4\x00\x00\x00\xe6\x00\x00\x00\xc0\x03\xb0\x03\xd0\x03\xc0\x03\xe5\x00\x00\x00\xe8\x00\x00\x00\xea\x00\x00\x00\xb0\x03\xe0\x03\xd0\x03\xb0\x03\xec\x00\x00\x00\xee\x00\x00\x00\xe9\x00\x00\x00\xd0\x03\xe0\x03\xf0\x03\xd0\x03\xef\x00\x00\x00\xf0\x00\x00\x00\xf2\x00\x00\x00\xf0\x03\x00\x04\xd0\x03\xf0\x03\xf4\x00\x00\x00\xf6\x00\x00\x00\xf3\x00\x00\x00\x10\x04\x00\x04 \x04\x10\x04\xf8\x00\x00\x00\xfa\x00\x00\x00\xfc\x00\x00\x00\x00\x04\xf0\x03 \x04\x00\x04\xf5\x00\x00\x00\xfe\x00\x00\x00\xfb\x00\x00\x00 \x04\xf0\x030\x04 \x04\xff\x00\x00\x00\x00\x01\x00\x00\x02\x01\x00\x00\xf0\x03@\x040\x04\xf0\x03\x04\x01\x00\x00\x06\x01\x00\x00\x01\x01\x00\x000\x04@\x04P\x040\x04\x07\x01\x00\x00\x08\x01\x00\x00\n\x01\x00\x00@\x04`\x04P\x04@\x04\x0c\x01\x00\x00\x0e\x01\x00\x00\t\x01\x00\x00P\x04`\x04p\x04P\x04\x0f\x01\x00\x00\x10\x01\x00\x00\x12\x01\x00\x00`\x04\x80\x04p\x04`\x04\x14\x01\x00\x00\x16\x01\x00\x00\x11\x01\x00\x00p\x04\x80\x04\x90\x04p\x04\x17\x01\x00\x00\x18\x01\x00\x00\x1a\x01\x00\x00\x80\x04\xa0\x04\x90\x04\x80\x04\x1c\x01\x00\x00\x1e\x01\x00\x00\x19\x01\x00\x00\x90\x04\xa0\x04\xb0\x04\x90\x04\x1f\x01\x00\x00 \x01\x00\x00"\x01\x00\x00\xa0\x04\x00\x03\xb0\x04\xa0\x04$\x01\x00\x00&\x01\x00\x00!\x01\x00\x00\xb0\x04\x00\x03\xe0\x02\xb0\x04\'\x01\x00\x00\xb5\x00\x00\x00(\x01\x00\x00 \x04\xc0\x04\x10\x04 \x04*\x01\x00\x00,\x01\x00\x00\xfd\x00\x00\x00\x10\x04\xc0\x04\xd0\x04\x10\x04-\x01\x00\x00.\x01\x00\x000\x01\x00\x00\xc0\x04\xe0\x04\xd0\x04\xc0\x042\x01\x00\x004\x01\x00\x00/\x01\x00\x00\xd0\x04\xe0\x04\xf0\x04\xd0\x045\x01\x00\x006\x01\x00\x008\x01\x00\x00\xe0\x04\x00\x05\xf0\x04\xe0\x04:\x01\x00\x00<\x01\x00\x007\x01\x00\x00\x00\x05\x10\x05\xf0\x04\x00\x05>\x01\x00\x00@\x01\x00\x00=\x01\x00\x00\xf0\x04\x10\x05 \x05\xf0\x04A\x01\x00\x00B\x01\x00\x00D\x01\x00\x00\x10\x050\x05 \x05\x10\x05F\x01\x00\x00H\x01\x00\x00C\x01\x00\x00 \x050\x05@\x05 \x05I\x01\x00\x00J\x01\x00\x00L\x01\x00\x00@\x05P\x05 \x05@\x05N\x01\x00\x00P\x01\x00\x00M\x01\x00\x00`\x05p\x05@\x05`\x05R\x01\x00\x00T\x01\x00\x00V\x01\x00\x00@\x05p\x05P\x05@\x05U\x01\x00\x00X\x01\x00\x00O\x01\x00\x00\x80\x05p\x05\x90\x05\x80\x05Z\x01\x00\x00\\\x01\x00\x00^\x01\x00\x00\x90\x05p\x05`\x05\x90\x05]\x01\x00\x00S\x01\x00\x00`\x01\x00\x00\xa0\x05\xb0\x05\x90\x05\xa0\x05b\x01\x00\x00d\x01\x00\x00f\x01\x00\x00\x90\x05\xb0\x05\x80\x05\x90\x05e\x01\x00\x00h\x01\x00\x00_\x01\x00\x00\xc0\x05\xb0\x05\xd0\x05\xc0\x05j\x01\x00\x00l\x01\x00\x00n\x01\x00\x00\xd0\x05\xb0\x05\xa0\x05\xd0\x05m\x01\x00\x00c\x01\x00\x00p\x01\x00\x00\xd0\x05\xe0\x05\xc0\x05\xd0\x05r\x01\x00\x00t\x01\x00\x00o\x01\x00\x00\xe0\x05\xf0\x05\xc0\x05\xe0\x05v\x01\x00\x00x\x01\x00\x00u\x01\x00\x00\xc0\x05\xf0\x05\x00\x06\xc0\x05y\x01\x00\x00z\x01\x00\x00|\x01\x00\x00\xf0\x05\x10\x06\x00\x06\xf0\x05~\x01\x00\x00\x80\x01\x00\x00{\x01\x00\x00\x00\x06\x10\x06\x00\x02\x00\x06\x81\x01\x00\x00\x82\x01\x00\x00\x84\x01\x00\x00\x10\x06 \x02\x00\x02\x10\x06\x86\x01\x00\x00{\x00\x00\x00\x83\x01\x00\x00 \x06@\x060\x06 \x06\x88\x01\x00\x00\x8a\x01\x00\x00\x8c\x01\x00\x000\x06@\x06P\x060\x06\x8b\x01\x00\x00\x8e\x01\x00\x00\x90\x01\x00\x00@\x06`\x06P\x06@\x06\x92\x01\x00\x00\x94\x01\x00\x00\x8f\x01\x00\x00P\x06`\x06p\x06P\x06\x95\x01\x00\x00\x96\x01\x00\x00\x98\x01\x00\x00`\x06\x80\x06p\x06`\x06\x9a\x01\x00\x00\x9c\x01\x00\x00\x97\x01\x00\x00p\x06\x80\x06\x90\x06p\x06\x9d\x01\x00\x00\x9e\x01\x00\x00\xa0\x01\x00\x00\x80\x06\xa0\x06\x90\x06\x80\x06\xa2\x01\x00\x00\xa4\x01\x00\x00\x9f\x01\x00\x00\x90\x06\xa0\x06\xb0\x06\x90\x06\xa5\x01\x00\x00\xa6\x01\x00\x00\xa8\x01\x00\x00\xa0\x06\xc0\x06\xb0\x06\xa0\x06\xaa\x01\x00\x00\xac\x01\x00\x00\xa7\x01\x00\x00@\x06 \x06\xd0\x06@\x06\x89\x01\x00\x00\xae\x01\x00\x00\xb0\x01\x00\x00 \x06\xe0\x06\xd0\x06 \x06\xb2\x01\x00\x00\xb4\x01\x00\x00\xaf\x01\x00\x00\xd0\x06\xe0\x06\xf0\x06\xd0\x06\xb5\x01\x00\x00\xb6\x01\x00\x00\xb8\x01\x00\x00\xe0\x06\x00\x07\xf0\x06\xe0\x06\xba\x01\x00\x00\xbc\x01\x00\x00\xb7\x01\x00\x00\xf0\x06\x00\x07\x10\x07\xf0\x06\xbd\x01\x00\x00\xbe\x01\x00\x00\xc0\x01\x00\x00\x00\x07 \x07\x10\x07\x00\x07\xc2\x01\x00\x00\xc4\x01\x00\x00\xbf\x01\x00\x00\x10\x07 \x070\x07\x10\x07\xc5\x01\x00\x00\xc6\x01\x00\x00\xc8\x01\x00\x00@\x07P\x07`\x07@\x07\xca\x01\x00\x00\xcc\x01\x00\x00\xce\x01\x00\x00p\x07\x80\x07@\x07p\x07\xd0\x01\x00\x00\xd2\x01\x00\x00\xd4\x01\x00\x00\x80\x07P\x07@\x07\x80\x07\xd6\x01\x00\x00\xcb\x01\x00\x00\xd3\x01\x00\x00p\x07\x90\x07\x80\x07p\x07\xd8\x01\x00\x00\xda\x01\x00\x00\xd1\x01\x00\x00\x90\x07\xa0\x07\x80\x07\x90\x07\xdc\x01\x00\x00\xde\x01\x00\x00\xdb\x01\x00\x00\x80\x07\xa0\x07\xb0\x07\x80\x07\xdf\x01\x00\x00\xe0\x01\x00\x00\xe2\x01\x00\x00\xa0\x07\xc0\x07\xb0\x07\xa0\x07\xe4\x01\x00\x00\xe6\x01\x00\x00\xe1\x01\x00\x00\xb0\x07\xc0\x07\xd0\x07\xb0\x07\xe7\x01\x00\x00\xe8\x01\x00\x00\xea\x01\x00\x00\xc0\x07\xe0\x07\xd0\x07\xc0\x07\xec\x01\x00\x00\xee\x01\x00\x00\xe9\x01\x00\x00\xe0\x07\xf0\x07\xd0\x07\xe0\x07\xf0\x01\x00\x00\xf2\x01\x00\x00\xef\x01\x00\x00\xd0\x07\xf0\x07\x00\x08\xd0\x07\xf3\x01\x00\x00\xf4\x01\x00\x00\xf6\x01\x00\x00\xf0\x07\x10\x08\x00\x08\xf0\x07\xf8\x01\x00\x00\xfa\x01\x00\x00\xf5\x01\x00\x00\x00\x08\x10\x08 \x08\x00\x08\xfb\x01\x00\x00\xfc\x01\x00\x00\xfe\x01\x00\x00\x10\x080\x08 \x08\x10\x08\x00\x02\x00\x00\x02\x02\x00\x00\xfd\x01\x00\x00 \x080\x08@\x08 \x08\x03\x02\x00\x00\x04\x02\x00\x00\x06\x02\x00\x00P\x08`\x08p\x08P\x08\x08\x02\x00\x00\n\x02\x00\x00\x0c\x02\x00\x00`\x08 \x08p\x08`\x08\x0e\x02\x00\x00\x10\x02\x00\x00\x0b\x02\x00\x00p\x08 \x08@\x08p\x08\x11\x02\x00\x00\x07\x02\x00\x00\x12\x02\x00\x00'
            #     num_last_data = 132
            #     num_unk0 = 136
            #     buff_model += buff_last_data


            off_unknown_data = len(buff_model) # Unknown Data
            num_unknown_data = 0
            # if use_temp_unknown_data:
            #     buff_unknown_data = b'\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x10\x00 \x00\x10\x00\x00\x00 \x00\x00\x00 \x00\x00\x00\x10\x000\x00\x10\x00\x00\x000\x00 \x000\x00\x00\x000\x00@\x000\x00\x00\x00@\x00 \x00@\x00\x00\x000\x00P\x000\x00\x00\x00P\x00@\x00P\x00\x00\x00P\x00`\x00P\x00\x00\x00`\x00@\x00`\x00\x00\x00P\x00p\x00P\x00\x00\x00p\x00`\x00p\x00\x00\x00P\x00\x80\x00P\x00\x00\x00\x80\x00p\x00\x80\x00\x00\x00\x80\x00\x90\x00\x80\x00\x00\x00\x90\x00p\x00\x90\x00\x00\x00\x90\x00\xa0\x00\x90\x00\x00\x00\xa0\x00p\x00\xa0\x00\x00\x00\x90\x00\xb0\x00\x90\x00\x00\x00\xb0\x00\xa0\x00\xb0\x00\x00\x00\xb0\x00\xc0\x00\xb0\x00\x00\x00\xc0\x00\xa0\x00\xc0\x00\x00\x00\xb0\x00\xd0\x00\xb0\x00\x00\x00\xd0\x00\xc0\x00\xd0\x00\x00\x00\xb0\x00\xe0\x00\xb0\x00\x00\x00\xe0\x00\xd0\x00\xe0\x00\x00\x00\xe0\x00\xf0\x00\xe0\x00\x00\x00\xf0\x00\xd0\x00\xf0\x00\x00\x00\xe0\x00\x00\x01\xe0\x00\x00\x00\x00\x01\xf0\x00\x00\x01\x00\x00\x00\x01\x10\x01\x00\x01\x00\x00\x10\x01\xf0\x00\x10\x01\x00\x00\x10\x01 \x01\x10\x01\x00\x00 \x01\xf0\x00 \x01\x00\x00\x10\x010\x01\x10\x01\x00\x000\x01 \x010\x01\x00\x000\x01@\x010\x01\x00\x00@\x01 \x01@\x01\x00\x000\x01P\x010\x01\x00\x00P\x01@\x01P\x01\x00\x000\x01`\x010\x01\x00\x00`\x01P\x01`\x01\x00\x00`\x01p\x01`\x01\x00\x00p\x01P\x01p\x01\x00\x00`\x01\x80\x01`\x01\x00\x00\x80\x01p\x01\x80\x01\x00\x00\x80\x01\x90\x01\x80\x01\x00\x00\x90\x01p\x01\x90\x01\x00\x00\xa0\x01\xc0\x01\xa0\x01\x00\x00\xc0\x01\xb0\x01\xc0\x01\x00\x00\xb0\x01\xa0\x01\xb0\x01\x00\x00\xc0\x01\xd0\x01\xc0\x01\x00\x00\xd0\x01\xb0\x01\xd0\x01\x00\x00\xc0\x01\xe0\x01\xc0\x01\x00\x00\xe0\x01\xd0\x01\xe0\x01\x00\x00\xe0\x01\x90\x01\xe0\x01\x00\x00\x90\x01\xd0\x01\x90\x01\x00\x00\xe0\x01\xf0\x01\xe0\x01\x00\x00\xf0\x01\x90\x01\xf0\x01\x00\x00\xf0\x01p\x01\xf0\x01\x00\x00\x00\x02 \x02\x00\x02\x00\x00 \x02\x10\x02 \x02\x00\x00\x10\x02\x00\x02\x10\x02\x00\x00 \x020\x02 \x02\x00\x000\x02\x10\x020\x02\x00\x00 \x02@\x02 \x02\x00\x00@\x020\x02@\x02\x00\x00@\x02P\x02@\x02\x00\x00P\x020\x02P\x02\x00\x00@\x02`\x02@\x02\x00\x00`\x02P\x02`\x02\x00\x00`\x02p\x02`\x02\x00\x00p\x02P\x02p\x02\x00\x00`\x02\x80\x02`\x02\x00\x00\x80\x02p\x02\x80\x02\x00\x00\x80\x02\x90\x02\x80\x02\x00\x00\x90\x02p\x02\x90\x02\x00\x00\x80\x02\xa0\x02\x80\x02\x00\x00\xa0\x02\x90\x02\xa0\x02\x00\x00\xa0\x02\xb0\x02\xa0\x02\x00\x00\xb0\x02\x90\x02\xb0\x02\x00\x00\xa0\x02\xc0\x02\xa0\x02\x00\x00\xc0\x02\xb0\x02\xc0\x02\x00\x00\xc0\x02\xd0\x02\xc0\x02\x00\x00\xd0\x02\xb0\x02\xd0\x02\x00\x00\xc0\x02\xe0\x02\xc0\x02\x00\x00\xe0\x02\xd0\x02\xe0\x02\x00\x00\xe0\x02\xf0\x02\xe0\x02\x00\x00\xf0\x02\xd0\x02\xf0\x02\x00\x00\xe0\x02\x00\x03\xe0\x02\x00\x00\x00\x03\xf0\x02\x00\x03\x00\x000\x02\x10\x030\x02\x00\x00\x10\x03\x10\x02\x10\x03\x00\x000\x02 \x030\x02\x00\x00 \x03\x10\x03 \x03\x00\x00 \x030\x03 \x03\x00\x000\x03\x10\x030\x03\x00\x000\x03@\x030\x03\x00\x00@\x03\x10\x03@\x03\x00\x000\x03P\x030\x03\x00\x00P\x03@\x03P\x03\x00\x000\x03`\x030\x03\x00\x00`\x03P\x03`\x03\x00\x00`\x03p\x03`\x03\x00\x00p\x03P\x03p\x03\x00\x00`\x03\x80\x03`\x03\x00\x00\x80\x03p\x03\x80\x03\x00\x00\x80\x03\x90\x03\x80\x03\x00\x00\x90\x03p\x03\x90\x03\x00\x00\x90\x03\xa0\x03\x90\x03\x00\x00\xa0\x03p\x03\xa0\x03\x00\x00\x90\x03\xb0\x03\x90\x03\x00\x00\xb0\x03\xa0\x03\xb0\x03\x00\x00\xb0\x03\xc0\x03\xb0\x03\x00\x00\xc0\x03\xa0\x03\xc0\x03\x00\x00\xb0\x03\xd0\x03\xb0\x03\x00\x00\xd0\x03\xc0\x03\xd0\x03\x00\x00\xb0\x03\xe0\x03\xb0\x03\x00\x00\xe0\x03\xd0\x03\xe0\x03\x00\x00\xe0\x03\xf0\x03\xe0\x03\x00\x00\xf0\x03\xd0\x03\xf0\x03\x00\x00\xf0\x03\x00\x04\xf0\x03\x00\x00\x00\x04\xd0\x03\x00\x04\x00\x00\x10\x04\x00\x04\x10\x04\x00\x00\x00\x04 \x04\x00\x04\x00\x00 \x04\x10\x04 \x04\x00\x00\xf0\x03 \x04\xf0\x03\x00\x00\xf0\x030\x04\xf0\x03\x00\x000\x04 \x040\x04\x00\x00\xf0\x03@\x04\xf0\x03\x00\x00@\x040\x04@\x04\x00\x00@\x04P\x04@\x04\x00\x00P\x040\x04P\x04\x00\x00@\x04`\x04@\x04\x00\x00`\x04P\x04`\x04\x00\x00`\x04p\x04`\x04\x00\x00p\x04P\x04p\x04\x00\x00`\x04\x80\x04`\x04\x00\x00\x80\x04p\x04\x80\x04\x00\x00\x80\x04\x90\x04\x80\x04\x00\x00\x90\x04p\x04\x90\x04\x00\x00\x80\x04\xa0\x04\x80\x04\x00\x00\xa0\x04\x90\x04\xa0\x04\x00\x00\xa0\x04\xb0\x04\xa0\x04\x00\x00\xb0\x04\x90\x04\xb0\x04\x00\x00\xa0\x04\x00\x03\xa0\x04\x00\x00\x00\x03\xb0\x04\x00\x03\x00\x00\xe0\x02\xb0\x04\xe0\x02\x00\x00 \x04\xc0\x04 \x04\x00\x00\xc0\x04\x10\x04\xc0\x04\x00\x00\xc0\x04\xd0\x04\xc0\x04\x00\x00\xd0\x04\x10\x04\xd0\x04\x00\x00\xc0\x04\xe0\x04\xc0\x04\x00\x00\xe0\x04\xd0\x04\xe0\x04\x00\x00\xe0\x04\xf0\x04\xe0\x04\x00\x00\xf0\x04\xd0\x04\xf0\x04\x00\x00\xe0\x04\x00\x05\xe0\x04\x00\x00\x00\x05\xf0\x04\x00\x05\x00\x00\x00\x05\x10\x05\x00\x05\x00\x00\x10\x05\xf0\x04\x10\x05\x00\x00\x10\x05 \x05\x10\x05\x00\x00 \x05\xf0\x04 \x05\x00\x00\x10\x050\x05\x10\x05\x00\x000\x05 \x050\x05\x00\x000\x05@\x050\x05\x00\x00@\x05 \x05@\x05\x00\x00@\x05P\x05@\x05\x00\x00P\x05 \x05P\x05\x00\x00`\x05p\x05`\x05\x00\x00p\x05@\x05p\x05\x00\x00@\x05`\x05@\x05\x00\x00p\x05P\x05p\x05\x00\x00\x80\x05p\x05\x80\x05\x00\x00p\x05\x90\x05p\x05\x00\x00\x90\x05\x80\x05\x90\x05\x00\x00`\x05\x90\x05`\x05\x00\x00\xa0\x05\xb0\x05\xa0\x05\x00\x00\xb0\x05\x90\x05\xb0\x05\x00\x00\x90\x05\xa0\x05\x90\x05\x00\x00\xb0\x05\x80\x05\xb0\x05\x00\x00\xc0\x05\xb0\x05\xc0\x05\x00\x00\xb0\x05\xd0\x05\xb0\x05\x00\x00\xd0\x05\xc0\x05\xd0\x05\x00\x00\xa0\x05\xd0\x05\xa0\x05\x00\x00\xd0\x05\xe0\x05\xd0\x05\x00\x00\xe0\x05\xc0\x05\xe0\x05\x00\x00\xe0\x05\xf0\x05\xe0\x05\x00\x00\xf0\x05\xc0\x05\xf0\x05\x00\x00\xf0\x05\x00\x06\xf0\x05\x00\x00\x00\x06\xc0\x05\x00\x06\x00\x00\xf0\x05\x10\x06\xf0\x05\x00\x00\x10\x06\x00\x06\x10\x06\x00\x00\x10\x06\x00\x02\x10\x06\x00\x00\x00\x02\x00\x06\x00\x02\x00\x00\x10\x06 \x02\x10\x06\x00\x00 \x06@\x06 \x06\x00\x00@\x060\x06@\x06\x00\x000\x06 \x060\x06\x00\x00@\x06P\x06@\x06\x00\x00P\x060\x06P\x06\x00\x00@\x06`\x06@\x06\x00\x00`\x06P\x06`\x06\x00\x00`\x06p\x06`\x06\x00\x00p\x06P\x06p\x06\x00\x00`\x06\x80\x06`\x06\x00\x00\x80\x06p\x06\x80\x06\x00\x00\x80\x06\x90\x06\x80\x06\x00\x00\x90\x06p\x06\x90\x06\x00\x00\x80\x06\xa0\x06\x80\x06\x00\x00\xa0\x06\x90\x06\xa0\x06\x00\x00\xa0\x06\xb0\x06\xa0\x06\x00\x00\xb0\x06\x90\x06\xb0\x06\x00\x00\xa0\x06\xc0\x06\xa0\x06\x00\x00\xc0\x06\xb0\x06\xc0\x06\x00\x00 \x06\xd0\x06 \x06\x00\x00\xd0\x06@\x06\xd0\x06\x00\x00 \x06\xe0\x06 \x06\x00\x00\xe0\x06\xd0\x06\xe0\x06\x00\x00\xe0\x06\xf0\x06\xe0\x06\x00\x00\xf0\x06\xd0\x06\xf0\x06\x00\x00\xe0\x06\x00\x07\xe0\x06\x00\x00\x00\x07\xf0\x06\x00\x07\x00\x00\x00\x07\x10\x07\x00\x07\x00\x00\x10\x07\xf0\x06\x10\x07\x00\x00\x00\x07 \x07\x00\x07\x00\x00 \x07\x10\x07 \x07\x00\x00 \x070\x07 \x07\x00\x000\x07\x10\x070\x07\x00\x00@\x07P\x07@\x07\x00\x00P\x07`\x07P\x07\x00\x00`\x07@\x07`\x07\x00\x00p\x07\x80\x07p\x07\x00\x00\x80\x07@\x07\x80\x07\x00\x00@\x07p\x07@\x07\x00\x00\x80\x07P\x07\x80\x07\x00\x00p\x07\x90\x07p\x07\x00\x00\x90\x07\x80\x07\x90\x07\x00\x00\x90\x07\xa0\x07\x90\x07\x00\x00\xa0\x07\x80\x07\xa0\x07\x00\x00\xa0\x07\xb0\x07\xa0\x07\x00\x00\xb0\x07\x80\x07\xb0\x07\x00\x00\xa0\x07\xc0\x07\xa0\x07\x00\x00\xc0\x07\xb0\x07\xc0\x07\x00\x00\xc0\x07\xd0\x07\xc0\x07\x00\x00\xd0\x07\xb0\x07\xd0\x07\x00\x00\xc0\x07\xe0\x07\xc0\x07\x00\x00\xe0\x07\xd0\x07\xe0\x07\x00\x00\xe0\x07\xf0\x07\xe0\x07\x00\x00\xf0\x07\xd0\x07\xf0\x07\x00\x00\xf0\x07\x00\x08\xf0\x07\x00\x00\x00\x08\xd0\x07\x00\x08\x00\x00\xf0\x07\x10\x08\xf0\x07\x00\x00\x10\x08\x00\x08\x10\x08\x00\x00\x10\x08 \x08\x10\x08\x00\x00 \x08\x00\x08 \x08\x00\x00\x10\x080\x08\x10\x08\x00\x000\x08 \x080\x08\x00\x000\x08@\x080\x08\x00\x00@\x08 \x08@\x08\x00\x00P\x08`\x08P\x08\x00\x00`\x08p\x08`\x08\x00\x00p\x08P\x08p\x08\x00\x00`\x08 \x08`\x08\x00\x00 \x08p\x08 \x08\x00\x00@\x08p\x08@\x08'
            #     num_unknown_data = 266
            #     buff_model += buff_unknown_data

            # with open("X:/Downloads/balls.mxf", 'wb') as f:
            #     f.write(buff_model)
            # return None, "Yeet"

            # if debug_stop is not None and j == debug_stop:
            #     return None, f"NAAAAAH"
            # else:
            #     continue

            if i < len(file)-2 and pad_after_mdl_data == True:
                buff_model += b'\xFF' * 16 #  # Separator padding (At the end of a model)




            buff_header = b'' # Model Header

            buff_header += bx_utils.pack_string(mdl_name, 16) # model name
            buff_header += struct.pack('i', off_model)        # model
            buff_header += struct.pack('i', len(buff_model))  # model length
            buff_header += struct.pack('i', off_bones)        # bones
            buff_header += struct.pack('i', off_bones)        # bones
            buff_header += struct.pack('i', off_materials)    # materials
            buff_header += struct.pack('i', off_bones)        # bones
            buff_header += struct.pack('i', off_iks)          # ik
            buff_header += struct.pack('i', off_morphs)       # morphs
            buff_header += struct.pack('i', off_skinning)     # skinning
            buff_header += struct.pack('i', off_tristrips)    # tristrips
            buff_header += struct.pack('i', 0)                # unknown/unused
            buff_header += struct.pack('i', off_vertices)     # vertex
            buff_header += struct.pack('i', off_last_data)    # last data
            buff_header += struct.pack('i', off_unknown_data) # unknown data
            buff_header += b'\x00' * 28
            buff_header += bytes_ff
            buff_header += b'\x00' * 266
            buff_header += struct.pack('h', num_unk0)             # unknown
            buff_header += struct.pack('h', 0)                    # unknown
            buff_header += struct.pack('h', num_bones)            # bone
            buff_header += struct.pack('h', num_morphs)           # morph
            buff_header += struct.pack('h', num_materials)        # material
            buff_header += struct.pack('h', 0)                    # ik
            buff_header += struct.pack('h', len(weights))         # weights
            buff_header += struct.pack('h', len(tristrip_groups)) # tristrips
            buff_header += struct.pack('h', 0)                    # unknown
            buff_header += struct.pack('h', len(vertices))        # vertex
            buff_header += struct.pack('h', skel_id)              # skeleton id
            buff_header += struct.pack('h', num_last_data)        # last data
            buff_header += struct.pack('h', num_unknown_data)     # unknown data

            buff_headers_list += buff_header # add this model header to the overall model headers 'list'
            buff_models_list += buff_model # add this model to the overall models 'list'


        while len(buff_headers_list)+len_file_header < len_headers: # in case the header section has empty bytes
            buff_headers_list += b'\xB0'

        if pad_after_header_list:
            buff_headers_list += b'\xDE' * len_headers_remainder # Separator padding

        # Write file

        if len(buff_file_header) > 4:
            if file_type == 'board':
                full_out_path = out_path+mdl_file+'.mxf'
            else:
                full_out_path = out_path+mdl_file+'_'+file_type+'.mxf'
            with open(full_out_path, 'wb') as f:
                f.write(buff_file_header+buff_headers_list+buff_models_list)
        print(f"{file_type}.mxf file written\n")
    return True, "Finished"