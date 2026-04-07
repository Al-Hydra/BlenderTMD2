
from .PyBinaryReader.binary_reader import *
from enum import IntEnum
import numpy as np
import struct


class GnfDataFormat(IntEnum):
    RGBA8888 = 0x0A   # 8:8:8:8 uncompressed
    # PS4/GNM BCn format values are confirmed empirically (not identical to desktop AMD):
    # 0x22 is unobserved in practice; values start at 0x23 for BC1.
    UNK_0x22 = 0x22   # unobserved — treat as BC1 if encountered
    BC1      = 0x23   # DXT1  /  4 bpp  /  8 B per 4×4 block  ← confirmed by data
    BC2      = 0x24   # DXT3  /  8 bpp  / 16 B per 4×4 block
    BC3      = 0x25   # DXT5  /  8 bpp  / 16 B per 4×4 block  ← confirmed by data (size)
    BC4      = 0x26   # ATI1  /  4 bpp  /  8 B per 4×4 block
    BC5      = 0x27   # ATI2  /  8 bpp  / 16 B per 4×4 block
    BC6H     = 0x28   # HDR   (requires DX10 header)
    BC7      = 0x29   # HQ    (requires DX10 header)


# (bpp, block_width, block_height)
_FORMAT_INFO = {
    GnfDataFormat.RGBA8888: (32, 1, 1),
    GnfDataFormat.UNK_0x22: (4,  4, 4),  # assume BC1-like
    GnfDataFormat.BC1:      (4,  4, 4),
    GnfDataFormat.BC2:      (8,  4, 4),
    GnfDataFormat.BC3:      (8,  4, 4),
    GnfDataFormat.BC4:      (4,  4, 4),
    GnfDataFormat.BC5:      (8,  4, 4),
    GnfDataFormat.BC6H:     (8,  4, 4),
    GnfDataFormat.BC7:      (8,  4, 4),
}

# DXGI format codes for DX10-header formats (BC4 and above need the DX10 extension header)
_DXGI_FORMAT = {
    GnfDataFormat.BC4:  80,   # DXGI_FORMAT_BC4_UNORM
    GnfDataFormat.BC5:  83,   # DXGI_FORMAT_BC5_UNORM
    GnfDataFormat.BC6H: 95,   # DXGI_FORMAT_BC6H_UF16
    GnfDataFormat.BC7:  98,   # DXGI_FORMAT_BC7_UNORM
}

def _build_ps4_morton_lut() -> tuple:
    # PS4 GCN uses X-first bit interleaving for 8×8 micro-tiles:
    #   even bits of t → x (0..7),  odd bits of t → y (0..7)
    t = np.arange(64, dtype=np.int32)
    x = np.zeros(64, dtype=np.int32)
    y = np.zeros(64, dtype=np.int32)
    for i in range(3):   # 3 bits per axis covers 0..7
        x |= ((t >> (2 * i))     & 1) << i
        y |= ((t >> (2 * i + 1)) & 1) << i
    return x, y


_PS4_MORTON_DX, _PS4_MORTON_DY = _build_ps4_morton_lut()


def _detile_ps4(data: bytes, width: int, height: int, bpp: int,
                block_w: int, block_h: int, tiling_index: int) -> bytes:

    if tiling_index in (0, 8):
        return data

    blocks_w = max(1, width  // block_w)
    blocks_h = max(1, height // block_h)
    block_size = max(1, bpp * block_w * block_h // 8)

    tiles_w = (blocks_w + 7) >> 3
    tiles_h = (blocks_h + 7) >> 3

    ty = np.repeat(np.arange(tiles_h, dtype=np.int32), tiles_w)
    tx = np.tile(  np.arange(tiles_w, dtype=np.int32), tiles_h)
    dest_x = tx[:, None] * 8 + _PS4_MORTON_DX  # (num_tiles, 64)
    dest_y = ty[:, None] * 8 + _PS4_MORTON_DY  # (num_tiles, 64)

    mask    = (dest_x < blocks_w) & (dest_y < blocks_h)
    dst_idx = (dest_y * blocks_w + dest_x)[mask]

    src = np.frombuffer(data, dtype=np.uint8).reshape(-1, block_size)
    dst = np.empty((blocks_w * blocks_h, block_size), dtype=np.uint8)
    dst[dst_idx] = src[:dst_idx.size]
    return dst.tobytes()


class GnmTexture:
    """Parses a 32-byte PS4 GCN T# hardware texture descriptor."""

    def __init__(self, dwords: list):
        assert len(dwords) == 8
        self._dwords = dwords

        # dword[1]: data_format at bits 25:20, num_format at bits 29:26
        self.data_format_raw = (dwords[1] >> 20) & 0x3F
        self.num_format      = (dwords[1] >> 26) & 0xF

        # dword[2]: width_m1 at bits 13:0, height_m1 at bits 27:14
        self.width  = ((dwords[2] >>  0) & 0x3FFF) + 1
        self.height = ((dwords[2] >> 14) & 0x3FFF) + 1

        # dword[3]: base_level at bits 15:12, last_level at bits 19:16, tiling_index at bits 24:20
        self.base_level   = (dwords[3] >> 12) & 0xF
        self.last_level   = (dwords[3] >> 16) & 0xF
        self.tiling_index = (dwords[3] >> 20) & 0x1F
        self.mip_count    = self.last_level - self.base_level + 1

        try:
            self.data_format = GnfDataFormat(self.data_format_raw)
        except ValueError:
            self.data_format = None


class GNFTexture:
    """One texture entry from a GNF container: descriptor + raw pixel bytes."""

    def __init__(self, gnm: GnmTexture, data: bytes):
        self.gnm  = gnm
        self.data = data

    def get_linear_data(self) -> bytes:
        fmt = self.gnm.data_format
        if fmt is None:
            return self.data  # unknown format, return raw
        bpp, bw, bh = _FORMAT_INFO.get(fmt, (32, 1, 1))
        return _detile_ps4(self.data, self.gnm.width, self.gnm.height,
                           bpp, bw, bh, self.gnm.tiling_index)

    def to_dds(self) -> bytes:
        fmt = self.gnm.data_format
        if fmt is None:
            raise NotImplementedError(
                f"GNF data_format 0x{self.gnm.data_format_raw:02X} is not supported"
            )

        pixel_data = self.get_linear_data()
        w, h = self.gnm.width, self.gnm.height
        mips = self.gnm.mip_count

        # ---- DX10 extension formats (BC4, BC5, BC6H, BC7) ----
        if fmt in _DXGI_FORMAT:
            dxgi = _DXGI_FORMAT[fmt]
            bpp, bw, bh = _FORMAT_INFO[fmt]
            pitch = max(1, (w + bw - 1) // bw) * (bpp * bw * bh // 8)

            # DDS_PIXELFORMAT with DDPF_FOURCC and FourCC="DX10"
            ddspf = struct.pack('<2I4s5I',
                32, 0x4, b'DX10', 0, 0, 0, 0, 0,
            )
            dds_header = struct.pack('<7I44s',
                124, 0x81007, h, w, pitch, 0, mips, bytes(44),
            ) + ddspf + struct.pack('<5I', 0x1000, 0, 0, 0, 0)

            # DDS_HEADER_DXT10
            dx10 = struct.pack('<5I',
                dxgi,   # dxgiFormat
                3,      # resourceDimension: D3D10_RESOURCE_DIMENSION_TEXTURE2D
                0,      # miscFlag
                1,      # arraySize
                0,      # miscFlags2
            )
            return b'DDS ' + dds_header + dx10 + pixel_data

        # ---- Standard compressed formats (BC1-BC3) ----
        _FOURCC = {
            GnfDataFormat.UNK_0x22: b'DXT1',  # treat unknown as BC1
            GnfDataFormat.BC1:      b'DXT1',
            GnfDataFormat.BC2:      b'DXT3',
            GnfDataFormat.BC3:      b'DXT5',
        }
        if fmt in _FOURCC:
            fourcc = _FOURCC[fmt]
            bpp, bw, bh = _FORMAT_INFO[fmt]
            block_bytes = bpp * bw * bh // 8
            pitch = max(1, (w + bw - 1) // bw) * block_bytes

            ddspf = struct.pack('<2I4s5I',
                32, 0x4, fourcc, 0, 0, 0, 0, 0,
            )
            dds_header = struct.pack('<7I44s',
                124, 0x81007, h, w, pitch, 0, mips, bytes(44),
            ) + ddspf + struct.pack('<5I', 0x1000, 0, 0, 0, 0)
            return b'DDS ' + dds_header + pixel_data

        # ---- Uncompressed RGBA8888 ----
        if fmt == GnfDataFormat.RGBA8888:
            pitch = w * 4
            ddspf = struct.pack('<2I4s5I',
                32, 0x41, b'\x00\x00\x00\x00', 32,
                0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000,
            )
            dds_header = struct.pack('<7I44s',
                124, 0x0002100F, h, w, pitch, 0, mips, bytes(44),
            ) + ddspf + struct.pack('<5I', 0x1000, 0, 0, 0, 0)
            return b'DDS ' + dds_header + pixel_data

        raise NotImplementedError(f"DDS export not implemented for GNF format {fmt!r}")


class GNF(BrStruct):

    def __br_read__(self, br: 'BinaryReader') -> None:
        self.magic = br.read_str(4)
        if self.magic != "GNF ":
            raise ValueError(f"Not a GNF file (magic={self.magic!r})")

        self.content_size = br.read_uint32()
        data_start        = br.pos() + self.content_size  # 0x08 + 0xF8 = 0x100

        self.version     = br.read_uint8()   # 0x08
        self.num_streams = br.read_uint8()   # 0x09
        self.alignment   = br.read_uint8()   # 0x0A
        br.read_uint8()                      # 0x0B  reserved
        br.read_uint32()                     # 0x0C  total file size (unused)

        # 0x10: num_streams × 32-byte GnmTexture descriptors.
        # dword[7] is repurposed to store the individual pixel data byte count.
        descriptors, data_sizes = [], []
        for _ in range(self.num_streams):
            dwords = [br.read_uint32() for _ in range(8)]
            descriptors.append(GnmTexture(dwords))
            data_sizes.append(dwords[7])

        br.seek(data_start, Whence.BEGIN)
        self.textures = [
            GNFTexture(gnm, br.read_bytes(sz))
            for gnm, sz in zip(descriptors, data_sizes)
        ]
