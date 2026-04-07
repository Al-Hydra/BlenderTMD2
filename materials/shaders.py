from ..tamLib.tmd2 import TMD2Material, TMD2MatTexture
from typing import NamedTuple
import os, bpy


class TextureSlot(NamedTuple):
    node: str
    tex_index: int
    min_textures: int
    non_color: bool = False


class ShaderParam(NamedTuple):
    input_name: str
    kind: str        # 'scalar' or 'color'
    indices: list


def _load_material(shader_name: str):
    path = os.path.dirname(os.path.realpath(__file__))
    material = bpy.data.materials.get(shader_name)
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link=False) as (data_from, data_to):
            data_to.materials = [shader_name]
        material = data_to.materials[0]
    return material


def _assign_texture(material, slot: TextureSlot, tm_material, textures):
    if len(textures) < slot.min_textures or len(tm_material.textures) <= slot.tex_index:
        return
    node = material.node_tree.nodes.get(slot.node)
    if node and tm_material.textures[slot.tex_index].texture.index < len(textures):
        node.image = textures[tm_material.textures[slot.tex_index].texture.index]
        if slot.non_color:
            node.image.colorspace_settings.name = 'Non-Color'


_TEXTURE_SLOTS = {
    "BSS1": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
        TextureSlot(node='Texture 3', tex_index=2, min_textures=3, non_color=True),
        TextureSlot(node='Texture 4', tex_index=3, min_textures=4),
        TextureSlot(node='Texture 5', tex_index=4, min_textures=5, non_color=True),
        TextureSlot(node='Texture 6', tex_index=5, min_textures=6, non_color=True),
        TextureSlot(node='Texture 7', tex_index=6, min_textures=7, non_color=True),
    ],
    "BHG1": [
        TextureSlot(node='Texture 3',     tex_index=2, min_textures=3, non_color=True),
        TextureSlot(node='Texture 3_UV1', tex_index=2, min_textures=3, non_color=True),
    ],
    "BHA1": [
        TextureSlot(node='Texture 2', tex_index=1, min_textures=2, non_color=True),
        TextureSlot(node='Texture 3', tex_index=2, min_textures=3, non_color=True),
    ],
    "BEI0": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
        TextureSlot(node='Texture 3', tex_index=2, min_textures=3, non_color=True),
        TextureSlot(node='Texture 4', tex_index=3, min_textures=4),
        TextureSlot(node='Texture 5', tex_index=4, min_textures=5, non_color=True),
        TextureSlot(node='Texture 7', tex_index=6, min_textures=7, non_color=True),
    ],
    "BED0": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
        TextureSlot(node='Texture 3', tex_index=2, min_textures=3, non_color=True),
        TextureSlot(node='Texture 4', tex_index=3, min_textures=4),
        TextureSlot(node='Texture 5', tex_index=4, min_textures=5, non_color=True),
        TextureSlot(node='Texture 7', tex_index=6, min_textures=7, non_color=True),
    ],
    "BES0": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
    ],
    "BEH0": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
        TextureSlot(node='Texture 3', tex_index=2, min_textures=3, non_color=True),
    ],
    "BGH0": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
        TextureSlot(node='Texture 3', tex_index=2, min_textures=3, non_color=True),
        TextureSlot(node='Texture 4', tex_index=3, min_textures=4),
        TextureSlot(node='Texture 5', tex_index=4, min_textures=5, non_color=True),
        TextureSlot(node='Texture 7', tex_index=6, min_textures=7, non_color=True),
    ],
    "BGH1": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
        TextureSlot(node='Texture 3', tex_index=2, min_textures=3, non_color=True),
        TextureSlot(node='Texture 4', tex_index=3, min_textures=4),
        TextureSlot(node='Texture 5', tex_index=4, min_textures=5, non_color=True),
        TextureSlot(node='Texture 7', tex_index=6, min_textures=7, non_color=True),
    ],
    "HSK1": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
        TextureSlot(node='Texture 2', tex_index=1, min_textures=2),
        TextureSlot(node='Texture 3', tex_index=2, min_textures=3, non_color=True),
        TextureSlot(node='Texture 4', tex_index=3, min_textures=4),
        TextureSlot(node='Texture 5', tex_index=4, min_textures=5, non_color=True),
    ],
    "Default": [
        TextureSlot(node='Texture 1', tex_index=0, min_textures=1),
    ],
}

_SHADER_PARAMS = {
    "BSS1": [
        ShaderParam("Shadow Intensity",     'scalar', [0]),
        ShaderParam("Shadow Color",         'color',  [1, 2, 3]),
        ShaderParam("Specular Size",        'scalar', [28]),
        ShaderParam("Specular Color",       'color',  [29, 30, 31]),
        ShaderParam("Color Burn Opacity",   'scalar', [10]),
        ShaderParam("Color Burn Intensity", 'scalar', [11]),
        ShaderParam("Alpha Clip Threshold", 'scalar', [24]),
    ],
    "BHG1": [
        ShaderParam("Hair Color 1", 'color', [12, 13, 14]),
        ShaderParam("Hair Color 2", 'color', [9, 10, 11]),
    ],
    "BHA1": [
        ShaderParam("Hair Base Color",  'color', [12, 13, 14]),
        ShaderParam("Hair Shine Color", 'color', [9, 10, 11]),
    ],
}


def _apply_shader_params(material, shader_name, tm_material):
    params = _SHADER_PARAMS.get(shader_name)
    if not params:
        return
    node_group = material.node_tree.nodes.get(shader_name)
    if not node_group:
        return
    try:
        for param in params:
            if param.kind == 'scalar':
                node_group.inputs[param.input_name].default_value = tm_material.shaderParams[param.indices[0]]
            else:
                node_group.inputs[param.input_name].default_value = (*[tm_material.shaderParams[i] for i in param.indices], 1)
    except Exception:
        pass


def _create_material(shader_name, mat_name, tm_material, textures):
    material = _load_material(shader_name)
    material = material.copy()
    material.name = mat_name
    for slot in _TEXTURE_SLOTS.get(shader_name, []):
        _assign_texture(material, slot, tm_material, textures)
    _apply_shader_params(material, shader_name, tm_material)
    return material


def _make_creator(shader_name):
    def create(mat_name=f"{shader_name}_Material", tm_material=TMD2Material, textures=[]):
        return _create_material(shader_name, mat_name, tm_material, textures)
    return create


shaders_dict = {name: _make_creator(name) for name in _TEXTURE_SLOTS}