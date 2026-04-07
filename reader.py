from .tamLib.pzze import *
from .tamLib.utils.PyBinaryReader.binary_reader import *
from .tamLib.tmd import *
from .tamLib.tmd2 import *
from .tamLib.lds import *
from .tamLib.cats import *
from .tamLib.tmo import *
from .tamLib.tmd0 import *
from .tamLib.tmdv import *
from .tamLib.vfxt import *
from .tamLib.tactpkg import *
import os


def readTMD2(file: str) -> TMD2:
    with open(file, 'rb') as f:
        #read magic
        magic = f.read(4).decode('utf-8')
        f.seek(0)  # Reset file pointer to the beginning for reading the TMD2 data
        if magic == "PZZE":
            pzze = readPZZE(file)
            
            tmd_data = pzze.decompress()
            if tmd_data is None:
                raise ValueError("Failed to decompress TMD2 data.")
            if not tmd_data.startswith(b'tmd0'):
                raise ValueError("Invalid TMD2 magic.")
        else:
            tmd_data = f.read()
            tmd_magic = tmd_data[:4].decode('utf-8')
            if tmd_magic != "tmd0":
                raise ValueError("Invalid TMD2 magic. Expected 'tmd0', got: " + tmd_magic)
        
        br = BinaryReader(tmd_data, Endian.LITTLE)
        
        file_name = os.path.splitext(os.path.basename(file))[0]
        
        tmd2 = br.read_struct(TMD2, None, file_name)
        return tmd2


def readTMD(file: str, texture_names = {}):
    with open(file, 'rb') as f:
        #read magic
        magic = f.read(4).decode('utf-8')
        f.seek(0)  # Reset file pointer to the beginning for reading the TMD2 data
        if magic == "PZZE":
            pzze = readPZZE(file)
            
            tmd_data = pzze.decompress()
            if tmd_data is None:
                raise ValueError("Failed to decompress TMD2 data.")
            if not tmd_data.startswith(b'tmd0'):
                raise ValueError("Invalid TMD2 magic.")
        else:
            tmd_data = f.read()
            tmd_magic = tmd_data[:4].decode('utf-8')
            if tmd_magic != "tmd0":
                raise ValueError("Invalid TMD2 magic. Expected 'tmd0', got: " + tmd_magic)
        
        br = BinaryReader(tmd_data, Endian.LITTLE)
        
        file_name = os.path.splitext(os.path.basename(file))[0]
        
        tmd = br.read_struct(TMD, None, file_name, texture_names)
        return tmd


def readTMD0(file: str, texture_names = {}):
    with open(file, 'rb') as f:
        #read magic
        magic = f.read(4).decode('utf-8')
        f.seek(0)  # Reset file pointer to the beginning for reading the TMD2 data
        if magic == "PZZE":
            pzze = readPZZE(file)
            
            tmd_data = pzze.decompress()
            if tmd_data is None:
                raise ValueError("Failed to decompress TMD0 data.")
            if not tmd_data.startswith(b'tmd0') or not tmd_data.startswith(b'0dmt'):
                raise ValueError("Invalid TMD0 magic.")
        else:
            tmd_data = f.read()
            tmd_magic = tmd_data[:4].decode('utf-8')
            if tmd_magic != "tmd0" and tmd_magic != "0dmt":
                raise ValueError("Invalid TMD0 magic. Expected 'tmd0', got: " + tmd_magic)
        
        br = BinaryReader(tmd_data, Endian.LITTLE)
        
        file_name = os.path.splitext(os.path.basename(file))[0]

        tmd = br.read_struct(TMD0, None, file_name, texture_names)
        return tmd


def readTMDV(file: str):
    with open(file, 'rb') as f:
        magic = f.read(4).decode('utf-8')
        f.seek(0)
        if magic == "PZZE":
            pzze = readPZZE(file)
            tmd_data = pzze.decompress()
            if tmd_data is None:
                raise ValueError("Failed to decompress TMDV data.")
        else:
            tmd_data = f.read()
            tmd_magic = tmd_data[:4].decode('utf-8')
            if tmd_magic != "tmdv" and tmd_magic != "vdmt":
                raise ValueError("Invalid TMDV magic. Expected 'tmdv', got: " + tmd_magic)

        br = BinaryReader(tmd_data, Endian.LITTLE)
        file_name = os.path.splitext(os.path.basename(file))[0]
        tmd = br.read_struct(TMDV, None, file_name)
        return tmd


def readLDS(file: str) -> LDS:
    with open(file, 'rb') as f:
        #read magic
        magic = f.read(4).decode('utf-8')
        f.seek(0)  # Reset file pointer to the beginning for reading the LDS data
        if magic == "PZZE":
            pzze = readPZZE(file)
            
            lds_data = pzze.decompress()
            if lds_data is None:
                raise ValueError("Failed to decompress LDS data.")

        else:
            lds_data = f.read()
        
    file_name = os.path.splitext(os.path.basename(file))[0]
    br = BinaryReader(lds_data, Endian.LITTLE)    
    lds = br.read_struct(LDS, None, file_name)
    return lds


def readVFXT(file: str) -> VFXT:
    with open(file, 'rb') as f:
        #read magic
        magic = f.read(4).decode('utf-8')
        f.seek(0)  # Reset file pointer to the beginning for reading the VFXT data
        if magic == "PZZE":
            pzze = readPZZE(file)

            vfx_data = pzze.decompress()
            if vfx_data is None:
                raise ValueError("Failed to decompress VFXT data.")

        else:
            vfx_data = f.read()

    file_name = os.path.splitext(os.path.basename(file))[0]
    br = BinaryReader(vfx_data, Endian.LITTLE)
    vfx = br.read_struct(VFXT, None, file_name)
    return vfx


def readCATS(file: str) -> CATS:
    with open(file, 'rb') as f:
        magic = f.read(4).decode('utf-8')
        f.seek(0)  # Reset file pointer to the beginning for reading the CATS data
        if magic == "PZZE":
            pzze = readPZZE(file)
            
            cats_data = pzze.decompress()
            if cats_data is None:
                raise ValueError("Failed to decompress CAT data.")
            if not cats_data.startswith(b'CATS'):
                raise ValueError("Invalid CATS magic.")
            
            
        else:
            cats_data = f.read()
            
        br = BinaryReader(cats_data, Endian.LITTLE)
        cats = br.read_struct(CATS)
        return cats


def readActorPackage(file: str):
    with open(file, 'rb') as f:
        magic = f.read(4).decode('utf-8')
        f.seek(0)  # Reset file pointer to the beginning for reading the ActorPackage data
        if magic == "PZZE":
            pzze = readPZZE(file)
            
            ap_data = pzze.decompress()
            if ap_data is None:
                raise ValueError("Failed to decompress ActorPackage data.")
            if not ap_data.startswith(b'actmng_pkg'):
                raise ValueError("Invalid ActorPackage magic.")
            
            
        else:
            ap_data = f.read()
            
        br = BinaryReader(ap_data, Endian.LITTLE)
        ap = br.read_struct(TactPkg)
        return ap


def readTMO(file: str) -> TMO:
    with open(file, 'rb') as f:
        magic = f.read(4).decode('utf-8')
        f.seek(0)  # Reset file pointer to the beginning for reading the CATS data
        if magic == "PZZE":
            pzze = readPZZE(file)
            
            tmo_data = pzze.decompress()
            if tmo_data is None:
                raise ValueError("Failed to decompress TMO data.")
            if not tmo_data.startswith(b'tmo1'):
                raise ValueError("Invalid TMO magic.")
            
        else:
            tmo_data = f.read()
        
        file_name = os.path.splitext(os.path.basename(file))[0]
        br = BinaryReader(tmo_data, Endian.LITTLE)
        tmo = br.read_struct(TMO)
        tmo.name = file_name
        return tmo


def writeTMD2(tmd2, output, compress = False):
    br = BinaryReader()
    br.write_struct(tmd2)
    
    filebytes = bytes(br.buffer())
    
    if compress:
        pzze = PZZEFile()
        pzze.fileFormat = 'tmd2'
        pzze.decompressedData = filebytes
        
        br = BinaryReader()
        br.write_struct(pzze)
        
        filebytes = bytes(br.buffer())
    
    with open(output, "wb") as f:
        f.write(filebytes)


def writeTMD(tmd, output):
    br = BinaryReader()
    br.write_struct(tmd)
    
    filebytes = bytes(br.buffer())
    
    with open(output, "wb") as f:
        f.write(filebytes)
        

def writeLDS(lds, output, compress = False):
    br = BinaryReader()
    br.write_struct(lds)
    filebytes = bytes(br.buffer())
    if compress:
        pzze = PZZEFile()
        pzze.fileFormat = 'lds'
        pzze.decompressedData = filebytes
        
        br = BinaryReader()
        br.write_struct(pzze)
        
        filebytes = bytes(br.buffer())
    
    with open(output, "wb") as f:
        f.write(filebytes)

if __name__ == "__main__":
    path = r"G:\Dev\BlenderTMD2\pl000_cos00_00.tmd2"
    output = r"G:\Dev\BlenderTMD2\test.tmd2"
    
    tmd = readTMD2(path)
    
    bw = BinaryReader()
    bw.write_struct(tmd)
    
    with open(output, "wb") as f:
        f.write(bytes(bw.buffer()))
    
    print("done")