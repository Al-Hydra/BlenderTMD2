if __name__ == "__main__" or __package__ is None:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "tamLib"

from .tmdv import TMDV
from .tmd0 import TMD0
from .tmo import TMO
from .utils.GNF import GNF
from .utils.GXT import GXT
from .lds import LDS
from .utils.PyBinaryReader.binary_reader import *
from collections import namedtuple
import os

# WIP implementation of cat files found in the following games:
# - Senran Kagura: Shinovi Versus

_METADATA_PREFIXES = ("GXT", "TMD", "TMD_Toon")
_METADATA_FILENAMES = ("_tex", "_mdl", "_mdl_hi", "_mdl_lo", "_m3r")

# Section types
SECTION_METADATA = "metadata"
SECTION_TMD0     = "tmd0"
SECTION_TMO      = "tmo"
SECTION_CAT      = "cat"
SECTION_TMDV     = "tmdv"
SECTION_GXT      = "gxt"
SECTION_GNF      = "gnf"
SECTION_LDS      = "lds"
SECTION_UNKNOWN  = "unknown"

_MAGIC_GXT = b'GXT\x00'
_MAGIC_GNF = b'GNF '

# type  : one of the SECTION_* constants
# name  : filename/path hint (from parent file_name; metadata tree mapping comes later)
# obj   : parsed object (Node, TMD0, TMO, cat1) or raw bytes for unknowns
# data  : raw bytes of the section as it appeared in the file
Section = namedtuple("Section", ["type", "name", "obj", "data"])

# name     : the entry name (texture/model filename hint)
# children : sub-entries that were introduced by a ',' (child) separator
MetaNode = namedtuple("MetaNode", ["name", "children"])


class cat1(BrStruct):
    def __init__(self):
        self.name = ""
        self.has_metadata = False
        self.content = []   # list of Section namedtuples

    def __br_read__(self, br: BinaryReader, file_name="", _depth=0) -> None:
        first_value = br.read_uint32()
        if first_value == 0:
            return  # empty/invalid file

        # Phase 1: collect all offsets
        all_offsets = [first_value]
        while br.pos() + 4 <= first_value and br.pos() + 4 <= br.size():
            val = br.read_uint32()
            if val == 0xFFFFFFFF:
                break
            if val == 0:
                continue
            all_offsets.append(val)

        self.has_metadata = any(s in file_name for s in _METADATA_FILENAMES)
        buf_size = br.size()

        # Phase 2: slice each section into raw bytes
        sections_raw = []
        for i, offset in enumerate(all_offsets):
            next_offset = all_offsets[i + 1] if i + 1 < len(all_offsets) else buf_size
            size = next_offset - offset
            if size <= 0:
                continue
            br.seek(offset, Whence.BEGIN)
            sections_raw.append(br.read_bytes(size))

        # Phase 3: identify and parse each section
        # Pre-parse metadata (always the first text block) so _identify can use it.
        metadata = None
        for data in sections_raw:
            if self._is_metadata(data):
                metadata = self._parse_metadata(data)
                break

        for i, data in enumerate(sections_raw):
            sec_type = self._identify(data, metadata)
            first_bytes = data[:4].hex()
            try:
                if sec_type == SECTION_METADATA:
                    obj = self._parse_metadata(data)
                elif sec_type == SECTION_TMD0:
                    obj = TMD0()
                    obj.__br_read__(BinaryReader(data), file_name)
                elif sec_type == SECTION_TMO:
                    obj = TMO()
                    obj.__br_read__(BinaryReader(data))
                    obj.name = file_name
                elif sec_type == SECTION_CAT:
                    obj = cat1()
                    obj.__br_read__(BinaryReader(data), file_name, _depth + 1)
                elif sec_type == SECTION_TMDV:
                    obj = TMDV()
                    obj.__br_read__(BinaryReader(data), file_name)
                elif sec_type == SECTION_GXT:
                    obj = GXT()
                    obj.__br_read__(BinaryReader(data))
                elif sec_type == SECTION_LDS:
                    obj = LDS()
                    obj.__br_read__(BinaryReader(data), file_name)
                elif sec_type == SECTION_GNF:
                    obj = GNF()
                    obj.__br_read__(BinaryReader(data))
                else:
                    obj = data
            except Exception as e:
                raise RuntimeError(
                    f"depth={_depth} section={i} type={sec_type} "
                    f"first_bytes=0x{first_bytes} -> {type(e).__name__}: {e}"
                ) from e
            self.content.append(Section(sec_type, file_name, obj, data))

    @staticmethod
    def _is_metadata(data: bytes) -> bool:
        """True only for the CSV metadata text block (GXT,/TMD,/TMD_Toon, prefix)."""
        if len(data) < 4:
            return False
        peek = data[:8].decode("ascii", errors="ignore")
        # A metadata block has a printable comma after the prefix, not a null byte.
        return any(peek.startswith(p) for p in _METADATA_PREFIXES) and data[3] == ord(",")

    @staticmethod
    def _identify_texture(data: bytes) -> str:
        """Given a blob known to be a texture container, pick GXT / GNF / LDS by magic."""
        if data[:4] == _MAGIC_GXT:
            return SECTION_GXT
        if data[:4] == _MAGIC_GNF:
            return SECTION_GNF
        return SECTION_LDS   # LDS has no magic — assume if neither of the above

    @staticmethod
    def _identify(data: bytes, metadata: dict = None) -> str:
        if cat1._is_metadata(data):
            return SECTION_METADATA

        peek = data[:8].decode("ascii", errors="ignore")
        if peek[:4] in ("tmd0", "0dmt"):
            return SECTION_TMD0
        if peek[:4] in ("tmdv", "vdmt"):
            return SECTION_TMDV
        if peek[:4] in ("tmo0", "tmo1"):
            return SECTION_TMO

        # If metadata lists a GXT category, the section is a texture container;
        # pick the exact type from its magic bytes.
        if metadata is not None and any(k.startswith("GXT") for k in metadata):
            return cat1._identify_texture(data)

        if data[:4] == _MAGIC_GXT:
            return SECTION_GXT
        if data[:4] == _MAGIC_GNF:
            return SECTION_GNF
        if cat1._is_cat(data):
            return SECTION_CAT
        return SECTION_UNKNOWN

    @staticmethod
    def _is_cat(data: bytes) -> bool:
        size = len(data)
        if size < 8:
            return False
        try:
            sub_br = BinaryReader(data)
            first = sub_br.read_uint32()
            if first < 8 or first >= size:
                return False
            prev = first
            while True:
                val = sub_br.read_uint32()
                if val == 0xFFFFFFFF:
                    return True
                if val >= size or val <= prev:
                    return False
                prev = val
        except Exception:
            return False

    def unpack(self, output_dir: str) -> None:
        """Extract all sections as individual files under output_dir."""
        os.makedirs(output_dir, exist_ok=True)

        # Collect named queues from the metadata section (same logic as print_tree)
        tex_names, model_names = [], []
        metadata_sec = next((s for s in self.content if s.type == SECTION_METADATA), None)
        if metadata_sec is not None:
            for key, nodes in metadata_sec.obj.items():
                if key.startswith("GXT"):
                    tex_names.extend(cat1._flatten_meta(nodes))
                elif key.startswith("TMD"):
                    model_names.extend(cat1._flatten_meta(nodes))

        _EXT = {
            SECTION_GXT:  ".gxt",
            SECTION_GNF:  ".gnf",
            SECTION_LDS:  ".lds",
            SECTION_TMD0: ".tmd",
            SECTION_TMDV: ".tmdv",
            SECTION_TMO:  ".tmo",
        }

        tex_idx = model_idx = anim_idx = 0
        for i, sec in enumerate(self.content):
            if sec.type == SECTION_METADATA:
                path = os.path.join(output_dir, f"{i:02d}_metadata.txt")
                with open(path, "wb") as f:
                    f.write(sec.data)
            elif sec.type in (SECTION_GXT, SECTION_GNF, SECTION_LDS):
                name = tex_names[tex_idx] if tex_idx < len(tex_names) else f"texture_{tex_idx}"
                tex_idx += 1
                path = os.path.join(output_dir, f"{name}{_EXT[sec.type]}")
                with open(path, "wb") as f:
                    f.write(sec.data)
            elif sec.type in (SECTION_TMD0, SECTION_TMDV):
                name = model_names[model_idx] if model_idx < len(model_names) else f"model_{model_idx}"
                model_idx += 1
                path = os.path.join(output_dir, f"{name}{_EXT[sec.type]}")
                with open(path, "wb") as f:
                    f.write(sec.data)
            elif sec.type == SECTION_TMO:
                path = os.path.join(output_dir, f"anim_{anim_idx}.tmo")
                anim_idx += 1
                with open(path, "wb") as f:
                    f.write(sec.data)
            elif sec.type == SECTION_CAT:
                sub_dir = os.path.join(output_dir, f"cat_{i:02d}")
                sec.obj.unpack(sub_dir)
            else:
                path = os.path.join(output_dir, f"{i:02d}_unknown.bin")
                with open(path, "wb") as f:
                    f.write(sec.data)

    def print_tree(self) -> None:
        """Print the content tree with box-drawing characters."""
        self._print_subtree("", True, is_root=True)

    def _print_subtree(self, prefix: str, is_last: bool, is_root: bool = False) -> None:
        label = f'cat1 "{self.name}"' if self.name else "cat1"
        if is_root:
            print(label)
            child_prefix = ""
        else:
            branch = "└── " if is_last else "├── "
            print(f"{prefix}{branch}{label}")
            child_prefix = prefix + ("    " if is_last else "│   ")

        # Collect named queues from the metadata section (if any)
        tex_names, model_names = [], []
        metadata_sec = next((s for s in self.content if s.type == SECTION_METADATA), None)
        if metadata_sec is not None:
            for key, nodes in metadata_sec.obj.items():
                if key.startswith("GXT"):
                    tex_names.extend(cat1._flatten_meta(nodes))
                elif key.startswith("TMD"):
                    model_names.extend(cat1._flatten_meta(nodes))

        tex_idx = model_idx = anim_idx = 0
        for i, sec in enumerate(self.content):
            last = (i == len(self.content) - 1)
            br   = "└── " if last else "├── "
            if sec.type == SECTION_METADATA:
                print(f"{child_prefix}{br}[{i}] metadata")
            elif sec.type in (SECTION_GXT, SECTION_GNF, SECTION_LDS):
                name = tex_names[tex_idx] if tex_idx < len(tex_names) else f"texture_{tex_idx}"
                tex_idx += 1
                print(f"{child_prefix}{br}[{i}] {sec.type}  {name!r}")
            elif sec.type in (SECTION_TMD0, SECTION_TMDV):
                name = model_names[model_idx] if model_idx < len(model_names) else f"model_{model_idx}"
                model_idx += 1
                print(f"{child_prefix}{br}[{i}] {sec.type}  {name!r}")
            elif sec.type == SECTION_TMO:
                print(f"{child_prefix}{br}[{i}] {sec.type}  anim_{anim_idx}")
                anim_idx += 1
            elif sec.type == SECTION_CAT:
                sec.obj._print_subtree(child_prefix, last)
            else:
                size = len(sec.obj) if isinstance(sec.obj, (bytes, bytearray)) else "?"
                print(f"{child_prefix}{br}[{i}] {sec.type}  ({size} bytes)")

    @staticmethod
    def _flatten_meta(nodes: list) -> list:
        """Depth-first flattening of a MetaNode list to a plain list of name strings."""
        out = []
        for node in nodes:
            out.append(node.name)
            out.extend(cat1._flatten_meta(node.children))
        return out

    @staticmethod
    def _parse_metadata(data: bytes) -> dict:
        """Parse the CSV metadata block into {category: [MetaNode, ...]} tree.

        Separator semantics (the bytes that follow each name token):
          ','    → next token is a child of this one
          '\\n,,' → next token is a sibling (same parent, same depth)
          '\\n'   → next token opens a new root-level category
        """
        text = data.rstrip(b"\x00").decode("utf-8")
        result = {}
        stack = []       # MetaNode ancestors; stack[-1] is the current parent
        current_cat = None
        is_first = True  # True when the next token should be a category name
        i = 0
        n = len(text)

        while i < n:
            # --- collect token ---
            j = i
            while j < n and text[j] not in (',', '\n'):
                j += 1
            name = text[i:j]
            i = j

            # --- classify separator ---
            if i >= n:
                sep = 'END'
            elif text[i] == ',':
                i += 1
                sep = 'CHILD'
            else:  # '\n'
                i += 1
                if i < n and text[i:i+2] == ',,':
                    i += 2
                    sep = 'SIBLING'
                else:
                    sep = 'ROOT'

            if not name:
                if sep in ('ROOT', 'END'):
                    is_first = True
                continue

            if is_first:
                current_cat = name
                result.setdefault(current_cat, [])
                stack = []
                is_first = False
            else:
                node = MetaNode(name, [])
                if stack:
                    stack[-1].children.append(node)
                else:
                    result[current_cat].append(node)

                if sep == 'CHILD':
                    stack.append(node)  # this node becomes parent for the next token
                # SIBLING: don't push — next token shares the same parent

            if sep in ('ROOT', 'END'):
                stack = []
                is_first = True

        return result


if __name__ == "__main__":
    import os
    from collections import Counter

    # test a whole game directory
    '''failed_files = {}
    type_counts = Counter()
    game_dir = r"G:\SteamLibrary\steamapps\common\Senran Kagura Shinovi Versus"
    for root, dirs, files in os.walk(game_dir):
        for file in files:
            if file.endswith(".cat"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "rb") as f:
                        cat = cat1()
                        br = BinaryReader(f.read())
                        cat.__br_read__(br, file_path)
                    for section in cat.content:
                        type_counts[section.type] += 1
                except Exception as e:
                    failed_files[file_path] = str(e)

    print("\nSection type counts:")
    for t, count in type_counts.most_common():
        print(f"  {t}: {count}")

    if failed_files:
        print(f"\nFailed files ({len(failed_files)}):")
        for file_path, error in failed_files.items():
            print(f"  {file_path}")
            print(f"    {error}")
    else:
        print("\nAll files processed successfully.")'''
        
    single_file = r"G:\SteamLibrary\steamapps\common\Senran Kagura Shinovi Versus\dlc00\nnj\nnj01_00_tex_hi.cat"
    with open(single_file, "rb") as f:
        cat = cat1()
        br = BinaryReader(f.read())
        cat.__br_read__(br, single_file)
        
        
        
        cat.unpack(r"G:\Dev\BlenderTMD2\output_cat")
