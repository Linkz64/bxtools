import struct
from ..general import bx_struct as s


def ssx2_get_mxf_data(file_path):
    """
    file_path = mxf file path e.g "G:/Game Files/mac_body.mxf"
    """

    modelHeadersList = []
    modelDataList = []

    with open(file_path, 'rb') as f:
        
        ### File Header
        
        fileHeader = dict(
            fileVersion     = s.get_uint32(f), # 0x00
            numModels       = s.get_uint16(f), # 0x04
            offModelHeaders = s.get_uint16(f), # 0x06
            offModelList    = s.get_uint32(f), # 0x08
        )


        ### Model Headers
        
        f.seek(fileHeader['offModelHeaders'])
        
        for i in range(fileHeader['numModels']): # one header is 396 bytes (0x18C) in length
                                                                    # OFFSET (Relative to header)
            modelHeader = {}
            modelHeader['modelName']          = s.get_string(f, 16) # 0x00 name of model 
            modelHeader["offModel"]           = s.get_uint32(f)     # 0x10 offset to model
            modelHeader["lenModel"]           = s.get_uint32(f)     # 0x14 byte size of model
            modelHeader["offBoneData"]        = s.get_uint32(f)     # 0x18
            modelHeader["offBoneData1"]       = s.get_uint32(f)     # 0x1C same offset
                
            modelHeader["offMaterialList"]    = s.get_uint32(f)     # 0x20
            modelHeader["offBoneData2"]       = s.get_uint32(f)     # 0x24 same offset
            modelHeader["offIKDataList"]      = s.get_uint32(f)     # 0x28
            modelHeader["offMorphSection"]    = s.get_uint32(f)     # 0x2C
                
            modelHeader["offSkinningSection"] = s.get_uint32(f)     # 0x30
            modelHeader["offTriStripSection"] = s.get_uint32(f)     # 0x34
            modelHeader["unknown0"]           = s.get_uint32(f)     # 0x38 unused maybe
            modelHeader["offVertexSection"]   = s.get_uint32(f)     # 0x3C
                
            modelHeader["offLastData"]        = s.get_uint32(f)     # 0x40 unknown
            modelHeader["offUnknownData"]     = s.get_uint32(f)     # 0x44

        
            f.seek(298, 1) # skip past empty/unknown bytes (hex 0x12A)
        
            modelHeader["unknown1"]           = s.get_uint16(f) # 0x172 some have almost the same as numVertices
            modelHeader["unknown2"]           = s.get_uint16(f) # 0x174
            modelHeader["numBones"]           = s.get_uint16(f) # 0x176
            modelHeader["numMorphHeaders"]    = s.get_uint16(f) # 0x178
            modelHeader["numMaterials"]       = s.get_uint16(f) # 0x17A
            modelHeader["numIKs"]             = s.get_uint16(f) # 0x17C
            modelHeader["numSkinningHeaders"] = s.get_uint16(f) # 0x17E
            modelHeader["numTriStripGroups"]  = s.get_uint16(f) # 0x180 aka material groups/splits or surfaces (Godot)
            modelHeader["unknown3"]           = s.get_uint16(f) # 0x182
            modelHeader["numVertices"]        = s.get_uint16(f) # 0x184
            modelHeader["skeletonID"]         = s.get_uint16(f) # 0x186 Weight Flag/ID or Skeleton ID (Sets the local skeleton/weight system ID. In the actual weight data if it's 0 then the bone ID is from the _body skeleton)
            modelHeader["numLastData"]        = s.get_uint16(f) # 0x188 
            modelHeader["numUnknownData"]     = s.get_uint16(f) # 0x18A crashes without numLastData. seems to be for shadows
            # could be that LastData actually looks for values inside UnknownData

            modelHeadersList.append(modelHeader)



        ### Model Buffers

        modelBuffers = []

        for i in range(fileHeader['numModels']):
            f.seek( fileHeader['offModelList']+modelHeadersList[i]["offModel"] ) # go to model offset
            modelBuffers.append( f.read(modelHeadersList[i]["lenModel"]) ) # read model and add to list



    ### Models

    for i in range(fileHeader['numModels']):

        b = modelBuffers[i]


        ## Materials

        materialList = []

        for j in range(modelHeadersList[i]["numMaterials"]):
            off = modelHeadersList[i]["offMaterialList"] + j * 32

            materialList.append(dict(
                texName      = s.bget_string(b, off,    4), # main texture (albedo, deffuse, etc)
                texName1     = s.bget_string(b, off+4,  4), # unknown
                texBumpName  = s.bget_string(b, off+8,  4), # *_b
                texGlossName = s.bget_string(b, off+12, 4), # *_g
                flagEnvr     = s.bget_string(b, off+16, 4), # 'envr' reflects everything on screen
                unkVec3      = s.bget_vec3(  b, off+20),
            ))




        ## Skeleton Hierarchy (Bones)

        boneList = []

        for j in range(modelHeadersList[i]["numBones"]):
            off = modelHeadersList[i]["offBoneData"] + j * 84 # 0x54

            boneList.append(dict(
                boneName     = s.bget_string(b, off, 16),
                skelParentID = s.bget_int16(b,  off+16),  # parent skeleton ID/index
                boneParentID = s.bget_int16(b,  off+18),
                unknownID    = s.bget_int16(b,  off+20),
                boneID       = s.bget_int16(b,  off+22),
                
                boneLoc      = s.bget_vec3(b, off+24), # xyz location relative to parent
                boneRot      = s.bget_vec3(b, off+36), # xyz euler radian rotation
                boneRot1     = s.bget_vec3(b, off+48),
                boneUnk      = s.bget_vec3(b, off+60),
                boneUnk1     = s.bget_vec3(b, off+72),
            ))

            



        ## Inverse Kinematics (IK target points)

        ikList = []

        for j in range(modelHeadersList[i]["numIKs"]):
            off = modelHeadersList[i]["offIKDataList"] + j * 16
    
            ikList.append(dict(
                ikLoc   = s.bget_vec3(b,  off),
                unknown = s.bget_int32(b, off+12), # maybe parent skeleton ID
            ))




        ## Morphs (aka Shape Keys)

        morphsHeaderList = []
        morphsDataList = []
    
        for j in range(modelHeadersList[i]["numMorphHeaders"]):
            off = modelHeadersList[i]["offMorphSection"] + j * 8
    
            morphsHeaderList.append(dict(
                numMorphData      = s.bget_int32(b, off),
                offMorphDataList  = s.bget_int32(b, off+4),
            ))

            tempMorphDataList = []

            for k in range(morphsHeaderList[j]["numMorphData"]):
                off = morphsHeaderList[j]["offMorphDataList"] + k * 16

                tempMorphDataList.append(( 
                    s.bget_vec3(b,   off),    # xyz value (for adding with vertex xyz)
                    s.bget_uint16(b, off+12), # vertex index
                    s.bget_int8(b,   off+14),
                    s.bget_int8(b,   off+15),
                ))

            morphsDataList.append(tempMorphDataList)


        ## Skinning Data (for Weights)
    
        skinningHeaderList = []
        skinningDataList = []
    
        for j in range(modelHeadersList[i]["numSkinningHeaders"]):
            off = modelHeadersList[i]["offSkinningSection"] + j * 12
    
            skinningHeaderList.append(dict(
                numSkinData      = s.bget_uint32(b, off),
                offSkinDataList  = s.bget_uint32(b, off+4),
                skinUnknown      = s.bget_uint16(b, off+6),
                skinUnknown1     = s.bget_uint16(b, off+8),
            ))

            tempSkinDataList = []
    
            for k in range(skinningHeaderList[j]["numSkinData"]):
                off = skinningHeaderList[j]["offSkinDataList"] + k * 4
    
                tempSkinDataList.append(dict( 
                    boneWeight = s.bget_uint16(b, off),   # percentage from 0 to 100
                    boneID     = s.bget_uint8(b,  off+2), # might be bone index instead
                    skeletonID = s.bget_uint8(b,  off+3),
                ))
    
            skinningDataList.append(tempSkinDataList)



        ## Triangle Strips

        triStripHeaderList = []
        triStripIndexList = []
        
        for j in range(modelHeadersList[i]["numTriStripGroups"]):
            off = modelHeadersList[i]["offTriStripSection"] + j * 16
        
            triStripHeaderList.append(dict(
                offIndexList   = s.bget_uint32(b, off),
                numIndices     = s.bget_uint16(b, off+4),
                materialIndex0 = s.bget_uint16(b, off+6),
                materialIndex1 = s.bget_uint16(b, off+8),
                materialIndex2 = s.bget_uint16(b, off+10),
                materialIndex3 = s.bget_uint16(b, off+12),
                materialIndex4 = s.bget_uint16(b, off+14),
            ))

            tempIndexList = []
        
            for k in range(triStripHeaderList[j]["numIndices"]):
                off = triStripHeaderList[j]["offIndexList"] + k * 2
        
                tempIndexList.append(s.bget_uint16(b, off)) # vertex index
        
            triStripIndexList.append(tempIndexList)




        ## Vertex Data
        
        vertexDataList = []
        
        for j in range(modelHeadersList[i]["numVertices"]):
            off = modelHeadersList[i]["offVertexSection"] + j * 64
        
            vertexDataList.append((
                s.bget_vec3(b,    off),    # 0 Vertex
                s.bget_float32(b, off+12), # 1 unknown
                s.bget_vec3(b,    off+16), # 2 Vertex Normal
                s.bget_float32(b, off+28), # 3 unknown
                s.bget_vec3(b,    off+32), # 4 Tangent Normal
                s.bget_float32(b, off+44), # 5 unknown
                s.bget_vec2(b,    off+48), # 6 Texture Coordinates (UVs)
                s.bget_int32(b,   off+56), # 7 unknown
                s.bget_int32(b,   off+60), # 8 Skinning Header Index
            ))




        ## Last Data

        lastDataList = []

        for j in range(modelHeadersList[i]["numLastData"]):
            off = modelHeadersList[i]["offLastData"] + j * 20

            lastDataList.append(( # this is correct, mac_head has 132 on Goggles and count matches
                s.bget_int16(b, off),
                s.bget_int16(b, off+2),
                s.bget_int16(b, off+4),
                s.bget_int16(b, off+6),
                s.bget_int16(b, off+8),
                s.bget_int16(b, off+10),
                s.bget_int16(b, off+12),
                s.bget_int16(b, off+12),
                s.bget_int16(b, off+12),
                s.bget_int16(b, off+12),
            ))


        ## Unknown Data

        unknownDataList = []

        for j in range(modelHeadersList[i]["numUnknownData"]):
            off = modelHeadersList[i]["offUnknownData"] + j * 8

            unknownDataList.append((
                s.bget_int16(b, off),
                s.bget_int16(b, off+2),
                s.bget_int16(b, off+4),
                s.bget_int16(b, off+6),
            ))


        modelDataList.append(dict( # this also appends shadow model
            materials = materialList,
            bones     = boneList,
            morphs    = morphsDataList,
            skins     = skinningDataList,
            tristrips = [triStripHeaderList, triStripIndexList],
            vertices  = vertexDataList
        ))

    return (modelHeadersList, modelDataList)