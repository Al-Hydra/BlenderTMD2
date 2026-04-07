from .utils.PyBinaryReader.binary_reader import *
import os

# implementation of cat files found in the following games:
# - Senran Kagura: Estival Versus
# - Senran Kagura: Burst ReNewal
# - Senran Kagura: Reflexions
# - Senran Kagura: Peach Ball
# - Senran Kagura: Peach Beach Splash
# - Gintama Rumble


class CAT(BrStruct):
    def __init__(self):
        self.name = ""
        self.catType = 0
        self.subCatCount = 0
        self.flags = 0
        self.content = []
        
    def __br_read__(self, br: BinaryReader, file_name = "") -> None:
        self.name = file_name
        self.flags = br.read_uint32()
        self.contentCount = br.read_uint32()
        self.catType = br.read_uint32()

        offsets = br.read_uint32(self.contentCount)
        sizes = br.read_uint32(self.contentCount)
        
        self.types = br.read_uint32(self.contentCount)
        self.subContentCounts = br.read_uint32(self.contentCount)
        if self.flags & 2:
            nameOffsets = br.read_uint32(self.contentCount)
        
        for i in range(self.contentCount):
            br.seek(offsets[i], Whence.BEGIN)
            
            catData = br.read_bytes(sizes[i])
            
            catBuf = BinaryReader(catData)
            subCat = catBuf.read_struct(subCAT, None, file_name, self.flags)

            
            self.content.append(subCat)


class subCAT(BrStruct):
    def __init__(self):
        self.content = []
        
        
    def __br_read__(self, br: BinaryReader, file_name = "", parentFlags = 0) -> None:
        self.name = file_name
        self.flags = br.read_uint32()
        self.contentCount = br.read_uint32()
        self.catType = br.read_uint32()
        self.headerSize = br.read_uint64()

        offsets = br.read_uint32(self.contentCount)
        sizes = br.read_uint32(self.contentCount)
        
        
        if parentFlags & 2:
            nameOffsets = br.read_uint32(self.contentCount)
        
        for i in range(self.contentCount):
            br.seek(offsets[i], Whence.BEGIN)
            
            catData = br.read_bytes(sizes[i])
            if parentFlags & 2:
                br.seek(nameOffsets[i], Whence.BEGIN)
                catName = br.read_str()
            else:
                catName = file_name
            
            if self.catType == 0 and self.headerSize > 16:
                catBuf = BinaryReader(catData)
                subCat = catBuf.read_struct(CAT, None, catName)
            else:
                subCat = catData
            
            self.content.append(subCat)

class catTextures(BrStruct):
    def __init__(self):
        self.content = []
        
        
    def __br_read__(self, br: BinaryReader, file_name = "", parentFlags = 0) -> None:
        self.name = file_name
        self.flags = br.read_uint32()
        self.contentCount = br.read_uint32()
        self.catType = br.read_uint32()
        self.headerSize = br.read_uint64()

        offsets = br.read_uint32(self.contentCount)
        sizes = br.read_uint32(self.contentCount)
        
        
        if parentFlags & 2:
            nameOffsets = br.read_uint32(self.contentCount)
        
        for i in range(self.contentCount):
            br.seek(offsets[i], Whence.BEGIN)
            
            catData = br.read_bytes(sizes[i])
            if parentFlags & 2:
                br.seek(nameOffsets[i], Whence.BEGIN)
                catName = br.read_str()
            else:
                catName = file_name
            
            if self.catType == 0 and self.headerSize > 16:
                catBuf = BinaryReader(catData)
                subCat = catBuf.read_struct(CAT, None, catName)
            else:
                subCat = catData
            
            self.content.append(subCat)

if __name__ == "__main__":
    tmo_path = r"F:\SteamLibrary\steamapps\common\Senran Kagura Burst ReNewal\GameData\Model\Playable\pl00_00\pl00_00_H.cat"
    file_name = os.path.splitext(os.path.basename(tmo_path))[0]
    
    def dumpCat(cat:CAT, cattype, export_path):
        if cattype == 0:
            if cat.flags & 1:
                #create a folder
                path = os.path.dirname(export_path)
                if cat.catType == 0:
                    path = os.path.join(path, cat.name)
                    os.makedirs(path, exist_ok=True)
            else:
                path = export_path
            
            for content, contentType in zip(cat.content, cat.types):
                dumpCat(content, path)
    
    with open(tmo_path, "rb") as f:
        data = f.read()
        br = BinaryReader(data)
        cat = CAT()
        cat.__br_read__(br, file_name)
        
        dumpCat(cat, 0, tmo_path)
        
        print("")