from ..tamLib.tmd2 import TMD2Material, TMD2MatTexture
import os, bpy

def create_BSS1(mat_name="BSS1_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BSS1')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BSS1']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex1_node = material.node_tree.nodes.get('Texture 1')
    if len(textures) >= 1:
        tmat_texture: TMD2MatTexture = tm_material.textures[0]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex1_node.image = image
    
    tex3_node = material.node_tree.nodes.get('Texture 3')
    if len(textures) >= 3:
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
    
    tex4_node = material.node_tree.nodes.get('Texture 4')
    if len(textures) >= 4:
        tmat_texture: TMD2MatTexture = tm_material.textures[3]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex4_node.image = image
    
    tex5_node = material.node_tree.nodes.get('Texture 5')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[4]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex5_node.image = image
        tex5_node.image.colorspace_settings.name = 'Non-Color'
    
    tex5_node = material.node_tree.nodes.get('Texture 6')
    if len(textures) >= 6:
        tmat_texture: TMD2MatTexture = tm_material.textures[5]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex5_node.image = image
        tex5_node.image.colorspace_settings.name = 'Non-Color'
    
    tex7_node = material.node_tree.nodes.get('Texture 7')
    if len(textures) >= 7:
        tmat_texture: TMD2MatTexture = tm_material.textures[6]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex7_node.image = image
        tex7_node.image.colorspace_settings.name = 'Non-Color'
    
    try:
    
        node_group = material.node_tree.nodes.get('BSS1')
        if node_group:
            node_group.inputs["Shadow Intensity"].default_value = tm_material.shaderParams[0]
            node_group.inputs["Shadow Color"].default_value = (tm_material.shaderParams[1],tm_material.shaderParams[2],tm_material.shaderParams[3],1)
            
            node_group.inputs["Specular Size"].default_value = tm_material.shaderParams[28]
            node_group.inputs["Specular Color"].default_value = (tm_material.shaderParams[29],tm_material.shaderParams[30],tm_material.shaderParams[31],1)
            
            node_group.inputs["Color Burn Opacity"].default_value = tm_material.shaderParams[10]
            node_group.inputs["Color Burn Intensity"].default_value = tm_material.shaderParams[11]
            
            node_group.inputs["Alpha Clip Threshold"].default_value = tm_material.shaderParams[24]
            
    except:
        pass
    

    return material


def create_BHG1(mat_name="BHG1_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BHG1')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BHG1']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex3_node = material.node_tree.nodes.get('Texture 3')
    if len(textures) >= 3:
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
        
        tex3_node = material.node_tree.nodes.get('Texture 3_UV1')
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
    
    
    node_group = material.node_tree.nodes.get('BHG1')
    if node_group:
        node_group.inputs["Hair Color 1"].default_value = (tm_material.shaderParams[12],tm_material.shaderParams[13],tm_material.shaderParams[14],1)
        node_group.inputs["Hair Color 2"].default_value = (tm_material.shaderParams[9],tm_material.shaderParams[10],tm_material.shaderParams[11],1)
    

    return material


def create_BHA1(mat_name="BHA1_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BHA1')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BHA1']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex3_node = material.node_tree.nodes.get('Texture 2')
    if len(textures) >= 2:
        tmat_texture: TMD2MatTexture = tm_material.textures[1]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
    
    if len(textures) >= 3:
        tex3_node = material.node_tree.nodes.get('Texture 3')
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
    
    
    node_group = material.node_tree.nodes.get('BHA1')
    if node_group:
        node_group.inputs["Hair Base Color"].default_value = (tm_material.shaderParams[12],tm_material.shaderParams[13],tm_material.shaderParams[14],1)
        node_group.inputs["Hair Shine Color"].default_value = (tm_material.shaderParams[9],tm_material.shaderParams[10],tm_material.shaderParams[11],1)
    

    return material


def create_BEI0(mat_name="BEI0_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BEI0')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BEI0']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex1_node = material.node_tree.nodes.get('Texture 1')
    if len(textures) >= 1:
        tmat_texture: TMD2MatTexture = tm_material.textures[0]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex1_node.image = image
    
    tex3_node = material.node_tree.nodes.get('Texture 3')
    if len(textures) >= 3:
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
    
    tex4_node = material.node_tree.nodes.get('Texture 4')
    if len(textures) >= 4:
        tmat_texture: TMD2MatTexture = tm_material.textures[3]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex4_node.image = image
    
    tex5_node = material.node_tree.nodes.get('Texture 5')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[4]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex5_node.image = image
        tex5_node.image.colorspace_settings.name = 'Non-Color'
    
    tex7_node = material.node_tree.nodes.get('Texture 7')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[6]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex7_node.image = image
        tex7_node.image.colorspace_settings.name = 'Non-Color'
    

    return material


def create_BED0(mat_name="BED0_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BED0')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BED0']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex1_node = material.node_tree.nodes.get('Texture 1')
    if len(textures) >= 1:
        tmat_texture: TMD2MatTexture = tm_material.textures[0]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex1_node.image = image
    
    tex3_node = material.node_tree.nodes.get('Texture 3')
    if len(textures) >= 3:
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
    
    tex4_node = material.node_tree.nodes.get('Texture 4')
    if len(textures) >= 4:
        tmat_texture: TMD2MatTexture = tm_material.textures[3]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex4_node.image = image
    
    tex5_node = material.node_tree.nodes.get('Texture 5')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[4]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex5_node.image = image
        tex5_node.image.colorspace_settings.name = 'Non-Color'
    
    tex7_node = material.node_tree.nodes.get('Texture 7')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[6]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex7_node.image = image
        tex7_node.image.colorspace_settings.name = 'Non-Color'
    

    return material


def create_BES0(mat_name="BES0_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BES0')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BES0']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex1_node = material.node_tree.nodes.get('Texture 1')
    if len(textures) >= 1:
        tmat_texture: TMD2MatTexture = tm_material.textures[0]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex1_node.image = image
    
    
    return material

def create_BEH0(mat_name="BEH0_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BEH0')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BEH0']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex1_node = material.node_tree.nodes.get('Texture 1')
    if len(textures) >= 1:
        tmat_texture: TMD2MatTexture = tm_material.textures[0]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex1_node.image = image
    
    tex3_node = material.node_tree.nodes.get('Texture 3')
    if len(textures) >= 3:
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'

    return material


def create_BGH0(mat_name="BGH0_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BGH0')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BGH0']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex1_node = material.node_tree.nodes.get('Texture 1')
    if len(textures) >= 1:
        tmat_texture: TMD2MatTexture = tm_material.textures[0]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex1_node.image = image
    
    tex3_node = material.node_tree.nodes.get('Texture 3')
    if len(textures) >= 3:
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
    
    tex4_node = material.node_tree.nodes.get('Texture 4')
    if len(textures) >= 4:
        tmat_texture: TMD2MatTexture = tm_material.textures[3]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex4_node.image = image
    
    tex5_node = material.node_tree.nodes.get('Texture 5')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[4]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex5_node.image = image
        tex5_node.image.colorspace_settings.name = 'Non-Color'
    
    tex7_node = material.node_tree.nodes.get('Texture 7')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[6]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex7_node.image = image
        tex7_node.image.colorspace_settings.name = 'Non-Color'
    

    return material


def create_BGH1(mat_name="BGH1_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BGH1')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['BGH1']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex1_node = material.node_tree.nodes.get('Texture 1')
    if len(textures) >= 1:
        tmat_texture: TMD2MatTexture = tm_material.textures[0]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex1_node.image = image
    
    tex3_node = material.node_tree.nodes.get('Texture 3')
    if len(textures) >= 3:
        tmat_texture: TMD2MatTexture = tm_material.textures[2]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex3_node.image = image
        tex3_node.image.colorspace_settings.name = 'Non-Color'
    
    tex4_node = material.node_tree.nodes.get('Texture 4')
    if len(textures) >= 4:
        tmat_texture: TMD2MatTexture = tm_material.textures[3]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex4_node.image = image
    
    tex5_node = material.node_tree.nodes.get('Texture 5')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[4]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex5_node.image = image
        tex5_node.image.colorspace_settings.name = 'Non-Color'
    
    tex7_node = material.node_tree.nodes.get('Texture 7')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[6]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex7_node.image = image
        tex7_node.image.colorspace_settings.name = 'Non-Color'
    

    return material


def create_Default(mat_name="Default_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('Default')
    if not material:
        material_path = f'{path}/materials.blend'
        with bpy.data.libraries.load(material_path, link = False) as (data_from, data_to):
            data_to.materials = ['Default']
        material = data_to.materials[0]
    
    material = material.copy()
    material.name = mat_name
    
    tex1_node = material.node_tree.nodes.get('Texture 1')
    if len(textures) >= 1:
        tmat_texture: TMD2MatTexture = tm_material.textures[0]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex1_node.image = image

    return material


shaders_dict = {
    "Default" : create_Default,
    "BSS1" : create_BSS1,
    "BHG1" : create_BHG1,
    "BHA1" : create_BHA1,
    "BEI0" : create_BEI0,
    "BED0" : create_BED0,
    "BES0" : create_BES0,
    "BEH0" : create_BEH0,
    "BGH0" : create_BGH0,
    "BGH1" : create_BGH1
}