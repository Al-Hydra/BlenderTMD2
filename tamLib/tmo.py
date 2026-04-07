from .utils.PyBinaryReader.binary_reader import *
import numpy as np

class TMO(BrStruct):
    def __init__(self):
        self.name = ""
        self.magic = ""
        self.offset = 0
        self.flag1 = 0
        self.flag2 = 0
        self.scale = 0.0
        self.camera = None
        self.flag3 = 0
        self.framesOffset = 0
        self.unk = 0
        self.boneHashesOffset = 0
        self.fCurvesCount = 0
        self.fCurvesOffset = 0
        self.keyframeCount = 0
        self.keyframeOffset = 0
        self.frameCount = 0
        self.boneCount = 0
        self.hashes = []
        self.fCurves = []
        self.keyframes = []
    
    def __br_read__(self, br: BinaryReader) -> None:
        self.magic = br.read_str(4)
        self.offset = br.read_uint32()
        self.flag1 = br.read_uint16()
        self.flag2 = br.read_uint16()
        self.scale = br.read_float32()

        # Camera data block
        if self.flag2 & 16:
            self.camera = {
                'location':       br.read_float32(3),
                'scale':          br.read_float32(3),
                'rotation':       br.read_float32(4),
                'resolution':     br.read_float32(2),
                'aspectRatio':    br.read_float32(),
                'clipNear':       br.read_float32(),
                'clipFar':        br.read_float32(),
                'baseFOVRad':     br.read_float32(),
                'sensorHeight':   br.read_float32(),
                'FOV':            br.read_float32(),
                'projectionScale':br.read_float32(),
                'focalLength_mm': br.read_float32(),
            }

        if self.flag1 & 1:
            self.flag3 = br.read_uint32()
            self.framesOffset = br.read_uint32()
            br.align_pos(16)
            self.unk = br.read_uint64()
            self.boneHashesOffset = br.read_uint32()
            self.fCurvesCount = br.read_uint32()
            self.fCurvesOffset = br.read_uint32()
            self.keyframeCount = br.read_uint32()
            self.keyframeOffset = br.read_uint32()
            br.align_pos(16)

            # Frame and bone counts
            br.seek(self.framesOffset, Whence.BEGIN)
            self.frameCount = br.read_uint16()
            self.boneCount = br.read_uint16()

            # Bone hashes
            br.seek(self.boneHashesOffset, Whence.BEGIN)
            self.hashes = br.read_uint32(self.boneCount)

            # fCurves: uint startFrame, uint frameCount, uint lastFrame
            br.seek(self.fCurvesOffset, Whence.BEGIN)
            dtype = np.dtype([('startFrame', '<u4'), ('frameCount', '<u4'), ('lastFrame', '<u4')])
            self.fCurves = br.read_structured_array(dtype, self.fCurvesCount)

            # Keyframes: ushort frame, ushort lastFrame, float value
            br.seek(self.keyframeOffset, Whence.BEGIN)
            dtype = np.dtype([('frame', '<u2'), ('lastFrame', '<u2'), ('value', '<f4')])
            self.keyframes = br.read_structured_array(dtype, self.keyframeCount)

        else:
            # fCurves: uint64 startFrame, uint frameCount, uint lastFrame
            br.seek(self.fCurvesOffset, Whence.BEGIN)
            dtype = np.dtype([('startFrame', '<u8'), ('frameCount', '<u4'), ('lastFrame', '<u4')])
            self.fCurves = br.read_structured_array(dtype, self.fCurvesCount)

            # Keyframes: ushort frame, short value (divide by 1000.0 when using)
            br.seek(self.keyframeOffset, Whence.BEGIN)
            dtype = np.dtype([('frame', '<u2'), ('value', '<i2')])
            self.keyframes = br.read_structured_array(dtype, self.keyframeCount)


if __name__ == "__main__":
    # Example usage
    tmo_path = r"C:\Users\Hydra\Desktop\anim.tmo"
    
    with open(tmo_path, "rb") as f:
        data = f.read()
        br = BinaryReader(data)
        tmo = TMO()
        tmo.__br_read__(br)
        print(tmo.hashes)
        print(tmo.offsets)
        print(tmo.keyframes)