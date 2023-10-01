import struct
from ..general import bx_struct as s


def ssx3_get_mxf_data(file_path):
    """
    file_path = file path of .mxf file (e.g "G:/Game Files/mac_BottomA.mxf")
    """

    modelHeadersBuffer = b''
    modelHeadersList = []
    modelBuffersList = []
    modelDataList = []

    with open(file_path, 'rb') as f:

        ### File Header
        
        fileHeader = dict(
            fileVersion     = s.get_uint32(f), # 0
            numModels       = s.get_uint16(f), # 4
            offModelHeaders = s.get_uint16(f), # 6
            offModelList    = s.get_uint32(f), # 8
        )
        
        
        
        ### Model Headers
        
        f.seek(fileHeader['offModelHeaders'])
        
        modelHeadersBuffer = f.read(448*fileHeader['numModels'])


        for i in range(fileHeader['numModels']):
            off = i * 448
         
            modelHeadersList.append(dict(
                modelName           = s.bget_string(modelHeadersBuffer, off, 16),
                offModel            = s.bget_uint32(modelHeadersBuffer, off+0x10),
                lenModel            = s.bget_uint32(modelHeadersBuffer, off+0x14),
                offUnused0          = s.bget_uint32(modelHeadersBuffer, off+0x18),
            
                offUnused1          = s.bget_uint32(modelHeadersBuffer, off+0x1C),
                offMaterialList     = s.bget_uint32(modelHeadersBuffer, off+0x20),
                offBoneData         = s.bget_uint32(modelHeadersBuffer, off+0x24),
                unknown0            = s.bget_uint32(modelHeadersBuffer, off+0x28),
            
                offMorphSection     = s.bget_uint32(modelHeadersBuffer, off+0x2C),
                unknown1            = s.bget_uint32(modelHeadersBuffer, off+0x30),
                offSkinningSection  = s.bget_uint32(modelHeadersBuffer, off+0x34),
                offTriStripSection  = s.bget_uint32(modelHeadersBuffer, off+0x38),
            
                unknown2            = s.bget_uint32(modelHeadersBuffer, off+0x3C),
                offVertexSection    = s.bget_uint32(modelHeadersBuffer, off+0x40),
            
                numVertexUnk0       = s.bget_uint32(modelHeadersBuffer, off+0x1A6), #  4 bytes
                numBones            = s.bget_uint16(modelHeadersBuffer, off+0x1AA), #  2
                numMorphShapes      = s.bget_uint16(modelHeadersBuffer, off+0x1AC), #  2
                numMaterials        = s.bget_uint16(modelHeadersBuffer, off+0x1AE), #  2
                unknown3            = s.bget_uint16(modelHeadersBuffer, off+0x1B0), #  2
                numSkinning         = s.bget_uint16(modelHeadersBuffer, off+0x1B2), #  2
                numTristripGroups   = s.bget_uint32(modelHeadersBuffer, off+0x1B4), #  4
                numFinalTriangles   = s.bget_uint32(modelHeadersBuffer, off+0x1B8), #  4 # number of triangles formed by the tristrips
                numVertices         = s.bget_uint16(modelHeadersBuffer, off+0x1BC), #  2
                skeletonID          = s.bget_uint16(modelHeadersBuffer, off+0x1BE), #  2
            ))



            ## Append Model Buffers

            f.seek( fileHeader['offModelList']+modelHeadersList[i]["offModel"] ) # go to model offset
            modelBuffersList.append( f.read(modelHeadersList[i]["lenModel"]) ) # read model bytes and add to list




    ### Models


    for i in range(fileHeader['numModels']):

        # check if the first 2 bytes are 10FB to see if it's compressed

        b = modelBuffersList[i]

        mdlName = modelHeadersList[i]['modelName']
        #print(f"\n{mdlName:16}")



        ## Materials

        materialList = []

        for j in range(modelHeadersList[i]["numMaterials"]):
            off = modelHeadersList[i]["offMaterialList"] + j * 32

            materialList.append(dict(
                texName   = s.bget_string(b, off,    4), # main texture (aka albedo, diffuse, etc)
                texName1  = s.bget_string(b, off+4,  4), # unknown
                flagUnk   = s.bget_string(b, off+8,  4), # exng, exgg, exlg, exsg for hat, hair, boltons?
                flagUnk1  = s.bget_string(b, off+12, 4), # exyg, ah_g
                flagEnvr  = s.bget_string(b, off+16, 4), # env0, env1 reflects environment?
                unkVec3   = s.bget_vec3(b, off+20),
            ))




        ## Skeleton Hierarchy (Bones)

        boneList = []

        for j in range(modelHeadersList[i]["numBones"]):
            off = modelHeadersList[i]["offBoneData"] + j * 80 # 0x50

            boneList.append(dict(
                boneName     = s.bget_string(b, off, 16),
                skelParentID = s.bget_int16(b,  off+16),  # parent skeleton ID/index
                boneParentID = s.bget_int16(b,  off+18),
                unknownID    = s.bget_int16(b,  off+20),
                boneID       = s.bget_int16(b,  off+22),

                unk0         = s.bget_int8(b, off+24),
                unk1         = s.bget_int8(b, off+25),
                unk2         = s.bget_int8(b, off+26),
                unk3         = s.bget_int8(b, off+27),

                unk4         = s.bget_int32(b,  off+28), # padding
                
                boneLoc      = s.bget_vec4(b, off+32), # xyzw location relative to parent
                boneRot      = s.bget_vec4(b, off+48), # xyzw quaternion rotation
                boneUnk      = s.bget_vec4(b, off+64), # xyzw unknown (maybe xyz scale and 1.0 for w)
            ))
            #print(boneList[j]['boneName'])




        ## Morph Data

        morphsHeaderList = []
        morphsDataList = []
    
        for j in range(modelHeadersList[i]["numMorphShapes"] ):
            off = modelHeadersList[i]["offMorphSection"] + j * 8
    
            morphsHeaderList.append(dict(
                numMorphData      = s.bget_int32(b, off),
                offMorphDataList  = s.bget_int32(b, off+4),
            ))

            tempMorphDataList = []

            for k in range(morphsHeaderList[j]["numMorphData"]):
                off = morphsHeaderList[j]["offMorphDataList"] + k * 8

                tempMorphDataList.append((
                    s.bget_vec3_int16_a(b,   off), # xyz value (for adding with vertex xyz)
                    s.bget_uint16(b, off+6), # vertex index
                ))

            morphsDataList.append(tempMorphDataList)




        ## Skinning Data (Weights)

        skinningHeaderList = []
        skinningDataList = []
    
        for j in range(modelHeadersList[i]["numSkinning"]):
            off = modelHeadersList[i]["offSkinningSection"] + j * 12
    
            skinningHeaderList.append(dict(
                numSkinData      = s.bget_uint32(b, off),
                offSkinDataList  = s.bget_uint32(b, off+4),
                skinUnknown      = s.bget_uint16(b, off+8),
                skinUnknown1     = s.bget_uint16(b, off+10),
            ))
            

            tempSkinDataList = []
    
            for k in range(skinningHeaderList[j]["numSkinData"]):
                off = skinningHeaderList[j]["offSkinDataList"] + k * 4
    
                tempSkinDataList.append(dict( 
                    boneWeight = s.bget_uint16(b, off),   # percentage from 0 to 100
                    boneID     = s.bget_uint8(b,  off+2), # might be bone index instead
                    skeletonID = s.bget_uint8(b,  off+3),
                ))
                #print(tempSkinDataList[k]['boneWeight'])
    
            skinningDataList.append(tempSkinDataList)




        ## Tristrip Data

        tristripHeaderList = []
        tristripIndexLists = []
    
        for j in range(modelHeadersList[i]["numTristripGroups"]):
            off = modelHeadersList[i]["offTriStripSection"] + j * 24

            tristripHeaderList.append(dict(
                offSkinRef_IndexList = s.bget_uint32(b, off), # Skin Ref + Index List
                offVertexList        = s.bget_uint32(b, off+4),
                numIndex             = s.bget_uint16(b, off+8),
                numSkinRef           = s.bget_uint16(b, off+10),
                numVertex            = s.bget_uint16(b, off+12),
                idxMaterial          = s.bget_uint16(b, off+14), # Material/Texture Index/ID
                unused0              = s.bget_uint32(b, off+16),
                unused1              = s.bget_uint32(b, off+20),
            ))
            #print(tristripHeaderList[j])

            tempSkinRefList = []
            for k in range(tristripHeaderList[j]['numSkinRef']):
                off = tristripHeaderList[j]["offSkinRef_IndexList"] + k * 2
                tempSkinRefList.append(s.bget_uint16(b, off))
            #print(tempSkinRefList)

            newIndexListOffset = tristripHeaderList[j]["offSkinRef_IndexList"] + tristripHeaderList[j]['numSkinRef'] * 2

            tempIndexList = []
            for k in range(tristripHeaderList[j]['numIndex']):
                off = newIndexListOffset + k * 2

                tempIndexList.append(s.bget_uint16(b, off))
            tristripIndexLists.append(tempIndexList)




        ## Vertex Data
        
        vertexDataList = []
        
        for j in range(modelHeadersList[i]["numVertices"]):
            off = modelHeadersList[i]["offVertexSection"] + j * 24
        
            vertexDataList.append((
                s.bget_vec3(b,    off),          # 0 Vertex
                s.bget_vec2_uint16_b(b, off+12), # 1 Unknown (maybe x,z of vtxNormal)
                s.bget_vec2_uint16_b(b, off+16), # 2 UV
                s.bget_float32(b, off+20),       # 3 Skin Reference Index (Divide by 4 and convert to int)
            ))



        modelDataList.append(dict(
            materials = materialList,
            bones     = boneList,
            morphs    = morphsDataList,
            skins     = skinningDataList,
            tristrips = [tristripHeaderList, tristripIndexLists],
            vertices  = vertexDataList
        ))

    return (modelHeadersList, modelDataList) # Headers and Models