from .tamLib.pzze import readPZZE
from .tamLib.utils.PyBinaryReader.binary_reader import *
from .tamLib.tmd2 import *
from .tamLib.lds import *
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


if __name__ == "__main__":
    pass