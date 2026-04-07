from .PyBinaryReader.binary_reader import *
from enum import IntEnum
import numpy as np
import struct


class GxtTextureType(IntEnum):
    Swizzled      = 0x00
    CubeMap       = 0x40
    Linear        = 0x60
    Tiled         = 0x80
    LinearStrided = 0x0C


class GxtPixelFormat(IntEnum):
    PVRT2BPP   = 0x80000000
    PVRT4BPP   = 0x81000000
    PVRTII2BPP = 0x82000000
    PVRTII4BPP = 0x83000000
    UBC1_DXT1  = 0x85000000
    UBC2_DXT3  = 0x86000000
    UBC3_DXT5  = 0x87000000
    ARGB1555   = 0x00040010
    ARGB4444   = 0x10000000
    ARGB8888   = 0x0C001000
    XRGB_888   = 0x0C005000
    RGB888     = 0x98001000
    RGB565     = 0x05001000
    RGB555     = 0x04005000
    RGB444     = 0x02001000


# (bpp, block_width, block_height)
_FORMAT_INFO = {
    GxtPixelFormat.PVRT2BPP:   (2,  8, 4),
    GxtPixelFormat.PVRT4BPP:   (4,  4, 4),
    GxtPixelFormat.PVRTII2BPP: (2,  8, 4),
    GxtPixelFormat.PVRTII4BPP: (4,  4, 4),
    GxtPixelFormat.UBC1_DXT1:  (4,  4, 4),
    GxtPixelFormat.UBC2_DXT3:  (8,  4, 4),
    GxtPixelFormat.UBC3_DXT5:  (8,  4, 4),
    GxtPixelFormat.ARGB1555:   (16, 1, 1),
    GxtPixelFormat.ARGB4444:   (16, 1, 1),
    GxtPixelFormat.ARGB8888:   (32, 1, 1),
    GxtPixelFormat.XRGB_888:   (32, 1, 1),
    GxtPixelFormat.RGB888:     (24, 1, 1),
    GxtPixelFormat.RGB565:     (16, 1, 1),
    GxtPixelFormat.RGB555:     (16, 1, 1),
    GxtPixelFormat.RGB444:     (16, 1, 1),
}


def _build_morton_lut(tile_w: int, tile_h: int) -> np.ndarray:
    """Return an index array where result[t] = morton_index(t) for all t."""
    n = tile_w * tile_h
    t = np.arange(n, dtype=np.uint32)
    p = t.copy()
    ddx = np.uint32(1)
    ddy = np.uint32(tile_w)
    q = np.zeros(n, dtype=np.uint32)
    h = tile_h
    w = tile_w
    for _ in range(16):
        h >>= 1
        if h:
            q |= np.where(p & 1, ddy, np.uint32(0)).astype(np.uint32)
            p >>= 1
        ddy = np.uint32(ddy << 1)
        w >>= 1
        if w:
            q |= np.where(p & 1, ddx, np.uint32(0)).astype(np.uint32)
            p >>= 1
        ddx = np.uint32(ddx << 1)
    return q


def unswizzle_psvita(pixel_data: bytes, img_width: int, img_height: int, bpp: int,
                     block_width: int = 1, block_height: int = 1) -> bytes:
    if bpp == 1:
        block_data_size = (block_width * block_height) // 8
    elif bpp == 2:
        block_data_size = (block_width * block_height) // 4
    elif bpp == 4:
        block_data_size = (block_width * block_height) // 2
    else:
        block_data_size = (bpp // 8) * block_width * block_height

    tile_w = img_width  // block_width
    tile_h = img_height // block_height
    n = tile_w * tile_h

    # View pixel_data as a 2-D array of blocks, then scatter via Morton LUT
    src = np.frombuffer(pixel_data, dtype=np.uint8).reshape(n, block_data_size)
    morton = _build_morton_lut(tile_w, tile_h)          # src[t] -> dst[morton[t]]
    dst = np.empty_like(src)
    dst[morton] = src
    return dst.tobytes()


class GxtTexture(BrStruct):
    def __br_read__(self, br: 'BinaryReader') -> None:
        self.textureOffset  = br.read_uint32()
        self.textureSize    = br.read_uint32()
        self.paletteIndex   = br.read_int32()
        self.unused         = br.read_uint32()
        self.textureType    = GxtTextureType(br.read_uint32())
        self.pixelFormat    = GxtPixelFormat(br.read_uint32())
        self.width          = br.read_uint16()
        self.height         = br.read_uint16()
        self.mipMaps        = br.read_uint16()
        self.padding        = br.read_uint16()

        # Seek to the absolute texture data offset and read, then restore position
        saved_pos = br.pos()
        br.seek(self.textureOffset, Whence.BEGIN)
        self.textureData = br.read_bytes(self.textureSize)
        br.seek(saved_pos, Whence.BEGIN)


    def get_unswizzled_data(self) -> bytes:
        """Return pixel data with Morton-order swizzling removed (Swizzled type only)."""
        if self.textureType != GxtTextureType.Swizzled:
            return self.textureData

        bpp, bw, bh = _FORMAT_INFO.get(self.pixelFormat, (32, 1, 1))
        return unswizzle_psvita(self.textureData, self.width, self.height, bpp, bw, bh)
    
    def to_dds(self) -> bytes:
        if self.pixelFormat == GxtPixelFormat.UBC1_DXT1:
            dds_fourcc  = b'DXT1'
            block_bytes = 8
        elif self.pixelFormat == GxtPixelFormat.UBC2_DXT3:
            dds_fourcc  = b'DXT3'
            block_bytes = 16
        elif self.pixelFormat == GxtPixelFormat.UBC3_DXT5:
            dds_fourcc  = b'DXT5'
            block_bytes = 16
        elif self.pixelFormat == GxtPixelFormat.ARGB8888:
            # Uncompressed RGBA — DDS_PIXELFORMAT with explicit channel masks
            pitch = self.width * 4  # bytes per row

            # DDS_PIXELFORMAT: DDPF_ALPHAPIXELS | DDPF_RGB, 32bpp, ARGB masks
            ddspf = struct.pack('<2I4s5I',
                32,          # dwSize
                0x41,        # dwFlags: DDPF_ALPHAPIXELS | DDPF_RGB
                b'\x00\x00\x00\x00',  # dwFourCC (unused)
                32,          # dwRGBBitCount
                0x00FF0000,  # dwRBitMask
                0x0000FF00,  # dwGBitMask
                0x000000FF,  # dwBBitMask
                0xFF000000,  # dwABitMask
            )

            dds_header = struct.pack('<7I44s',
                124,
                0x0002100F,   # dwFlags: CAPS | HEIGHT | WIDTH | PIXELFORMAT | PITCH
                self.height,
                self.width,
                pitch,
                0,
                self.mipMaps,
                bytes(44),
            ) + ddspf + struct.pack('<5I',
                0x1000, 0, 0, 0, 0,
            )

            return b'DDS ' + dds_header + self.get_unswizzled_data()
        else:
            raise NotImplementedError(f"DDS export not implemented for pixel format {self.pixelFormat}")

        # Compressed formats
        pitch = max(1, (self.width + 3) // 4) * block_bytes

        # DDS_PIXELFORMAT (32 bytes)
        ddspf = struct.pack('<2I4s5I',
            32,         # dwSize
            0x4,        # dwFlags: DDPF_FOURCC
            dds_fourcc, # dwFourCC
            0, 0, 0, 0, 0,
        )

        # DDS_HEADER (124 bytes)
        dds_header = struct.pack('<7I44s',
            124,          # dwSize
            0x81007,      # dwFlags: CAPS | HEIGHT | WIDTH | PIXELFORMAT | LINEARSIZE
            self.height,
            self.width,
            pitch,        # dwPitchOrLinearSize
            0,            # dwDepth
            self.mipMaps, # dwMipMapCount
            bytes(44),    # dwReserved1[11]
        ) + ddspf + struct.pack('<5I',
            0x1000,       # dwCaps: DDSCAPS_TEXTURE
            0, 0, 0, 0,   # dwCaps2/3/4, dwReserved2
        )

        return b'DDS ' + dds_header + self.get_unswizzled_data()
        


class GXT(BrStruct):
    def __br_read__(self, br: 'BinaryReader') -> None:
        self.magic         = br.read_str(4)
        self.version       = br.read_uint32()
        self.textureCount  = br.read_uint32()
        self.dataOffset    = br.read_uint32()
        self.dataSize      = br.read_uint32()
        self.palette4Count = br.read_uint32()
        self.palette8Count = br.read_uint32()
        self.padding       = br.read_uint32()

        self.textures = br.read_struct(GxtTexture, self.textureCount)