import bpy
from mathutils import Vector

from ..general import bx_utils
from ..general import blender_get_data
from ..external import msh_model_triangle_strips
from .ssx3_model_unpack import ssx3_get_mxf_data

import os
import struct

# Have both Xbox and GameCube functions here
# Get the export file name from the child Collection name
# Get the skeleton from the parent or Armature Modifier

def remove_separator_chars(string):
    # remove the separator characters " " and "_"
    if string.startswith(' ') or string.startswith('_'):
        return string.replace(' ', '').replace('_', '')
    else:
        return string

def ssx3_set_mxf_data():

    mxf_out_path = os.path.abspath(bpy.path.abspath(bpy.context.scene.ssx3_ModelPackPath))+'/'
    mxf_file = bpy.context.scene.ssx3_CustomModelFile.lower()

    #print(mxf_file) # oops this gives the blender path if the box is empty or if there's spaces only

    copy_bones = bpy.context.scene.ssx3_CopyBones
    copy_skel_id = bpy.context.scene.ssx3_CopySkelID

    mxf_in_path = os.path.abspath(bpy.path.abspath(bpy.context.scene.ssx3_ModelUnpackPath))+'/'


    custom_collec = bpy.context.scene.ssx3_CustomModelCollec



    files_to_export = {} # collections to export
    files_names = [] # export file names
    files_found = False
    if custom_collec != None:
        if len(custom_collec.children) == 0:
            return False, f"No subcollections found"

        for collec in custom_collec.children:

            if len(collec.all_objects) > 0:
                files_found = True
                
                name = collec.name
                
                name_with_caps = mxf_file[0].upper()+mxf_file[1:] # first character in upper case

                if mxf_file in collec.name:
                    files_to_export[remove_separator_chars(collec.name.replace(mxf_file, ''))] = collec.all_objects
                elif name_with_caps in collec.name:
                    name = remove_separator_chars(collec.name.replace(name_with_caps, mxf_file))
                    files_to_export[remove_separator_chars(collec.name.replace(name_with_caps, ''))] = collec.all_objects
                else:
                    files_to_export[remove_separator_chars(collec.name)] = collec.all_objects

                files_names.append(name)

        if len(files_to_export) == 0:
            return False, f"No objects found in subcollections"
    else:
        return False, f"Collection not set"


    bytes_00 = b'\x00\x00\x00\x00'
    bytes_ff = b'\xFF\xFF\xFF\xFF'
    inner_header_pad = b'\x00'*354

    pad_separator = True    # within model data
    num_pad_separator_rows = 1 # extra padding rows
    pad_after_mdl_data = False  # after a whole model data
    pad_after_header_list = False


    for fi, file in enumerate(files_to_export):

        copy_used = copy_bones or copy_skel_id

        if copy_used:
            sussy = mxf_in_path+mxf_file+'_'+file#+'.mxf'
            if os.path.exists(sussy+'.mxf'):
                pass
            elif os.path.exists(sussy+'_deco'+'.mxf'):
                original_mxf = ssx3_get_mxf_data(sussy+'_deco'+'.mxf')
            else:
                return False, f"Copy failed. Original .mxf file not found.\nEnsure Collection and names are correct"

            original_model_names = []
            for i in original_mxf[0]:
                original_model_names.append(i['modelName'])


        if len(files_to_export[file]) == 0:
            continue
        else:
            file = files_to_export[file]

        len_file_header = 12 # custom file header length (12 or 16)

        len_headers = len_file_header + 448 * len(file) # file header + model headers
        len_headers_remainder = bx_utils.calc_padding_bytes(len_headers, 16) #-(len_headers % -16) # remainder bytes for 16 byte alignment


        buff_file_header = b''
        buff_file_header += b'\x08\x00\x00\x00'                                   # version maybe
        buff_file_header += struct.pack('h', len(file))                           # numModels
        buff_file_header += struct.pack('h', len_file_header)                     # offset to model header list
        buff_file_header += struct.pack('i', len_headers)#+len_headers_remainder) # offset to model data list
        #buff_file_header += bytes_ff



        buff_headers_list = b''
        buff_models_list = b''



        for i, obj in enumerate(file):

            buff_model = b''


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




            # Skeleton

            custom_skel_object = None
            for modifier in obj.modifiers:
                if modifier.type == "ARMATURE":
                    if modifier.object is not None:
                        custom_skel_object = modifier.object
                        break
            if custom_skel_object is not None:
                pass
            elif custom_skel_object is None and obj.parent is not None:
                if obj.parent.type == 'ARMATURE':
                    custom_skel_object = obj.parent
                else:
                    return False, f"Cannot find parent Armature/Skeleton for {obj.name}"
            else:
                return False, f"{obj.name} is not parented/assigned to an Armature"
            # check if copySkeleton checkbox is enabled, if so get the bone data from the original mxf instead



            if copy_skel_id:
                skel_id = original_mxf[0][original_index]['skeletonID'] # [header][header dict index]['dict key']
            else:
                try:
                    skel_id = int(obj['Skeleton ID'])
                except:
                    return False, "No Skeleton ID found.\nSet it in the object's custom properties or enable copy Skel ID."



            # Model

            off_model = len(buff_models_list)
            mdl_data = blender_get_data.get_mesh_data_for_3(obj=obj, skel=custom_skel_object, original_data=None)
            if type(mdl_data) == str:
                return False, mdl_data
            elif mdl_data == None:
                return None, 'NONEEEEEEEEEEE'

            



            # Materials

            off_materials = 0
            num_materials = len(mdl_data['materials'])

            buff_mats = b''

            for mat in mdl_data['materials']:

                if 'env0' in mat:
                    slot4 = b'env0'
                elif 'env1' in mat:
                    slot4 = b'env1'
                else:
                    slot4 = bytes_00

                buff_mats += bx_utils.pack_string(mat, 4)           # slot0: main texture name: boot, head, suit, alph
                buff_mats += bytes_00                               # slot1: unknown
                buff_mats += bytes_00                               # slot2: unknown: exng, exgg, exlg, exsg
                buff_mats += bytes_00                               # slot3: unknown: exyg, ah_g
                buff_mats += slot4                                  # slot4: environment reflection: env0, env1
                buff_mats += bytes_00*3#struct.pack('fff', 0, 0, 0) # vec3

            buff_model += buff_mats




            # Bones

            off_bones = len(buff_model)

            if copy_bones:
                copied_bones = original_mxf[1][original_index]['bones']

                num_bones = len(mdl_data['bones'])

                buff_bones = b'' #b'\00' * 0x54 * len(mdl_data['bones'])

                for j, bone in enumerate(copied_bones):
                    buff_bones += bx_utils.pack_string(bone['boneName'], 16) # bone name
                    buff_bones += struct.pack('h', bone['skelParentID'])
                    buff_bones += struct.pack('h', bone['boneParentID'])
                    buff_bones += struct.pack('h', bone['unknownID'])
                    buff_bones += struct.pack('h', bone['boneID'])
                    buff_bones += struct.pack('bbbb', bone['unk0'],bone['unk1'],bone['unk2'],bone['unk3'])
                    buff_bones += struct.pack('i', bone['unk4'])
                    buff_bones += struct.pack('ffff', *bone['boneLoc'])
                    buff_bones += struct.pack('ffff', *bone['boneRot'])
                    buff_bones += struct.pack('ffff', *bone['boneUnk'])

                buff_model += buff_bones
            else:
                num_bones = 0



            if pad_separator:
                buff_model += bx_utils.padding_bytes(buff_model, num_rows=num_pad_separator_rows) # Separator padding



            off_morphs = len(buff_model) # Morphs
            num_morphs = 0



            

            off_skinning = len(buff_model) # Skinning (Weights)

            if len(mdl_data['weights']) > 255:
                print("Skinning Count exceeded 255! Weights have to be optimized.")

            off_weights = 12 * len(mdl_data['weights']) + off_skinning

            temp_offsets = [off_weights]

            buff_skinning = b''

            for skin in mdl_data['weights']:
                buff_skinning += struct.pack('i', len(skin))       # weight count
                buff_skinning += struct.pack('i', temp_offsets[-1]) # weight list offset
                buff_skinning += bytes_00

                off_weights += len(skin)*4

                temp_offsets.append(off_weights)


            bone_names = []
            if copy_bones:
                for bone in copied_bones:
                    bone_names.append(bone['boneName'])

            for skin in mdl_data['weights']:

                for skin_weight in skin:
                    if copy_bones:
                        try:
                            bone_index = bone_names.index(skin_weight[1])
                        except:
                            continue # to next loop iteration
                        skel_parent_id = copied_bones[bone_index]['skelParentID']

                    buff_skinning += struct.pack('h', skin_weight[0]) # weight percentage
                    buff_skinning += struct.pack('b', bone_index)     # bone index
                    buff_skinning += struct.pack('b', skel_parent_id) # skeleton ID
    
                    #if skin_weight[2] != 0:
                    #    skel_id = skin_weight[2]

            buff_model += buff_skinning
            #print(buff_skinning)



            if pad_separator:
                buff_model += bx_utils.padding_bytes(buff_model, num_rows=num_pad_separator_rows) # Separator padding




            off_tristrips = len(buff_model) # Triangle Strip Groups

            tristrip_groups = []
            for j in range(len(mdl_data['polygons_by_material'])):

                new_strips = msh_model_triangle_strips.create_triangle_strips(mdl_data['polygons_by_material'][j])
                tristrip_groups.append(bx_utils.stitch_tristrips(new_strips))


            # calculate offset of after headers (start of skin refs and indices)
            off_ref_off_idx = 24 * len(tristrip_groups) + off_tristrips

            temp_offsets = [off_ref_off_idx]

            buff_tristrips = bytearray(b'')

            for stripidx, strip in enumerate(tristrip_groups): # headers
                buff_tristrips += struct.pack('i', temp_offsets[-1]) # offset to skin refs and index list
                buff_tristrips += struct.pack('i', 0)                # offset to vertex list
                buff_tristrips += struct.pack('h', len(strip))       # number of indices
                buff_tristrips += struct.pack('h', len(mdl_data['weights']))  # number of skin refs
                buff_tristrips += struct.pack('h', len(mdl_data['vertices'])) # number of vertices
                buff_tristrips += struct.pack('h', stripidx)         # material index
                buff_tristrips += struct.pack('ii', 0, 0)            # unused, unused

                off_ref_off_idx += len(strip) * 2 # * 2 cuz uint16 indices
                temp_offsets.append(off_ref_off_idx)

            for skinref in range(len(mdl_data['weights'])): # skin indices/references
                buff_tristrips += struct.pack('h', skinref)

            for strip in tristrip_groups: # vertex indices
                for j, idx in enumerate(strip):
                    buff_tristrips += struct.pack('h', idx)


            buff_model += buff_tristrips



            if pad_separator:
                buff_model += bx_utils.padding_bytes(buff_model, num_rows=num_pad_separator_rows) # Separator padding



            off_vertices = len(buff_model) # Vertex Data (Vertices, UVs, etc)

            # temp vertex offset thingy
            struct.pack_into('i', buff_tristrips, 4, off_vertices)


            buff_vertex_data = b''

            for j in range(2):
                for j, vtx in enumerate(mdl_data['vertices']):
                    buff_vertex_data += struct.pack('fff', *vtx[0]) # Vertex
                    buff_vertex_data += struct.pack('hh', 0, 0)     # Unknown (maybe x,z of vtxNormal)
                    buff_vertex_data += struct.pack('hh', 0, 0)     # UV
                    buff_vertex_data += struct.pack('f', vtx[1]*4)  # Skinning index

            buff_model += buff_vertex_data




            if i < len(file)-2 and pad_after_mdl_data == True:
                buff_model += b'\xFF' * 16 #  # Separator padding (At the end of a model)




            buff_header = b'' # Model Header

            buff_header += bx_utils.pack_string(mdl_name, 16) # model name
            buff_header += struct.pack('i', off_model)        # model offset
            buff_header += struct.pack('i', len(buff_model))  # model length
            
            buff_header += struct.pack('i', 0)             # unused
            buff_header += struct.pack('i', 0)             # unused
            buff_header += struct.pack('i', off_materials) # materials
            buff_header += struct.pack('i', off_bones)     # bones
            buff_header += struct.pack('i', 0)             # unknown/unused
            buff_header += struct.pack('i', off_morphs)    # morphs
            buff_header += struct.pack('i', 0)             # unknown/unused
            buff_header += struct.pack('i', off_skinning)  # skinning
            buff_header += struct.pack('i', off_tristrips) # tristrips
            buff_header += struct.pack('i', 0)             # unknown/unused
            buff_header += struct.pack('i', off_vertices)  # vertex

            buff_header += inner_header_pad
            buff_header += struct.pack('i', 0)                         # unknown
            buff_header += struct.pack('h', num_bones)                 # bone
            buff_header += struct.pack('h', num_morphs)                # morph
            buff_header += struct.pack('h', num_materials)             # materials
            buff_header += struct.pack('h', 0)                         # unknown
            buff_header += struct.pack('h', len(mdl_data['weights']))  # skinning
            buff_header += struct.pack('i', len(tristrip_groups))      # tristrips
            buff_header += struct.pack('i', 0)                         # final triangles
            buff_header += struct.pack('h', len(mdl_data['vertices'])) # vertex
            buff_header += struct.pack('h', skel_id)                   # skeleton id



            buff_headers_list += buff_header
            buff_models_list += buff_model
        
        with open(f'X:/Downloads/bx_test/ssx3/{fi}_test.mxf', 'wb') as f: # all files
            f.write(buff_file_header+buff_headers_list+buff_models_list)
        print(f"\n\n{files_names[fi]} written to file.\n")

    with open('X:/Downloads/bx_test/ssx3/export_test.mxf', 'wb') as f: # single test file
        f.write(buff_models_list)



    return True, "Export Finished!"