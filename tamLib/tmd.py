from .utils.PyBinaryReader.binary_reader import *
from .pzze import readPZZE
import numpy as np
from itertools import chain
import struct

class TMD(BrStruct):

    def __init__(self) -> None:
        self.magic = 'tmd0'
        self.name = ""
        self.version = 0x201
        self.modelFlags = 0
        
        self.bones = []
        self.models = []
        self.indexTables = []
        self.textures = []
        
        self.unkBoneInfo = []
        
    def __br_read__(self, br: 'BinaryReader', file_name = "", texture_names = {}) -> None:

        self.magic = br.read_str(4)
        if self.magic != 'tmd0':
            raise ValueError(f"Invalid magic: {self.magic}")

        if file_name:
            self.name = file_name
        
        unk0 = br.read_uint16()
        self.modelFlags = br.read_uint16()
        self.animFlag = br.read_uint16()
        self.version = br.read_uint16()
        headerSize = br.read_uint16()
        self.frameCount = br.read_int16()
        self.boundingBox = br.read_float32(6)
        
        
        self.modelsOffset = br.read_uint64()
        br.seek(16, 1)
        
        self.subMeshEntriesOffset = br.read_uint64()
        self.materialsOffset = br.read_uint64()
        self.shaderParamsOffset = br.read_uint64()
        self.namesOffset = br.read_uint64()
        self.transformationFramesOffset = br.read_uint64()
        self.subMeshOffset = br.read_uint64()
        self.trianglesOffset = br.read_uint64()
        self.texturesOffset = br.read_uint64()
        unk1 = br.read_uint64()
        self.materialTexturesOffset = br.read_uint64()
        self.verticesOffset = br.read_uint64()
        self.unkOffset = br.read_uint64()
        unk2 = br.read_uint64()
        self.modelCount = br.read_uint64()
        unk3 = br.read_uint32()
        self.subMeshEntriesCount = br.read_uint32()
        self.materialCount = br.read_uint32()
        self.shaderParamsCount = br.read_uint32()
        self.namesSize = br.read_uint32()
        self.TransformationFramesCount = br.read_uint32()
        self.subMeshCount = br.read_uint32()
        self.trianglesCount = br.read_uint32()
        self.textureCount = br.read_uint64()
        self.materialTextureCount = br.read_uint32()
        self.vertexCount = br.read_uint32()
        if self.modelFlags & 0x2000:
            self.indexTablesOffset = br.read_uint64()
            self.tableIndicesOffset = br.read_uint64()
            self.boneMatrixOffset = br.read_uint64()
            self.boneHierarchyOffset = br.read_uint64()
            self.indexTablesCount = br.read_uint32()
            self.tableIndicesCount = br.read_uint32()
            self.boneCount = br.read_uint32()
            self.totalBoneCount = br.read_uint32()

        
        #Textures Info
        br.seek(self.texturesOffset, Whence.BEGIN)
        self.textures = br.read_struct(TMDTexture, self.textureCount, texture_names)
        
        #Material Textures Info
        br.seek(self.materialTexturesOffset, Whence.BEGIN)
        self.materialTextures = br.read_struct(TMDMatTexture, self.materialTextureCount, self.textures)
        
        #Shader Params Info
        br.seek(self.shaderParamsOffset, Whence.BEGIN)
        self.shaderParams = [br.read_float32(2)[1] for _ in range(self.shaderParamsCount)]
        
        #Material Info
        br.seek(self.materialsOffset, Whence.BEGIN)
        self.materials = br.read_struct(TMDMaterial, self.materialCount, self.materialTextures, self.shaderParams)

        
        def unpack_normals(v):
            # Strip 4th component and normalize XYZ
            f = ((v[..., :3].astype(np.float32) / 255.0) * 2.0) - 1.0
            norm = np.linalg.norm(f, axis=-1, keepdims=True)
            norm[norm == 0] = 1.0
            return f / norm
        
        # Define converters for specific attributes
        _attribute_converters = {
            'normal':      unpack_normals,
            'normal2':     unpack_normals,
            'tangent':     unpack_normals,
            'binormal':    unpack_normals,
            'color':       lambda v: v.astype(np.float32) / 255.0,
            'color2':      lambda v: v.astype(np.float32) / 255.0,
            'boneWeights': lambda v: v.astype(np.float32) / 255.0,
            'boneWeights2':lambda v: v.astype(np.float32) / 255.0,
            'uv':lambda v: v.astype(np.float32) / 1024.0,
            'uv2':lambda v: v.astype(np.float32) / 1024.0,
            'uv3':lambda v: v.astype(np.float32) / 1024.0,
        }

        # Determine vertex attributes based on flags
        vertex_attributes = []
        if self.modelFlags & 0x2:
            vertex_attributes.append(('position', 'f4', 3))

        if self.modelFlags & 0x400:
            vertex_attributes.append(('boneWeights', 'u1', 4))
            vertex_attributes.append(('boneIDs', 'u1', 4))

        if self.modelFlags & 0x8000:
            vertex_attributes.append(('boneWeights2', 'u1', 4))
            vertex_attributes.append(('boneIDs2', 'u1', 4))

        if self.modelFlags & 0x4:
            vertex_attributes.append(('normal', 'u1', 4))

        if self.modelFlags & 0x8:
            vertex_attributes.append(('tangent', 'u1', 4))
            vertex_attributes.append(('binormal', 'u1', 4))

        if self.modelFlags & 0x80:
            vertex_attributes.append(('color', 'u1', 4))

        if self.modelFlags & 0x100:
            vertex_attributes.append(('normal2', 'u1', 4))

        if self.modelFlags & 0x200:
            vertex_attributes.append(('color2', 'u1', 4))

        if self.modelFlags & 0x10:
            vertex_attributes.append(('uv', 'u2', 2))
        if self.modelFlags & 0x20:
            vertex_attributes.append(('uv2', 'u2', 2))
        if self.modelFlags & 0x40:
            vertex_attributes.append(('uv3', 'u2', 2))

        # Read vertex buffer
        br.seek(self.verticesOffset, Whence.BEGIN)
        npVertexAtt = np.dtype(vertex_attributes)
        self.rawVertices = br.read_structured_array(npVertexAtt, self.vertexCount)

        
        # Convert fields in bulk
        converted_attributes = {}
        for name, dtype, size in vertex_attributes:
            column = self.rawVertices[name]
            if name in _attribute_converters:
                column = _attribute_converters[name](column)
            converted_attributes[name] = column

        # Create and fill vertex objects
        self.vertices = [TMDVertex() for _ in range(self.vertexCount)]
        for i in range(self.vertexCount):
            vertex = self.vertices[i]
            for name in converted_attributes:
                setattr(vertex, name, list(converted_attributes[name][i]))

        #print(self.vertices[0].__dict__)

        # Read triangle info
        br.seek(self.trianglesOffset, Whence.BEGIN)
        if self.modelFlags & 0x800:
            self.triangles = [br.read_uint32(3) for _ in range(self.trianglesCount)]
        else:
            self.triangles = [br.read_uint16(3) for _ in range(self.trianglesCount)]


        if self.modelFlags & 0x2000:
            #read all indices for the index table
            br.seek(self.tableIndicesOffset, Whence.BEGIN)
            self.allIndices = [br.read_uint8() for i in range(self.tableIndicesCount)]
            
            #pass the indices list to the index table class and read the individual index tables
            br.seek(self.indexTablesOffset, Whence.BEGIN)
            self.indexTables = br.read_struct(TMDIndexTable, self.indexTablesCount, self.allIndices)
            
            if not self.indexTables:
                genericIndexTable = TMDIndexTable()
                genericIndexTable.indices = [i for i in range(self.boneCount)]
                self.indexTables = [genericIndexTable]
            
            # read skeleton info
            br.seek(self.boneHierarchyOffset, Whence.BEGIN)
            self.bones = br.read_struct(TMDBone, self.boneCount, self.namesOffset)
            
            #read the matrix info
            br.seek(self.boneMatrixOffset, Whence.BEGIN)
            for i in range(self.boneCount):
                self.bones[i].matrix = [br.read_float32(4) for _ in range(4)]
            
            #print(self.bones[0].__dict__)
        
        #transformation frames info
        br.seek(self.transformationFramesOffset, Whence.BEGIN)
        self.materialAnimationFrames = br.read_struct(TMDMaterialAnimationFrame, self.TransformationFramesCount)
        
        br.seek(self.subMeshEntriesOffset, Whence.BEGIN)
        self.submeshEntries = br.read_struct(TMDSubmeshEntry,self.subMeshEntriesCount)
        
        br.seek(self.subMeshOffset, Whence.BEGIN)
        self.submeshes = br.read_struct(TMDSubmesh,self.subMeshCount, self.triangles, self.vertices)
        
        #read model info
        br.seek(self.modelsOffset, Whence.BEGIN)
        self.models = br.read_struct(TMDModel, self.modelCount, self.indexTables, self.submeshEntries, self.submeshes, self.materials, self.namesOffset)
                
        
    def __br_write__(self, br: 'BinaryReader', *args) -> None:
        #magic
        br.write_str_fixed("tmd0",4)
        br.write_int16(0)
        br.write_uint16(self.modelFlags)
        br.write_uint16(0) #this has something to do with hair meshes
        br.write_uint16(self.version)
        br.write_uint16(0x28)
        br.write_int16(self.frameCount)
        br.write_float32(self.boundingBox)
        
        modelOffsetPos = br.pos()
        br.write_uint64(0)
        
        br.pad(16)
        
        entriesOffsetPos = br.pos()
        br.write_uint64(0)
        
        materialsOffsetPos = br.pos()
        br.write_uint64(0)
        
        paramsOffsetPos = br.pos()
        br.write_uint64(0)
        
        namesOffsetPos = br.pos()
        br.write_uint64(0)
        
        transformationFramesOffsetPos = br.pos()
        br.write_uint64(0)
        
        submeshOffsetPos = br.pos()
        br.write_uint64(0)
        
        trianglesOffsetPos = br.pos()
        br.write_uint64(0)
        
        texturesOffsetPos = br.pos()
        br.write_uint64(0)
        
        br.write_uint64(0) #unk offset
        
        matTexOffsetPos = br.pos()
        br.write_uint64(0)
        
        verticesOffsetPos = br.pos()
        br.write_uint64(0)
        
        unkSecOffsetPos = br.pos()
        br.write_uint64(0)
        
        br.write_uint64(0) #unk offset
        
        br.write_uint64(len(self.models))
        br.write_uint32(0)
        
        entriesCountPos = br.pos()
        br.write_uint32(0)
        
        materialCountPos = br.pos()
        br.write_uint32(0)
        
        paramCountPos = br.pos()
        br.write_uint32(0)
        
        namesBufferSizePos = br.pos()
        br.write_uint32(0) #Names Buffer Size
        
        br.write_uint32(self.TransformationFramesCount) # TransformationFramesCount
        
        submeshCountPos = br.pos()
        br.write_uint32(0)
        
        trianglesCountPos = br.pos()
        br.write_uint32(0)
        
        textureCountPos = br.pos()
        br.write_uint64(0)
        
        matTexCountPos = br.pos()
        br.write_uint32(0)
        
        vertexCountPos = br.pos()
        br.write_uint32(0)
        
        if len(self.bones):
            idxTblOffsetPos = br.pos()
            br.write_uint64(0)
            
            indicesOffsetPos = br.pos()
            br.write_uint64(0)
            
            matricesOffsetPos = br.pos()
            br.write_uint64(0)
            
            hierarchyOffsetPos = br.pos()
            br.write_uint64(0)
            
            idxTblCountPos = br.pos()
            br.write_uint32(0)
            
            indicesCountPos = br.pos()
            br.write_uint32(0)
            
            boneCountPos = br.pos()
            br.write_uint32(0)
            
            boneCount2Pos = br.pos()
            br.write_uint32(0)
        
        br.align(16)
            
        #we have to write the rest of the file before writing the rest of the header
        matBuffer = BinaryReader()
        paramBuffer = BinaryReader()
        matTexBuffer = BinaryReader()
        texBuffer = BinaryReader()
        
        matTexList = []
        LastTextures = []
        paramsList = []
        
        # write materials
        matBuffer.write_struct(self.materials, matTexList, LastTextures, paramsList)
        print("Materials Written")
        
        #write params
        for param in paramsList:
            paramBuffer.pad(4)
            paramBuffer.write_float32(param)
        print("Params Written")
        
        materialAnimationBuffer = BinaryReader()
        #write material animation frames
        materialAnimationBuffer.write_struct(self.materialAnimationFrames)
        
        #write material textures
        matTexBuffer.write_struct(self.materialTextures)
        print("Material Textures Written")
        
        #write texture info
        texBuffer.write_struct(self.textures)
        print("Textures Written")
        
        
        #write models
        modelBuffer = BinaryReader()
        namesBuffer = BinaryReader(encoding="cp932")        
        
        indexTablesList = []
        submeshEntries = []
        submeshes = []
        modelBuffer.write_struct(self.models, indexTablesList, submeshEntries, submeshes, self.materials, namesBuffer, len(self.bones))
        
        self.submeshes= submeshes
        
        #write submesh entries
        entryBuffer = BinaryReader()
        entryBuffer.write_struct(submeshEntries)
        
        
        #write the submeshes
        trianglesList = []
        verticesList = []
        triangleOffsets = []
        
        submeshBuffer = BinaryReader()
        submeshBuffer.write_struct(submeshes, trianglesList, triangleOffsets)
        print("submeshes Written")
        
        
        def encode_weights_np(np_weights):
            # Scale all 8 weights to 0-255 range
            out = np_weights.copy()
            out *= 255.0
            out = np.clip(np.round(out), 0, 255).astype(np.uint8)

            # Calculate total for all 8 weights per vertex
            total = out.sum(axis=1, keepdims=True)
            diffs = 255 - total

            # Distribute difference to max-weight component across all 8 weights
            max_idx = np.argmax(out, axis=1)
            out[np.arange(len(out)), max_idx] += diffs[:, 0]
            out = np.clip(out, 0, 255).astype(np.uint8)

            # Split into first 4 and last 4 after normalization
            return out[:, :4], out[:, 4:]


        def encode_normal_np(np_normals):
            scaled = ((np_normals + 1.0) * 0.5) * 255.0
            encoded = np.clip(np.round(scaled), 0, 255).astype(np.uint8)
            return encoded


        encoded_vertex_dtype = []
        vertex_attributes = {}
        count = len(self.vertices)
        flags = self.modelFlags

        # Position ----------------------------------------------------------
        if flags & 0x2:
            encoded_vertex_dtype.append(('position', 'f4', (3,)))
            vertex_attributes['position'] = self.vertices['position']

        # Bone Weights + IDs ------------------------------------------------
        if flags & 0x400:
            encoded_vertex_dtype += [
                ('boneWeights1', 'u1', (4,)),
                ('boneIDs1',     'u1', (4,))
            ]
            bweights1, bweights2 = encode_weights_np(self.vertices['weights'])
            bindices1 = self.vertices['boneIDs'].astype(np.uint8)[:, :4]
            bindices2 = self.vertices['boneIDs'].astype(np.uint8)[:, 4:]
            vertex_attributes['boneWeights1'] = bweights1
            vertex_attributes['boneIDs1'] = bindices1


        # Custom normal -----------------------------------------------------
        if flags & 0x4:
            encoded_vertex_dtype += [
                ('custom_normal', 'u1', (3,)),
                ('normal_pad',    'u1', (1,))
            ]
            vertex_attributes['custom_normal'] = encode_normal_np(self.vertices['custom_normal'])
            vertex_attributes['normal_pad'] = np.full((count, 1), 255, dtype=np.uint8)

        # Tangent and Bitangent --------------------------------------------
        if flags & 0x8:
            encoded_vertex_dtype += [
                ('tangent',        'u1', (3,)),
                ('tangent_pad',    'u1', (1,)),
                ('bitangent',      'u1', (3,)),
                ('bitangent_pad',  'u1', (1,))
            ]
            vertex_attributes['tangent'] = encode_normal_np(self.vertices['tangent'])
            vertex_attributes['tangent_pad'] = np.zeros((count, 1), dtype=np.uint8)
            vertex_attributes['bitangent'] = encode_normal_np(self.vertices['bitangent'])
            vertex_attributes['bitangent_pad'] = np.zeros((count, 1), dtype=np.uint8)

        # Color layers ------------------------------------------------------
        if flags & 0x80:
            encoded_vertex_dtype.append(('color0', 'u1', (4,)))
            vertex_attributes['color0'] = (self.vertices['color0'] * 255).clip(0, 255).astype(np.uint8)

        if flags & 0x100:
            encoded_vertex_dtype += [
                ('real_normal',    'u1', (3,)),
                ('real_normal_pad','u1', (1,))
            ]
            vertex_attributes['real_normal'] = encode_normal_np(self.vertices['real_normal'])
            vertex_attributes['real_normal_pad'] = np.full((count, 1), 255, dtype=np.uint8)

        if flags & 0x200:
            encoded_vertex_dtype.append(('color1', 'u1', (4,)))
            vertex_attributes['color1'] = (self.vertices['color1'] * 255).clip(0,255).astype(np.uint8)

        # UVs ---------------------------------------------------------------
        if flags & 0x10:
            encoded_vertex_dtype.append(('uv0', 'i2', (2,)))
            vertex_attributes['uv0'] = (self.vertices['uv0']  * 1024.0).clip(0, 32767).astype(np.int16)
            

        if flags & 0x20:
            encoded_vertex_dtype.append(('uv1', 'i2', (2,)))
            vertex_attributes['uv1'] = (self.vertices['uv1'] * 1024.0).clip(0, 32767).astype(np.int16)

        if flags & 0x40:
            encoded_vertex_dtype.append(('uv2', 'i2', (2,)))
            vertex_attributes['uv2'] = (self.vertices['uv2'] * 1024.0).clip(0, 32767).astype(np.int16)


        # ---- Build structured array safely ----------------------------------
        encoded_vertices = np.empty(count, dtype=np.dtype(encoded_vertex_dtype))

        for name, _, _ in encoded_vertex_dtype:
            encoded_vertices[name] = vertex_attributes[name]
        

        # Raw bytes
        vertexBuffer = BinaryReader()
        vertexBuffer.write_bytes(encoded_vertices.tobytes())
        
        print("vertex buffer written")
        
        #write triangles buffer
        triBuffer = BinaryReader()
        
        if self.modelFlags & 0x800:
            triangleBuffer = np.array(trianglesList, dtype=np.uint32).tobytes()
            triBuffer.write_bytes(triangleBuffer)
        else:
            triangleBuffer = np.array(trianglesList, dtype=np.uint16).tobytes()
            triBuffer.write_bytes(triangleBuffer)

        print("triangles buffer written")
        
        
        #write bone buffers
        boneMatrixBuffer = BinaryReader()
        boneHierarchyBuffer = BinaryReader()
        boneExtraInfoBuffer = BinaryReader()
        unkBoneBuffer = BinaryReader()
        
        for bone in self.bones:
            boneMatrixBuffer.write_float32([value for row in bone.matrix for value in row])
            boneHierarchyBuffer.write_struct(bone, namesBuffer, self.version)
            boneExtraInfoBuffer.write_int16(bone.extra)
            if bone.extra > -1:
                self.unkBoneInfo.append(bone.offset)
        
        for unkInfo in self.unkBoneInfo:
            unkBoneBuffer.write_float32(unkInfo)
        
        print("Bone Data Written")
        
        #write index tables
        indexTblBuffer = BinaryReader()
        indicesBuffer = BinaryReader()
        
        indicesList = []
        indexTblBuffer.write_struct(indexTablesList, indicesList)
        indicesBuffer.write_uint8(indicesList)
        
        print("Indices Written")
        
        
        # Write all buffers and record their offsets
        def write_and_get_offset(buffer: BinaryReader, alignment=16):
            offset = br.pos()
            br.write_bytes(bytes(buffer.buffer()))
            br.align(alignment)
            return offset


        modelOffset = write_and_get_offset(modelBuffer)
        entriesOffset = write_and_get_offset(entryBuffer)
        materialsOffset = write_and_get_offset(matBuffer)
        paramsOffset = write_and_get_offset(paramBuffer)
        namesOffset = write_and_get_offset(namesBuffer)
        transformationFramesOffset = write_and_get_offset(materialAnimationBuffer)
        for offset in triangleOffsets:
            submeshBuffer.seek(offset, Whence.BEGIN)
            submeshBuffer.write_uint32(br.size() + submeshBuffer.size())
        
        submeshOffset = write_and_get_offset(submeshBuffer)
        trianglesOffset = write_and_get_offset(triBuffer)
        texturesOffset = write_and_get_offset(texBuffer)
        matTexOffset = write_and_get_offset(matTexBuffer)
        verticesOffset = write_and_get_offset(vertexBuffer)
        

        # Optional bone section
        if len(self.bones):
            if len(self.bones) >= 255:
                indexTablesOffset = write_and_get_offset(indexTblBuffer)
                tableIndicesOffset = write_and_get_offset(indicesBuffer)
            else:
                indexTablesOffset = tableIndicesOffset = 0
                indicesList = []
                indexTablesList = []
            boneMatrixOffset = write_and_get_offset(boneMatrixBuffer)
            boneHierarchyOffset = write_and_get_offset(boneHierarchyBuffer)
        
        
        

        # Patch header
        def patch_u32(pos, val):
            here = br.pos()
            br.seek(pos)
            br.write_uint32(val)
            br.seek(here)

        def patch_u64(pos, val):
            here = br.pos()
            br.seek(pos)
            br.write_uint64(val)
            br.seek(here)

        patch_u64(modelOffsetPos, modelOffset)
        patch_u64(entriesOffsetPos, entriesOffset)
        patch_u64(materialsOffsetPos, materialsOffset)
        patch_u64(paramsOffsetPos, paramsOffset)
        patch_u64(namesOffsetPos, namesOffset)
        patch_u64(transformationFramesOffsetPos, transformationFramesOffset)
        patch_u64(submeshOffsetPos, submeshOffset)
        patch_u64(trianglesOffsetPos, trianglesOffset)
        patch_u64(texturesOffsetPos, texturesOffset)
        patch_u64(matTexOffsetPos, matTexOffset)
        patch_u64(verticesOffsetPos, verticesOffset)
        patch_u64(unkSecOffsetPos, 0)
        
        patch_u32(entriesCountPos, len(submeshEntries))
        patch_u32(materialCountPos, len(self.materials))
        patch_u32(paramCountPos, len(paramsList))
        patch_u32(namesBufferSizePos, namesBuffer.size())
        patch_u32(submeshCountPos, len(self.submeshes))
        patch_u32(trianglesCountPos, len(self.triangles))
        patch_u64(textureCountPos, len(self.textures))
        patch_u32(matTexCountPos, len(self.materialTextures))
        patch_u32(vertexCountPos, len(self.vertices))

        if len(self.bones):
            patch_u32(idxTblOffsetPos, indexTablesOffset)
            patch_u32(indicesOffsetPos, tableIndicesOffset)
            patch_u32(matricesOffsetPos, boneMatrixOffset)
            patch_u32(hierarchyOffsetPos, boneHierarchyOffset)
            patch_u32(idxTblCountPos, len(indexTablesList))
            patch_u32(indicesCountPos, len(indicesList))
            patch_u32(boneCountPos, len(self.bones))
            patch_u32(boneCount2Pos, len(self.bones))
    
    
        print("done")
        
            
        

class TMDUnk(BrStruct):
    def __init__(self) -> None:
        self.values = [0] * 24
    
    def __br_read__(self, br: 'BinaryReader') -> None:
        self.values = br.read_float32(24)
    
    def __br_write__(self, br, *args):
        br.write_float32(self.values)


class TMDModel(BrStruct):
    def __init__(self) -> None:
        self.boundingBox = [0,0,0,0,0,0]
        self.meshes = []
        self.materials = []
        self.name = ""
        self.hash = 0
        self.hashFlag = 0
        self.nameFlag = 0
        self.unk1 = 0
        self.unk2 = 0
        self.unk3 = 0
    
    def __br_read__(self, br: 'BinaryReader', indexTables, entries, submeshes, materials, namesOffset) -> None:
        self.boundingBox = br.read_float32(6)
        self.entriesCount = br.read_uint16()
        self.hashFlag =  br.read_uint8()
        self.nameFlag =  br.read_uint8()
        self.hash =  br.read_uint32()
        self.entriesStart = br.read_uint64()
        self.nameOffset = br.read_int32()
        self.unk1 = br.read_int32()
        self.unk2 = br.read_int32()
        self.unk3 = br.read_int32()
        
        if namesOffset > 0 and self.nameOffset != -1:
            self.name = br.read_str_at_offset(namesOffset + self.nameOffset)
        else:
            self.name = f"{str(self.hash)}"
        
        materialIdx = -1
        indexTable = indexTables[0] if indexTables else TMDIndexTable()
        
        for entry in entries[self.entriesStart: self.entriesStart + self.entriesCount]:
            if entry.type == 96:
                self.materials.append(materials[entry.index])
                materialIdx = entry.index
            
            elif entry.type == 64:
                indexTable = indexTables[entry.index]
            elif entry.type == 48:
                mesh = submeshes[entry.index]
                mesh.materialIndex = materialIdx
                mesh.material = materials[materialIdx]
                mesh.indexTable = indexTable.indices
                self.meshes.append(mesh)
            
    
    def __br_write__(self, br: 'BinaryReader', indexTables, entries, submeshes, materials, namesBuffer, boneCount) -> None:
        br.write_float32(self.boundingBox)
        #br.write_uint16(len(self.meshes))
        
        #write meshes
        materialIdx = -1
        submeshIdx = len(submeshes)
        localEntries = []
        
        for mesh in self.meshes:
            mesh: TMDSubmesh
            materialIndex = materials.index(mesh.material)
            print(materialIndex)
            if materialIdx != materialIndex:
                #update the material index
                materialIdx = materialIndex
                
                #create a material entry
                matEntry = TMDSubmeshEntry()
                matEntry.type = 96
                matEntry.index = materialIdx
                localEntries.append(matEntry)
            
            if mesh.indexTable and boneCount >= 255:
                
                idxTbl = TMDIndexTable()
                idxTbl.indices = mesh.indexTable
                
                #create index table entry
                idxTblEntry = TMDSubmeshEntry()
                idxTblEntry.type = 64
                idxTblEntry.index = len(indexTables)
                
                indexTables.append(idxTbl)                
                localEntries.append(idxTblEntry)
                
                
            #create mesh and its entry
            submeshes.append(mesh)
            meshEntry = TMDSubmeshEntry()
           # meshEntry.index = submeshes.index(mesh)
            meshEntry.index = submeshIdx
            submeshIdx += 1
            meshEntry.type = 48
            
            localEntries.append(meshEntry)
        
        #when done create end Entry
        endEntry = TMDSubmeshEntry()
        endEntry.index = 0
        endEntry.type = 16
        localEntries.append(endEntry)
                
        
        #write the amount of local entries then extend the entries list
        br.write_uint16(len(localEntries))
        br.write_uint8(self.hashFlag)
        br.write_uint8(self.nameFlag)
        br.write_uint32(self.hash)
        br.write_uint64(len(entries))
        entries.extend(localEntries)
        try:
            # Try interpreting name as an integer
            if self.name.isdigit() and int(self.name) == self.hash:
                br.write_int32(-1)  # name matches hash, don't write
            else:
                br.write_int32(namesBuffer.size())  # write offset
                namesBuffer.write_str(self.name)
        except ValueError:
            # Non-integer name, write it normally
            br.write_int32(namesBuffer.size())
            namesBuffer.write_str(self.name)
        
        br.write_int32(self.unk1)
        br.write_int32(self.unk2)
        br.write_int32(self.unk3)
        
        

class TMDSubmesh(BrStruct):
    def __init__(self):
        self.material = None
        self.indexTable = []
        self.triangles = []
        self.vertices = []
        self.materialIndex = 0
        self.trianglesCount = 0
        self.trianglesStart = 0
    
    
    def __br_read__(self, br, triangles, vertices):
        self.trianglesCount = br.read_uint32()
        self.trianglesOffset = br.read_uint32()
        self.trianglesStart = br.read_uint32()
        unk = br.read_uint32()
        
        
        vertex_map = {}  # Maps global index -> local index

        for tris in triangles[self.trianglesStart : self.trianglesStart + self.trianglesCount]:
            local_tri = []
            for global_idx in tris:
                if global_idx not in vertex_map:
                    vertex_map[global_idx] = len(self.vertices)
                    self.vertices.append(vertices[global_idx])
                local_tri.append(vertex_map[global_idx])
            self.triangles.append(local_tri)
    
    def __br_write__(self, br: 'BinaryReader', trianglesList, triangleOffsets):
        br.write_uint32(len(self.triangles))  # Write triangle count
        triangleOffsets.append(br.pos())  # Store the triangle offset
        br.write_uint32(0)  # Placeholder for triangle offset
        # Store the starting triangle index
        t_startIndex = len(trianglesList)
        br.write_uint64(t_startIndex)
        trianglesList.extend(self.triangles.tolist())
        

class TMDSubmeshEntry(BrStruct):
    def __init__(self):
        self.type = None
        self.index = -1
    
    def __br_read__(self, br, *args):
        self.index = br.read_uint8()
        self.type = br.read_uint8()
    
    def __br_write__(self, br, *args):
        br.write_int8(self.index)
        br.write_int8(self.type)


class TMDTexture(BrStruct):
    def __init__(self) -> None:
        self.name = ''
        self.hash = 0
        self.index = 0
        self.width = 0
        self.height = 0
        self.format = 21074
        self.data = b''
    
    def __br_read__(self, br: 'BinaryReader', texture_names = {}) -> None:
        self.hash = br.read_uint32()
        self.name = texture_names.get(self.hash, str(self.hash))
        self.index = br.read_uint16()
        self.width = br.read_uint16()
        self.height = br.read_uint16()
        self.format = br.read_uint16()
    
    
    def __br_write__(self, br: 'BinaryReader', *args) -> None:
        br.write_uint32(self.hash)
        br.write_uint16(self.index)
        br.write_uint16(self.width)
        br.write_uint16(self.height)
        br.write_uint16(self.format)
        


class TMDMatTexture(BrStruct):
    def __init__(self) -> None:
        self.textureHash = 0
        self.textureIndex = 0
        self.texture = None
        self.unk1 = 0
        self.unk2 = 0
        self.slot = 0

    def __br_read__(self, br: 'BinaryReader', textures) -> None:
        self.textureHash = br.read_uint32()
        self.textureIndex = br.read_uint16()
        self.texture = textures[self.textureIndex]
        self.unk1 = br.read_int16()
        self.unk2 = br.read_int16()
        self.slot = br.read_int16() >> 8
    
    def __br_write__(self, br):
        br.write_uint32(self.texture.hash)
        #br.write_uint16(textures.index(self.texture))
        br.write_uint16(self.textureIndex)
        br.write_int16(self.unk1)
        br.write_int16(self.unk2)
        br.write_int8(0)
        br.write_int8(self.slot)

class TMDMaterial(BrStruct):
    def __init__(self) -> None:
        self.hash = 0
        self.name = ''
        self.shaderID = ""
        self.textures = []
        self.shaderParams = []
        self.unk = -1

    def __br_read__(self, br: 'BinaryReader', textures, params) -> None:
        self.hash = br.read_uint32()
        self.name = str(self.hash)
        self.shaderID = br.read_str(4)
        self.textureStartIndex = br.read_uint16()
        self.textureCount = br.read_uint16()
        self.textures = textures[self.textureStartIndex: self.textureStartIndex + self.textureCount]
        
        self.shaderParamsStartIndex = br.read_uint16()
        self.shaderParamsCount = br.read_uint16()
        self.unk = br.read_int32()
        self.shaderParams = params[self.shaderParamsStartIndex: self.shaderParamsStartIndex + self.shaderParamsCount]

    def __br_write__(self, br: 'BinaryReader', matTextures, LastTextures, params) -> None:
        br.write_uint32(self.hash)
        br.write_str_fixed(self.shaderID,4)
        
        reuse = False
        #compare LastTextures with the current textures
        if len(LastTextures) == len(self.textures):
            for i in range(len(LastTextures)):
                if LastTextures[i].textureHash != self.textures[i].textureHash:
                    reuse = False
                    break
                reuse = True
        
        
        if reuse:
            br.write_uint16(len(matTextures) - len(self.textures))
            br.write_uint16(len(self.textures))
        else:
            br.write_uint16(len(matTextures))
            br.write_uint16(len(self.textures))
            #add textures from this material to the texture list
            matTextures.extend(self.textures)
        LastTextures.clear()
        LastTextures.extend(self.textures)
        
        br.write_uint16(len(params))
        br.write_uint16(len(self.shaderParams))
        #add params from this material to the shader params list
        params.extend(self.shaderParams)
        br.write_int32(self.unk)


class TMDMaterialAnimationFrame(BrStruct):
    def __init__(self) -> None:
        self.materialIndex = 0
        self.frameCount = 0
        self.frames = []
    
    def __br_read__(self, br: 'BinaryReader', *args) -> None:
        self.frame = br.read_uint16()
        self.flags = br.read_uint16()
        self.value = br.read_float32()
    
    def __br_write__(self, br: 'BinaryReader', *args) -> None:
        br.write_uint16(self.frame)
        br.write_uint16(self.flags)
        br.write_float32(self.value)


class TMDVertex:
    def __init__(self) -> None:
        self.position = [0.0, 0.0, 0.0]
        self.normal = [0.0, 0.0, 0.0]
        self.normal2 = [0.0, 0.0, 0.0]
        self.tangent = [0.0, 0.0, 0.0]
        self.binormal = [0.0, 0.0, 0.0]
        self.uv = [0.0, 0.0]
        self.uv2 = [0.0, 0.0]
        self.uv3 = [0.0, 0.0]
        self.uv4 = [0.0, 0.0]
        self.color = [0, 0, 0, 255]
        self.color2 = [0, 0, 0, 255]
        self.boneIDs = [0, 0, 0, 0]
        self.boneWeights = [0, 0, 0, 0]
        self.boneIDs2 = [0, 0, 0, 0]
        self.boneWeights2 = [0, 0, 0, 0]


class TMDBone(BrStruct):
    def __init__(self) -> None:
        self.name = ''
        self.parentIndex = 0
        self.posedLocation = [0.0, 0.0, 0.0]
        self.matrix = np.zeros((4, 4), dtype=np.float32)
        self.extra = -1
        self.offset = [0,0,0]

    def __br_read__(self, br: 'BinaryReader', namesOffset = -1) -> None:
        self.hash = br.read_uint32()
        self.posedLocation = br.read_float32(3)
        self.parentIndex = br.read_int32()
        
        self.unk1 = br.read_uint16()
        self.nameOffset = br.read_uint16()
        self.name = str(self.hash)
    
    
    def __br_write__(self, br, namesBuffer: BinaryReader, version):
        br.write_uint32(self.hash)
        br.write_float32(self.posedLocation)
        br.write_int32(self.parentIndex)
        br.write_uint16(0)
        
        if version >= 0x209:
            br.write_uint16(namesBuffer.size())
            namesBuffer.write_str(self.name)
        else:
            br.write_int16(0)


class TMDIndexTable(BrStruct):
    def __init__(self):
        self.indices = []
        self.indicesCount = 0
    
    def __br_read__(self, br, tableIndices):
        
        self.indicesCount = br.read_uint32()
        unkString = br.read_str(4)
        self.startIndex = br.read_uint64()
        
        self.indices = tableIndices[self.startIndex: self.startIndex + self.indicesCount]

    def __br_write__(self, br, indicesList):
        br.write_uint64(len(self.indices))
        br.write_uint64(len(indicesList))
        indicesList.extend(self.indices)


CRC32TABLE = [
    0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA, 0x076DC419, 0x706AF48F, 0xE963A535, 0x9E6495A3,
	0x0EDB8832, 0x79DCB8A4, 0xE0D5E91E, 0x97D2D988, 0x09B64C2B, 0x7EB17CBD, 0xE7B82D07, 0x90BF1D91,
	0x1DB71064, 0x6AB020F2, 0xF3B97148, 0x84BE41DE, 0x1ADAD47D, 0x6DDDE4EB, 0xF4D4B551, 0x83D385C7,
	0x136C9856, 0x646BA8C0, 0xFD62F97A, 0x8A65C9EC, 0x14015C4F, 0x63066CD9, 0xFA0F3D63, 0x8D080DF5,
	0x3B6E20C8, 0x4C69105E, 0xD56041E4, 0xA2677172, 0x3C03E4D1, 0x4B04D447, 0xD20D85FD, 0xA50AB56B,
	0x35B5A8FA, 0x42B2986C, 0xDBBBC9D6, 0xACBCF940, 0x32D86CE3, 0x45DF5C75, 0xDCD60DCF, 0xABD13D59,
	0x26D930AC, 0x51DE003A, 0xC8D75180, 0xBFD06116, 0x21B4F4B5, 0x56B3C423, 0xCFBA9599, 0xB8BDA50F,
	0x2802B89E, 0x5F058808, 0xC60CD9B2, 0xB10BE924, 0x2F6F7C87, 0x58684C11, 0xC1611DAB, 0xB6662D3D,
	0x76DC4190, 0x01DB7106, 0x98D220BC, 0xEFD5102A, 0x71B18589, 0x06B6B51F, 0x9FBFE4A5, 0xE8B8D433,
	0x7807C9A2, 0x0F00F934, 0x9609A88E, 0xE10E9818, 0x7F6A0DBB, 0x086D3D2D, 0x91646C97, 0xE6635C01,
	0x6B6B51F4, 0x1C6C6162, 0x856530D8, 0xF262004E, 0x6C0695ED, 0x1B01A57B, 0x8208F4C1, 0xF50FC457,
	0x65B0D9C6, 0x12B7E950, 0x8BBEB8EA, 0xFCB9887C, 0x62DD1DDF, 0x15DA2D49, 0x8CD37CF3, 0xFBD44C65,
	0x4DB26158, 0x3AB551CE, 0xA3BC0074, 0xD4BB30E2, 0x4ADFA541, 0x3DD895D7, 0xA4D1C46D, 0xD3D6F4FB,
	0x4369E96A, 0x346ED9FC, 0xAD678846, 0xDA60B8D0, 0x44042D73, 0x33031DE5, 0xAA0A4C5F, 0xDD0D7CC9,
	0x5005713C, 0x270241AA, 0xBE0B1010, 0xC90C2086, 0x5768B525, 0x206F85B3, 0xB966D409, 0xCE61E49F,
	0x5EDEF90E, 0x29D9C998, 0xB0D09822, 0xC7D7A8B4, 0x59B33D17, 0x2EB40D81, 0xB7BD5C3B, 0xC0BA6CAD,
	0xEDB88320, 0x9ABFB3B6, 0x03B6E20C, 0x74B1D29A, 0xEAD54739, 0x9DD277AF, 0x04DB2615, 0x73DC1683,
	0xE3630B12, 0x94643B84, 0x0D6D6A3E, 0x7A6A5AA8, 0xE40ECF0B, 0x9309FF9D, 0x0A00AE27, 0x7D079EB1,
	0xF00F9344, 0x8708A3D2, 0x1E01F268, 0x6906C2FE, 0xF762575D, 0x806567CB, 0x196C3671, 0x6E6B06E7,
	0xFED41B76, 0x89D32BE0, 0x10DA7A5A, 0x67DD4ACC, 0xF9B9DF6F, 0x8EBEEFF9, 0x17B7BE43, 0x60B08ED5,
	0xD6D6A3E8, 0xA1D1937E, 0x38D8C2C4, 0x4FDFF252, 0xD1BB67F1, 0xA6BC5767, 0x3FB506DD, 0x48B2364B,
	0xD80D2BDA, 0xAF0A1B4C, 0x36034AF6, 0x41047A60, 0xDF60EFC3, 0xA867DF55, 0x316E8EEF, 0x4669BE79,
	0xCB61B38C, 0xBC66831A, 0x256FD2A0, 0x5268E236, 0xCC0C7795, 0xBB0B4703, 0x220216B9, 0x5505262F,
	0xC5BA3BBE, 0xB2BD0B28, 0x2BB45A92, 0x5CB36A04, 0xC2D7FFA7, 0xB5D0CF31, 0x2CD99E8B, 0x5BDEAE1D,
	0x9B64C2B0, 0xEC63F226, 0x756AA39C, 0x026D930A, 0x9C0906A9, 0xEB0E363F, 0x72076785, 0x05005713,
	0x95BF4A82, 0xE2B87A14, 0x7BB12BAE, 0x0CB61B38, 0x92D28E9B, 0xE5D5BE0D, 0x7CDCEFB7, 0x0BDBDF21,
	0x86D3D2D4, 0xF1D4E242, 0x68DDB3F8, 0x1FDA836E, 0x81BE16CD, 0xF6B9265B, 0x6FB077E1, 0x18B74777,
	0x88085AE6, 0xFF0F6A70, 0x66063BCA, 0x11010B5C, 0x8F659EFF, 0xF862AE69, 0x616BFFD3, 0x166CCF45,
	0xA00AE278, 0xD70DD2EE, 0x4E048354, 0x3903B3C2, 0xA7672661, 0xD06016F7, 0x4969474D, 0x3E6E77DB,
	0xAED16A4A, 0xD9D65ADC, 0x40DF0B66, 0x37D83BF0, 0xA9BCAE53, 0xDEBB9EC5, 0x47B2CF7F, 0x30B5FFE9,
	0xBDBDF21C, 0xCABAC28A, 0x53B39330, 0x24B4A3A6, 0xBAD03605, 0xCDD70693, 0x54DE5729, 0x23D967BF,
	0xB3667A2E, 0xC4614AB8, 0x5D681B02, 0x2A6F2B94, 0xB40BBE37, 0xC30C8EA1, 0x5A05DF1B, 0x2D02EF8D]


def tamCRC32(name: str) -> int:
    hash_value = len(name)
    for byte in name.encode('utf-8'):
        hash_value = (hash_value >> 8) ^ CRC32TABLE[byte ^ (hash_value & 0xFF)]
    return hash_value