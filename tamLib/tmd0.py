from .utils.PyBinaryReader.binary_reader import *
from .pzze import readPZZE
import numpy as np
from itertools import chain
import struct

class TMD0(BrStruct):

    def __init__(self) -> None:
        self.magic = 'tmd0'
        self.name = ""
        self.version = 0x100
        self.modelFlags = 0
        
        self.bones = []
        self.models = []
        self.indexTables = []
        self.textures = []
        
        self.unkBoneInfo = []
        
    def __br_read__(self, br: 'BinaryReader', file_name = "", texture_names = {}) -> None:

        self.magic = br.read_str(4)
        if self.magic == 'tmd0':
            br.set_endian(Endian.LITTLE)
            self.endian = '<'
        elif self.magic == '0dmt':
            br.set_endian(Endian.BIG)
            self.endian = '>'
        else:
            raise ValueError("Invalid TMD magic. Expected 'tmd0' or '0dmt', got: " + self.magic)

        
        if file_name:
            self.name = file_name
        
        unk0 = br.read_uint16()
        self.modelFlags = br.read_uint16()
        self.animFlag = br.read_uint16()
        self.version = br.read_uint16()
        headerSize = br.read_uint16()
        self.frameCount = br.read_int16()
        
        
        self.boundingBox = br.read_float32(6)
        self.modelsOffset = br.read_uint32()
        self.modelCount = br.read_uint32()
        self.subMeshEntriesOffset = br.read_uint32()
        self.subMeshEntriesCount = br.read_uint32()
        self.stringsOffset = br.read_uint32()
        self.stringsCount = br.read_uint32()
        
        self.indexTablesOffset = br.read_uint32()
        self.indexTablesCount = br.read_uint32()
        
        self.materialsOffset = br.read_uint32()
        self.materialCount = br.read_uint32()
        self.subMeshOffset = br.read_uint32()
        self.subMeshCount = br.read_uint32()
        self.trianglesOffset = br.read_uint32()
        self.trianglesCount = br.read_uint32()
        self.vertexCount = br.read_uint32()
        self.verticesOffset = br.read_uint32()
        
        self.uselessOffsets = br.read_uint32(7)
        
        self.boneMatrixOffset = br.read_uint32()
        self.boneMatrixCount = br.read_uint32()
        self.boneHierarchyOffset = br.read_uint32()
        self.bonesCount = br.read_uint32()
        self.texturesOffset = br.read_uint32()
        self.textureCount = br.read_uint32()

        
        #Textures Info
        br.seek(self.texturesOffset, Whence.BEGIN)
        self.textures = br.read_struct(TMDTexture, self.textureCount, texture_names)
        #Material Info
        br.seek(self.materialsOffset, Whence.BEGIN)
        self.materials = br.read_struct(TMDMaterial, self.materialCount, self.textures)


        # Determine vertex attributes based on flags
        vertex_attributes = []
        if self.modelFlags & 0x2:
            vertex_attributes.append(('position', f'{self.endian}3f4'))

        if self.modelFlags & 0x800:
            vertex_attributes.append(('boneWeights', f'{self.endian}4u1'))
            vertex_attributes.append(('boneIDs', f'{self.endian}4u1'))

        if self.modelFlags & 0x4:
            vertex_attributes.append(('normal', f'{self.endian}4u1'))

        if self.modelFlags & 0x20:
            vertex_attributes.append(('color', f'{self.endian}4u1'))

        if self.modelFlags & 0x40:
            vertex_attributes.append(('uv', f'{self.endian}2i2'))



        # Read vertex buffer
        br.seek(self.verticesOffset, Whence.BEGIN)
        npVertexAtt = np.dtype(vertex_attributes)
        self.vertices = br.read_structured_array(npVertexAtt, self.vertexCount)
        
        newDataTypesMap = {
            'position': '3f4',
            'boneWeights': '4f4',
            'boneIDs': '4u4',
            'normal': '3f4',
            'color': '4f4',
            'uv': '2f4',
        }
        
        # convert everything to floats
        newVertices = np.zeros(self.vertexCount, dtype=[(name, newDataTypesMap[name]) for name, _ in vertex_attributes])
        for name, _ in vertex_attributes:
            if name == 'boneWeights':
                newVertices[name] = self.vertices[name].astype(np.float32) / 255.0
            elif name == 'boneIDs':
                newVertices[name] = self.vertices[name].astype(np.uint32)
            elif name in ['normal']:
                vec = self.vertices[name].astype(np.float32) / 255.0 * 2.0 - 1.0
                norm = np.linalg.norm(vec, axis=1, keepdims=True)
                norm[norm == 0] = 1
                vec = vec / norm
                newVertices[name] = vec[:, :3]  # we don't need the w component for these
            elif name == 'color':
                newVertices[name] = self.vertices[name].astype(np.float32) / 255.0
            elif name == 'uv':
                newVertices[name] = self.vertices[name].astype(np.float32) / 1024.0
            else:
                newVertices[name] = self.vertices[name].astype(np.float32)
        
        self.vertices = newVertices

        # Read triangle info
        br.seek(self.trianglesOffset, Whence.BEGIN)
        triBuffer = br.read_bytes(self.trianglesCount * 2 * 3)
        self.triangles = np.frombuffer(triBuffer, dtype=f"{self.endian}u2").reshape(-1, 3)


        #pass the indices list to the index table class and read the individual index tables
        br.seek(self.indexTablesOffset, Whence.BEGIN)
        self.indexTables = br.read_struct(TMDIndexTable, self.indexTablesCount)
        
        if not self.indexTables:
            genericIndexTable = TMDIndexTable()
            genericIndexTable.indices = [i for i in range(self.bonesCount)]
            self.indexTables = [genericIndexTable]
        
        #read the matrix info
        br.seek(self.boneMatrixOffset, Whence.BEGIN)
        matrixBuf = br.read_bytes(self.boneMatrixCount * 64)
        self.boneMatrices = np.frombuffer(matrixBuf, dtype=f"{self.endian}f4").reshape(self.boneMatrixCount, 4, 4)
        
        # read skeleton info
        br.seek(self.boneHierarchyOffset, Whence.BEGIN)
        self.bones = [br.read_struct(TMDBone, None, self.boneMatrices[i], self.stringsOffset) for i in range(self.bonesCount)]
            
        br.seek(self.subMeshEntriesOffset, Whence.BEGIN)
        self.submeshEntries = br.read_struct(TMDSubmeshEntry,self.subMeshEntriesCount)
        
        br.seek(self.subMeshOffset, Whence.BEGIN)
        self.submeshes = br.read_struct(TMDSubmesh,self.subMeshCount, self.triangles, self.vertices)
        
        #read model info
        br.seek(self.modelsOffset, Whence.BEGIN)
        self.models = br.read_struct(TMDModel, self.modelCount, self.indexTables, self.submeshEntries, self.submeshes, self.materials, self.stringsOffset)
                
        

class TMDModel(BrStruct):
    def __init__(self) -> None:
        self.boundingBox = [0,0,0,0,0,0]
        self.meshes = []
        self.materials = []
        self.name = ""
        self.hash = 0
        self.hashFlag = 0
        self.nameFlag = 0
    
    def __br_read__(self, br: 'BinaryReader', indexTables, entries, submeshes, materials, namesOffset) -> None:
        self.boundingBox = br.read_float32(6)
        self.entryStart = br.read_uint32()
        self.entriesCount = br.read_uint16()
        self.unk = br.read_uint16()
        self.name = "mesh"
        
        materialIdx = -1
        indexTable = indexTables[0] if indexTables else TMDIndexTable()
        
        for entry in entries[self.entryStart: self.entryStart + self.entriesCount]:
            if entry.type == 32:
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
        self.trianglesCount = br.read_uint16()
        self.trianglesOffset = br.read_uint16()
        self.trianglesStart = br.read_uint32()
        
        self.triangles = triangles[self.trianglesStart : self.trianglesStart + self.trianglesCount]
        
        

class TMDSubmeshEntry(BrStruct):
    def __init__(self):
        self.type = None
        self.index = -1
    
    def __br_read__(self, br, *args):
        flags = br.read_uint16()
        self.index = flags & 0xFF
        self.type = (flags >> 8) & 0xFF


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
        self.index = br.read_uint32()
        self.flag = br.read_uint32()
        self.hash = br.read_uint32()
        self.width = br.read_uint16()
        self.height = br.read_uint16()
        
        

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

class TMDMaterial(BrStruct):
    def __init__(self) -> None:
        self.hash = 0
        self.name = ''
        self.shaderID = ""
        self.textures = []
        self.shaderParams = []
        self.unk = -1

    def __br_read__(self, br: 'BinaryReader', textures) -> None:
        self.paramCount = br.read_uint32()
        self.unk = br.read_int32()
        self.textureIndex = br.read_uint32()
        
        matTexture = TMDMatTexture()
        matTexture.textureIndex = self.textureIndex
        matTexture.texture = textures[self.textureIndex] if self.textureIndex < len(textures) else None
        
        self.textures.append(matTexture)
        self.unkFloats = br.read_float32(41)
        self.shaderID = br.read_str(4)
        self.shaderParams = br.read_float32(self.paramCount)



class TMDBone(BrStruct):
    def __init__(self) -> None:
        self.name = ''
        self.parentIndex = 0
        self.posedLocation = [0.0, 0.0, 0.0]
        self.matrix = np.zeros((4, 4), dtype=np.float32)
        self.extra = -1
        self.offset = [0,0,0]

    def __br_read__(self, br: 'BinaryReader', matrix, namesOffset = -1) -> None:
        self.hash = br.read_uint32()
        self.posedLocation = br.read_float32(3)
        self.parentIndex = br.read_int32()
        
        self.matrix = matrix
        
        self.unk1 = br.read_uint16()
        self.nameOffset = br.read_uint16()
        self.name = str(self.hash)
    

class TMDIndexTable(BrStruct):
    def __init__(self):
        self.indices = []
        self.indicesCount = 0
    
    def __br_read__(self, br):

        # tmd 0x100 seems to have a fixed size of 32 indices and only the amount specfied is used while the rest might be garbage data
        self.indicesCount = br.read_uint32()
        self.indices = br.read_uint32(32)[:self.indicesCount]

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