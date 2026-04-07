if __name__ == "__main__" or __package__ is None:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "tamLib"


from .tmo import TMO
from .utils.GXT import GXT
from .lds import LDS
from .tmd0 import TMD0
from .tmo0 import TMO0
from .utils.PyBinaryReader.binary_reader import *
from enum import IntEnum
import numpy as np


# implementation of cat files found in the following games:
# - Hyperdimension Neptunia U: Action Unleashed
# - Hyperdimension Neptunia: Producing Perfection
# - MegaTagmension Blanc + Neptune VS Zombies
# - To LOVE-Ru Darkness: Battle Ecstasy
# - Natsuiro High School: Seishun Hakusho


class subCatType(IntEnum):
    Model = 0
    Texture = 1
    Animation = 2
    CameraAnimation = 3
    Script = 5
    MapData = 6
    Parameters = 8
    Binary = 9
    Names = 11


class cat(BrStruct):
    def __init__(self):
        self.subCats = []
        self.fileNames = []
        self.models = {}
        self.textures = {}
        self.mapData = {}
        self.animations = {}
        self.binaryData = {}
    def __br_read__(self, br: BinaryReader, isSubCat = False, namedSubCats = False) -> None:
        self.flags = br.read_uint32()
        self.subCatCount = br.read_uint32()
        self.catType = br.read_uint32()
        
        if self.flags & 2:
            namedSubCats = True
        
        if self.flags & 1 and not isSubCat:
            catOffsets = br.read_uint32(self.subCatCount)
            catSizes = br.read_uint32(self.subCatCount)
            catTypes = br.read_uint32(self.subCatCount)
            catSubCounts = br.read_uint32(self.subCatCount)
            
            for i in range(self.subCatCount):
                br.seek(catOffsets[i], Whence.BEGIN)
                catData = br.read_bytes(catSizes[i])
                catBuf = BinaryReader(catData)

                if catTypes[i] == subCatType.Model:
                    subCatFile = catBuf.read_struct(modelCat, None, namedSubCats)
                elif catTypes[i] == subCatType.Texture:
                    subCatFile = catBuf.read_struct(textureCat, None, namedSubCats)
                elif catTypes[i] == subCatType.Animation or catTypes[i] == subCatType.CameraAnimation:
                    subCatFile = catBuf.read_struct(animationCat, None, namedSubCats)
                elif catTypes[i] == subCatType.MapData:
                    subCatFile = catBuf.read_struct(mapDataCat, None, namedSubCats)
                elif catTypes[i] == subCatType.Binary or catTypes[i] == subCatType.Script or catTypes[i] == subCatType.Parameters:
                    subCatFile = catBuf.read_struct(binaryCat, None, namedSubCats)
                elif catTypes[i] == subCatType.Names:
                    subCatFile = catBuf.read_struct(namesCat, None, namedSubCats)
                    self.fileNames.extend(subCatFile.names)
                else:
                    print(f"Unknown subcat type {catTypes[i]} at index {i}, skipping")
                    continue
                self.subCats.append(subCatFile)
        
        else:
            headerSize = br.read_uint32()
            catOffsets = br.read_uint32(self.subCatCount)
            catSizes = br.read_uint32(self.subCatCount)
            if namedSubCats:
                nameOffsets = br.read_uint32(self.subCatCount)
            
            for i in range(self.subCatCount):
                br.seek(catOffsets[i], Whence.BEGIN)
                catData = br.read_bytes(catSizes[i])
                catBuf = BinaryReader(catData)
                subCatObj = catBuf.read_struct(cat, None, True, namedSubCats)
                self.subCats.append(subCatObj)
                
                if namedSubCats:
                    saved_pos = br.pos()
                    br.seek(nameOffsets[i], Whence.BEGIN)
                    name = br.read_str(256) 
                    self.fileNames.append(name)
                    br.seek(saved_pos, Whence.BEGIN)
        
        
        # categorize subcats and assign file names
        if self.fileNames:
            nameIndex = 0
            for subCat in self.subCats:
                if isinstance(subCat, namesCat):
                    continue
                elif isinstance(subCat, modelCat):
                    self.models.update({self.fileNames[nameIndex + i]: model for i, model in enumerate(subCat.models)})
                    nameIndex += len(subCat.models)
                elif isinstance(subCat, textureCat):
                    self.textures.update({self.fileNames[nameIndex + i]: texture for i, texture in enumerate(subCat.textureContainers)})
                    nameIndex += len(subCat.textureContainers)
                elif isinstance(subCat, animationCat):
                    self.animations.update({self.fileNames[nameIndex + i]: animation for i, animation in enumerate(subCat.animations)})
                    nameIndex += len(subCat.animations)
                elif isinstance(subCat, mapDataCat):
                    self.mapData.update({self.fileNames[nameIndex + i]: data for i, data in enumerate(subCat.data)})
                    nameIndex += len(subCat.data)
                elif isinstance(subCat, binaryCat):
                    self.binaryData.update({self.fileNames[nameIndex + i]: data for i, data in enumerate(subCat.files)})
                    nameIndex += len(subCat.files)


class modelCat(BrStruct):
    def __init__(self):
        self.models = []
        self.binaryData = []
    
    def __br_read__(self, br: BinaryReader, isSubCat=False, namedSubCats=False):
        self.flags = br.read_uint32()
        self.modelCount = br.read_uint32()
        self.catType = br.read_uint32()
        self.headerSize = br.read_uint64()
        modelOffsets = br.read_uint32(self.modelCount)
        modelSizes = br.read_uint32(self.modelCount)
        
        for i in range(self.modelCount):
            br.seek(modelOffsets[i], Whence.BEGIN)
            modelData = br.read_bytes(modelSizes[i])
            modelBuf = BinaryReader(modelData)
            try:
                model = modelBuf.read_struct(TMD0)
            except Exception as e:
                print(f"Failed to read model {i} at offset {modelOffsets[i]} with size {modelSizes[i]}")
                print(f"Error: {e}")
                self.binaryData.append(modelData)
                continue
            self.models.append(model)


class textureCat(BrStruct):
    def __init__(self):
        self.textureContainerType = "LDS"
        self.textureContainers = []
        self.binaryData = []
    
    def __br_read__(self, br: BinaryReader, isSubCat=False, namedSubCats=False) -> None:
        self.flags = br.read_uint32()
        self.textureCount = br.read_uint32()
        self.catType = br.read_uint32()
        self.headerSize = br.read_uint64()
        textureOffsets = br.read_uint32(self.textureCount)
        textureSizes = br.read_uint32(self.textureCount)
        
        for i in range(self.textureCount):
            br.seek(textureOffsets[i], Whence.BEGIN)
            textureData = br.read_bytes(textureSizes[i])
            textureBuf = BinaryReader(textureData)
            
            #we'll read the first 4 bytes to determine the type of texture container
            try:
                textureMagic = textureBuf.read_str(4)
            except Exception as e:
                textureMagic = ""
            if textureMagic == "GXT":
                self.textureContainerType = "GXT"
                
                textureBuf.seek(0, Whence.BEGIN)
                texture = textureBuf.read_struct(GXT)
                self.textureContainers.append(texture)
                
            elif textureMagic == "GNF":
                self.textureContainerType = "GNF"
                #GNF not implemented yet, we'll just store the raw data for now
                self.binaryData.append(textureData)
                
            else:
                # we'll assume that it's LDS (texture container for PC)
                textureBuf.seek(0, Whence.BEGIN)
                try:
                    texture = textureBuf.read_struct(LDS)
                    self.textureContainers.append(texture)
                    self.textureContainerType = "LDS"
                except Exception as e:
                    print(f"Failed to read LDS texture: {e}")
                    self.binaryData.append(textureData)
        
        
                
            
            

class animationCat(BrStruct):
    def __init__(self):
        self.animations = []
        self.binaryData = []
    
    def __br_read__(self, br: BinaryReader, isSubCat=False, namedSubCats=False) -> None:
        self.flags = br.read_uint32()
        self.animationCount = br.read_uint32()
        self.catType = br.read_uint32()
        self.headerSize = br.read_uint64()
        animationOffsets = br.read_uint32(self.animationCount)
        animationSizes = br.read_uint32(self.animationCount)
        
        for i in range(self.animationCount):
            br.seek(animationOffsets[i], Whence.BEGIN)
            animationData = br.read_bytes(animationSizes[i])
            animationBuf = BinaryReader(animationData)
            try:
                animation = animationBuf.read_struct(TMO0)
            except Exception as e:
                print(f"Failed to read animation {i} at offset {animationOffsets[i]} with size {animationSizes[i]}")
                print(f"Error: {e}")
                self.binaryData.append(animationData)
                continue
            self.animations.append(animation)


class mapDataCat(BrStruct):
    def __init__(self):
        self.data = []
    
    def __br_read__(self, br: BinaryReader, isSubCat=False, namedSubCats=False) -> None:
        self.flags = br.read_uint32()
        self.fileCount = br.read_uint32()
        self.catType = br.read_uint32()
        self.headerSize = br.read_uint64()
        fileOffsets = br.read_uint32(self.fileCount)
        fileSizes = br.read_uint32(self.fileCount)
        
        for i in range(self.fileCount):
            br.seek(fileOffsets[i], Whence.BEGIN)
            fileData = br.read_bytes(fileSizes[i])
            self.data.append(fileData)


class binaryCat(BrStruct):
    def __init__(self):
        self.files = []
    
    def __br_read__(self, br: BinaryReader, isSubCat=False, namedSubCats=False):
        self.flags = br.read_uint32()
        self.fileCount = br.read_uint32()
        self.catType = br.read_uint32()
        self.headerSize = br.read_uint64()
        fileOffsets = br.read_uint32(self.fileCount)
        fileSizes = br.read_uint32(self.fileCount)
        for i in range(self.fileCount):
            br.seek(fileOffsets[i], Whence.BEGIN)
            fileData = br.read_bytes(fileSizes[i])
            self.files.append(fileData)


class namesCat(BrStruct):
    def __init__(self):
        self.names = []
        
    def __br_read__(self, br: BinaryReader, isSubCat=False, namedSubCats=False) -> None:
        self.flags = br.read_uint32()
        self.fileCount = br.read_uint32()
        self.catType = br.read_uint32()
        self.headerSize = br.read_uint64()
        fileOffsets = br.read_uint32(self.fileCount)
        fileSizes = br.read_uint32(self.fileCount)
        
        for i in range(self.fileCount):
            br.seek(fileOffsets[i], Whence.BEGIN)
            namesFile = BinaryReader(br.read_bytes(fileSizes[i]))
            nameCount = namesFile.read_uint32()
            unk = namesFile.read_uint32()
            maxNameLength = namesFile.read_uint32()
            unk2 = namesFile.read_uint32()
            for j in range(nameCount):
                try:
                    name = namesFile.read_str(maxNameLength)
                except Exception as e:
                    print(f"Failed to read name {j} in namesCat at offset {fileOffsets[i]} with size {fileSizes[i]}")
                    print(f"Error: {e}")
                    name = f"corrupted_name_{j}"
                self.names.append(name)



if __name__ == "__main__":
    game_path = r"G:\SteamLibrary\steamapps\common\MegaTagmension Blanc + Neptune VS Zombies"
    
    import os
    failed_files = {}
    files_counter = 0
    for root, dirs, files in os.walk(game_path):
        for file in files:
            if file.endswith(".cat"):
                file_path = os.path.join(root, file)
                files_counter += 1
                try:
                    with open(file_path, "rb") as f:
                        catObj = cat()
                        br = BinaryReader(f.read())
                        catObj.__br_read__(br, False, False)
                except Exception as e:
                    failed_files[file_path] = str(e)
    print("\nFailed files:")
    for file_path, error in failed_files.items():
        print(f"  {file_path}: {error}")
    
    print("\nSummary:")
    print(f"  Total .cat files: {files_counter}")
    print(f"  Successfully read: {files_counter - len(failed_files)}")
    print(f"  Failed to read: {len(failed_files)}")