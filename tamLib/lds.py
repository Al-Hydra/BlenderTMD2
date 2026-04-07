from .utils.PyBinaryReader.binary_reader import *


class LDS(BrStruct):
    
    def __init__(self):
        self.name = ""
        self.textureCount = 0
        self.textures = []
        self.unk = 0
    
    def __br_read__(self, br: BinaryReader, file_name = "") -> None:
        self.name = file_name
        self.dataStart = br.read_uint32()
        self.textureCount = br.read_uint32()
        self.fileSize = br.read_uint32()
        
        offsets = []
        
        for i in range(self.textureCount):
            offsets.append(br.read_uint32())
        
        
        pos = br.pos()
        for i in range(self.textureCount):
            br.seek(offsets[i] + pos, Whence.BEGIN)
            
            if i != self.textureCount - 1:
                textureSize = offsets[i + 1] - offsets[i]
                self.textures.append(br.read_bytes(textureSize))
            else:
                textureSize = br.size() - offsets[i] - pos
                self.textures.append(br.read_bytes(textureSize))
        
        
    def __br_write__(self, br: BinaryReader, *args) -> None:
        dataStart = ((len(self.textures) - 1) * 4) + 16
        br.write_uint32(dataStart)
        br.write_uint32(len(self.textures))
        
        sizePos = br.pos()
        br.write_uint32(0)
        
        texturesBuffer = BinaryReader()
        for i in range(len(self.textures)):
            br.write_uint32(texturesBuffer.size())
            texturesBuffer.write_bytes(self.textures[i])
        br.extend(texturesBuffer.buffer())
        br.seek(texturesBuffer.size())
        
        del texturesBuffer
        
        br.seek(sizePos)
        br.write_uint32(br.size())

