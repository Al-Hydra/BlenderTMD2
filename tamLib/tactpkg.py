from .utils.PyBinaryReader.binary_reader import *
from .pzze import readPZZE
from.tmo import TMO

class TactPkg(BrStruct):
    def __init__(self):
        self.name = ""
        self.type = "actmng_pkg"
        self.hash = 0
        self.scripts = {} 
        self.unkPkg = {}
        self.tmoPkg = None
        self.tmvPkg = None
        self.mtlPkg = None
        self.motBlend = None
    def __br_read__(self, br: BinaryReader, name = "") -> None:
        self.type = br.read_str(10)
        
        br.seek(18, Whence.CUR)
        self.hash = br.read_uint32()
        self.pkgCount = br.read_uint32()
        
        #if self.type == "actmng_pkg":
        for i in range(self.pkgCount):
            subPkgName = br.read_str(64)
            subPkgOffset = br.read_uint32()
            subPkgSize = br.read_uint32()
            pos = br.pos()
            br.seek(subPkgOffset, Whence.BEGIN)
            
            try:
                subPkgType = br.buffer()[br.pos():br.pos()+16].rstrip(b"\x00").decode("utf-8")
            except UnicodeDecodeError:
                subPkgType = "unknown"
            
            if subPkgType not in ["acttmo_pkg", "acttmv_pkg", "actmtl_pkg", "motblend_file"]:
                self.scripts[subPkgName] = br.read_str(subPkgSize)
            else:
                subType = br.read_str(16)
                br.seek(-16, Whence.CUR)
                pkgData = br.read_bytes(subPkgSize)
                pkgBuf = BinaryReader(pkgData)
                if subType == "acttmo_pkg":
                    self.tmoPkg = pkgBuf.read_struct(TactTmo)
                    self.tmoPkg.name = subPkgName
                elif subType == "acttmv_pkg":
                    self.tmvPkg = pkgBuf.read_struct(TactTmv)
                    self.tmvPkg.name = subPkgName
                elif subType == "actmtl_pkg":
                    self.mtlPkg = pkgBuf.read_struct(TactMtl)
                    self.mtlPkg.name = subPkgName
                elif subType == "motblend_file":
                    self.motBlend = pkgBuf.read_bytes(subPkgSize)
                else:
                    print(f"Unknown sub package type: {subType}")
                    self.unkPkg[subPkgName] = pkgData

            br.seek(pos, Whence.BEGIN)


class TactTmo(BrStruct):
    def __init__(self):
        self.name = ""
        self.type = "acttmo_pkg"
        self.hash = 0
        self.tmoCount = 0
        self.tmoFiles = {}
        
    
    def __br_read__(self, br: BinaryReader) -> None:
        self.type = br.read_str(16)
        br.seek(12, Whence.CUR)
        self.hash = br.read_uint32()
        self.tmoCount = br.read_uint32()
        
        for i in range(self.tmoCount):
            tmoName = br.read_str(64)
            tmoOffset = br.read_uint32()
            tmoSize = br.read_uint32()
            pos = br.pos()
            br.seek(tmoOffset, Whence.BEGIN)
            tmoData = br.read_bytes(tmoSize)
            tmo = BinaryReader(tmoData).read_struct(TMO)
            br.seek(pos, Whence.BEGIN)
            self.tmoFiles[tmoName] = tmo

class TactTmv(BrStruct):
    def __init__(self):
        self.name = ""
        self.type = "acttmv_pkg"
        self.hash = 0
        self.tmvCount = 0
        self.tmvData = []
        
    
    def __br_read__(self, br: BinaryReader) -> None:
        self.type = br.read_str(16)
        br.seek(12, Whence.CUR)
        self.hash = br.read_uint32()
        self.tmvCount = br.read_uint32()
        
        for i in range(self.tmvCount):
            tmvName = br.read_str(64)
            tmvOffset = br.read_uint32()
            tmvSize = br.read_uint32()
            pos = br.pos()
            br.seek(tmvOffset, Whence.BEGIN)
            tmvData = br.read_bytes(tmvSize)
            br.seek(pos, Whence.BEGIN)
            self.tmvData.append((tmvName, tmvData))


class TactMtl(BrStruct):
    def __init__(self):
        self.name = ""
        self.type = "actmtl_pkg"
        self.hash = 0
        self.mtlCount = 0
        self.mtlData = []
        
    
    def __br_read__(self, br: BinaryReader) -> None:
        self.type = br.read_str(16)
        br.seek(12, Whence.CUR)
        self.hash = br.read_uint32()
        self.mtlCount = br.read_uint32()
        
        for i in range(self.mtlCount):
            mtlName = br.read_str(64)
            mtlOffset = br.read_uint32()
            mtlSize = br.read_uint32()
            pos = br.pos()
            br.seek(mtlOffset, Whence.BEGIN)
            mtlData = br.read_bytes(mtlSize)
            br.seek(pos, Whence.BEGIN)
            self.mtlData.append((mtlName, mtlData))
            

if __name__ == "__main__":
    filepath = r"G:\SteamLibrary\steamapps\common\BLEACH Rebirth of Souls\Motion\pl003.tactpkg"
    file_name = filepath.split("\\")[-1]
    file_name = file_name.split(".")[0]
    with open(filepath, "rb") as f:
        #read 4 first bytes to check if it's a tactpkg file
        magic = f.read(4).decode('utf-8')
        if magic == "PZZE":
            compressed = readPZZE(filepath)
            
            uncompressed = compressed.decompress()

            br = BinaryReader(uncompressed)
            tactpkg = br.read_struct(TactPkg, None, file_name)
        
        else:
            f.seek(0)
        
            br = BinaryReader(f.read())
            tactpkg = br.read_struct(TactPkg, None, file_name)
        print(tactpkg)
        