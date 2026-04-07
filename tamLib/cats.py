from .utils.PyBinaryReader.binary_reader import *


class CATS(BrStruct):
    def __init__(self):
        self.name = ""
        self.catCount = 0
        self.subNames = []
        self.subData = []
        self.subCATS = []
    
    def __br_read__(self, br: BinaryReader) -> None:
        
        self.magic = br.read_str(4)
        if self.magic != "CATS":
            raise ValueError("Invalid CATS magic. Expected 'CATS', got: " + self.magic)
        self.unk = br.read_uint32()
        self.catCount = br.read_uint32()
        self.headersOffset = br.read_uint32()
        br.seek(self.headersOffset, Whence.CUR)
        
        for i in range(self.catCount):
            catName = br.read_str_at_offset(br.read_uint64())
            catDataOffset = br.read_uint64()
            catDataSize = br.read_uint64()
            pos = br.pos()
            br.seek(catDataOffset, Whence.BEGIN)
            catData = br.read_bytes(catDataSize)
            br.seek(pos, Whence.BEGIN)
            br.align_pos(16)
            
            #check the magic of the subcat
            subCatMagic = catData[:4].decode('utf-8')
            if subCatMagic != "CATS":
                self.subData.append(catData)
                self.subNames.append(catName)
            else:
                #we need a new buffer for each subcat
                subCatBuffer = BinaryReader(bytearray(catData))
                subCat = subCatBuffer.read_struct(CATS)
                subCat.name = catName
                self.subCATS.append(subCat)
                del subCatBuffer
            
            del catData
    
    def __br_write__(self, br: BinaryReader) -> None:
        br.write_str(self.magic)
        br.write_uint32(self.unk)
        br.write_uint32(len(self.subCATS))
        br.write_uint32(0)
            

if __name__ == "__main__":
    file = r"G:\SteamLibrary\steamapps\common\BLEACH Rebirth of Souls\00HIGH\Model\MapAssetCat\bg000_00.cat"
    with open(file, 'rb') as f:
        byte = f.read()
        br = BinaryReader(byte, Endian.LITTLE)
        cats = br.read_struct(CATS)

    print(cats.catCount)
    print(cats.subNames)