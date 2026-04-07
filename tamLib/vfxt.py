from .utils.PyBinaryReader.binary_reader import *


class VFXT(BrStruct):
    def __init__(self):
        self.textures = []

    def __br_read__(self, br, *args):
        self.magic = br.read_str(4)
        br.seek(4,1)  # Skip 4 bytes
        textureCount = br.read_uint32()
        self.textures = br.read_struct(vfxTexture, textureCount)


class vfxTexture(BrStruct):
    def __init__(self):
        self.textureData = b""

    def __br_read__(self, br, *args):
        self.magic = br.read_str(4)
        self.totalSize = br.read_uint32()
        self.hashString = br.read_bytes(4)
        self.hashLength = br.read_uint32()
        self.hash = br.read_bytes(self.hashLength)
        self.textureType = br.read_str(4)
        self.textureSize = br.read_uint32()
        self.textureData = br.read_bytes(self.textureSize)
        br.align_pos(4)
        br.seek(12, 1)