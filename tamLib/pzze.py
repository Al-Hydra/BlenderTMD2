import os
import zlib
from .utils.PyBinaryReader.binary_reader import *


class PZZEFile(BrStruct):
    def __init__(self):
        self.magic = 'PZZE'
        self.dataOffset = 24
        self.fileFormat = ''
        self.decompressedSize = 0
        self.compressedData = b''
        self.decompressedData = b''
    
    def __br_read__(self, br: BinaryReader, *args) -> None:
        self.magic = br.read_str(4)
        if self.magic != 'PZZE':
            print(f"{self.magic} is not a PZZE file.")
            return None
        
        self.fileFormat = br.read_str(4)
        self.decompressedSize = br.read_uint64()
        self.dataOffset = br.read_uint64()
        self.compressedData = br.buffer()[self.dataOffset:]
    
    def __br_write__(self, br: BinaryReader) -> None:
        br.write_str_fixed(self.magic, 4)
        br.write_str_fixed(self.fileFormat, 4)
        br.write_uint64(len(self.decompressedData))
        br.write_uint64(24)
        br.write_bytes(self.compress())
        
    def decompress(self):
        if self.compressedData:
            try:
                self.decompressedData = zlib.decompress(self.compressedData)
            except zlib.error:
                print(f"Decompression failed.")
                return None
        else:
            print(f"No compressed data found.")
            return None
        return self.decompressedData
    
    def compress(self):
        if self.decompressedData:
            try:
                self.compressedData = zlib.compress(self.decompressedData)
            except zlib.error:
                print(f"Compression failed.")
                return None
        else:
            print(f"No decompressed data found.")
            return None
        return self.compressedData


def readPZZE(path):
    with open(path, "rb") as f:
        br = BinaryReader(f.read())
        pzze = br.read_struct(PZZEFile)
        return pzze


if __name__ == "__main__":
    pass
