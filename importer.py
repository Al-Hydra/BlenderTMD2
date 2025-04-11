import bpy, bmesh, math, mathutils
from mathutils import Vector, Quaternion, Matrix
from math import radians
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, CollectionProperty
from bpy.types import Operator
from .reader import readTMD2, readLDS
from .tamLib.tmd2 import *
import os, tempfile
import numpy as np


class TMD2_IMPORTER_OT_IMPORT(Operator, ImportHelper):
    bl_label = "Import TMD2"
    bl_idname = "import_scene.tmd2"


    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    filter_glob: StringProperty(default="*.tmd2;*.lds", options={"HIDDEN"}) # type: ignore
    filename_ext = ".tmd2"
    filepath: StringProperty(subtype='FILE_PATH') # type: ignore
    auto_find_textures: BoolProperty(default=True) # type: ignore
    texture_path: StringProperty(subtype='FILE_PATH') # type: ignore

    def execute(self, context):
        # Split files by type
        tmd2_files = {}
        lds_files = {}

        for file in self.files:
            full_path = os.path.join(self.directory, file.name)
            base_name, ext = os.path.splitext(file.name.lower())

            if ext == ".tmd2":
                tmd2_files[base_name] = full_path
            elif ext == ".lds":
                lds_files[base_name] = full_path

        print(f"🟦 TMD2 files: {list(tmd2_files.keys())}")
        print(f"🟨 LDS files: {list(lds_files.keys())}")

        for base_name, tmd2_path in tmd2_files.items():
            texture_path = ""

            # Step 1: Check LDS dict
            if base_name in lds_files:
                texture_path = lds_files[base_name]
                print(f"✅ Using matching LDS file for {base_name}: {texture_path}")

            else:
                # Step 2: Check filesystem in same directory
                fallback_path = os.path.join(self.directory, base_name + ".lds")
                if os.path.exists(fallback_path):
                    texture_path = fallback_path
                    print(f"📁 Found fallback LDS file for {base_name}: {texture_path}")
                else:
                    print(f"❌ No LDS found for {base_name}, importing TMD2 without texture.")

            # Read and import TMD2
            tmd2 = readTMD2(tmd2_path)
            importer = importTMD2(self, tmd2_path, self.as_keywords(ignore=("filter_glob",)), tmd2, context)

            # Store texture path for later use
            importer.texture_path = texture_path

            importer.read(context)

        return {'FINISHED'}

    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "auto_find_textures", text= "Auto Find Textures")
        #layout.prop(self, "texture_path", text= "Texture Path")


class DropTMD2(Operator):
    """Allows TMD2 files to be dropped into the viewport to import them"""
    bl_idname = "import_scene.drop_tmd2"
    bl_label = "Import TMD2"

    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    filter_glob: StringProperty(default="*.tmd2", options={"HIDDEN"}) # type: ignore
    filename_ext = ".tmd2"
    filepath: StringProperty(subtype='FILE_PATH') # type: ignore
    def execute(self, context):
        for file in self.files:
        
            self.filepath = os.path.join(self.directory, file.name)

            tmd2 = readTMD2(self.filepath)

            importer = importTMD2(self, self.filepath, self.as_keywords(ignore=("filter_glob",)), tmd2, context)
            importer.read(context)
        
        return {'FINISHED'}


class TMD2_FH_import(bpy.types.FileHandler):
    bl_idname = "TMD2_FH_import"
    bl_label = "File handler for TMD2 files"
    bl_import_operator = "import_scene.drop_tmd2"
    bl_file_extensions = ".tmd2"

    @classmethod
    def poll_drop(cls, context):
        return (context.area and context.area.type == 'VIEW_3D')
    
    def draw():
        pass

class DropLDS(Operator):
    """Allows LDS files to be dropped into the viewport to import them"""
    bl_idname = "import_scene.drop_lds"
    bl_label = "Import LDS"

    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    filter_glob: StringProperty(default="*.tmd2", options={"HIDDEN"}) # type: ignore
    filename_ext = ".lds"
    filepath: StringProperty(subtype='FILE_PATH') # type: ignore
    def execute(self, context):
        for file in self.files:
        
            self.filepath = os.path.join(self.directory, file.name)

            importLDS(self.filepath)
        
        return {'FINISHED'}

class LDS_FH_import(bpy.types.FileHandler):
    bl_idname = "LDS_FH_import"
    bl_label = "File handler for LDS files"
    bl_import_operator = "import_scene.drop_lds"
    bl_file_extensions = ".lds"

    @classmethod
    def poll_drop(cls, context):
        return (context.area and context.area.type == 'VIEW_3D')
    
    def draw():
        pass


class importTMD2:
    def __init__(self, operator: Operator, filepath, import_settings: dict, tmd2file, context):
        self.operator = operator
        self.filepath = filepath
        self.texture_path = ""
        for key, value in import_settings.items():
            setattr(self, key, value)
        
        self.tmd2: TMD2 = tmd2file
    
    
    def read(self, context):
        #import and process materials and textures
        images_list = importLDS(self.texture_path, True) if self.texture_path else []
        
        materials_dict = {}
        for i, tm_mat in enumerate(self.tmd2.materials):
            tm_mat: TMD2Material
            
            if tm_mat.shaderID == 'BSS1':
                blender_mat = create_BSS1(f"{self.tmd2.name}_{i}", tm_mat, images_list)
            else:
                blender_mat = bpy.data.materials.new(f"{self.tmd2.name}_{i}")
            bmat_props = blender_mat.tmd2_material
            
            bmat_props.material_hash = str(tm_mat.hash)
            bmat_props.shader_id = tm_mat.shaderID
            bmat_props.param_count = tm_mat.shaderParamsCount
            for i in range(tm_mat.shaderParamsCount):
                bmat_props.param_values[i].value = tm_mat.shaderParams[i]
            
            for tmat_texture in tm_mat.textures:
                tmat_texture: TMD2MatTexture
                tm_texture: TMD2Texture = tmat_texture.texture
                t = bmat_props.textures.add()
                t.texture_hash = str(tm_texture.hash)
                if images_list:
                    t.image = images_list[tm_texture.index]
            
            materials_dict[tm_mat] = blender_mat
        
        # Create a new mesh
        YUP_TO_ZUP = Matrix.Rotation(radians(90), 4, 'X')        
        
        if self.tmd2.modelFlags & 0x2000:
            #skeleton data
            armature = bpy.data.armatures.new(self.tmd2.name)
            armature_obj = bpy.data.objects.new(self.tmd2.name, armature)
            context.collection.objects.link(armature_obj)
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            armature_obj.data.display_type = 'STICK'
            
            for tmbone in self.tmd2.bones:
                bbone = armature_obj.data.edit_bones.new(tmbone.name)
                
                matrix = Matrix(tmbone.matrix).transposed().inverted()
                matrix = YUP_TO_ZUP @ matrix
                
                bbone.matrix = matrix
                bbone.tail += Vector((0, 0, 0.01)) # Set the tail position to be 1 unit along the Z axis

            for bone in self.tmd2.bones:
                if bone.parentIndex != -1:
                    blender_bone = armature_obj.data.edit_bones[bone.name]
                    parent_bone = armature_obj.data.edit_bones[self.tmd2.bones[bone.parentIndex].name]
                    blender_bone.parent = parent_bone
            
            bpy.ops.object.mode_set(mode='OBJECT')
        
        
        for tmd_model in self.tmd2.models:
            
        
            mesh = bpy.data.meshes.new(tmd_model.name)
            mesh_obj = bpy.data.objects.new(tmd_model.name, mesh)
            context.collection.objects.link(mesh_obj)
            
            #create materials
            for mesh_mat in tmd_model.materials:
                mesh.materials.append(materials_dict[mesh_mat])
            

            # Create a new bmesh object
            bm = bmesh.new()

            # Create vertices
            custom_normals = []
            vgroups_count = 0
            if self.tmd2.modelFlags & 0x400:
                vgroup_layer = bm.verts.layers.deform.new("Weights")
                vgroups_count = 4
                
                for bone in armature.bones:
                    mesh_obj.vertex_groups.new(name = bone.name)
                
                #add arnature modifier
                armature_modifier = mesh_obj.modifiers.new(name = armature.name, type = 'ARMATURE')
                armature_modifier.object = armature_obj
                
                mesh_obj.parent = armature_obj
                
                if self.tmd2.modelFlags & 0x8000:
                    vgroups_count += 4
            
            uv_layers = []
            if self.tmd2.modelFlags & 0x10:
                uv0_layer = bm.loops.layers.uv.new(f"UVMap")
                uv_layers.append(uv0_layer)
            
            if self.tmd2.modelFlags & 0x20:
                uv1_layer = bm.loops.layers.uv.new(f"UVMap1")
                uv_layers.append(uv1_layer)
            
            if self.tmd2.modelFlags & 0x40:
                uv2_layer = bm.loops.layers.uv.new(f"UVMap2")
                uv_layers.append(uv2_layer)
            
            color_layers = []
            if self.tmd2.modelFlags & 0x80:
                col1_layer = bm.loops.layers.color.new(f"Color")
                color_layers.append(col1_layer)
            
            if self.tmd2.modelFlags & 0x200:
                col2_layer = bm.loops.layers.color.new(f"Color2")
                color_layers.append(col2_layer)
            
            for tmd_mesh in tmd_model.meshes:
                
                #vertex data
                bm_verts = []
                for vertex in tmd_mesh.vertices:
                    v = bm.verts.new(vertex.position)
                    v.normal = vertex.normal
                    bm_verts.append(v)
                    custom_normals.append(vertex.normal)
                    
                    boneIDs = vertex.boneIDs + vertex.boneIDs2
                    boneWeights = vertex.boneWeights + vertex.boneWeights2
                    
                    v[vgroup_layer][tmd_mesh.indexTable[boneIDs[0]]] = 0
                    v[vgroup_layer][tmd_mesh.indexTable[boneIDs[1]]] = 0
                    v[vgroup_layer][tmd_mesh.indexTable[boneIDs[2]]] = 0
                    v[vgroup_layer][tmd_mesh.indexTable[boneIDs[3]]] = 0
                    v[vgroup_layer][tmd_mesh.indexTable[boneIDs[4]]] = 0
                    v[vgroup_layer][tmd_mesh.indexTable[boneIDs[5]]] = 0
                    v[vgroup_layer][tmd_mesh.indexTable[boneIDs[6]]] = 0
                    v[vgroup_layer][tmd_mesh.indexTable[boneIDs[7]]] = 0
                    
                    
                    for boneID, weight in zip(boneIDs, boneWeights):
                        v[vgroup_layer][tmd_mesh.indexTable[boneID]] += weight 

                bm.verts.ensure_lookup_table()
                
                #face data
                for tri in tmd_mesh.triangles:
                    face = bm.faces.new([bm_verts[i] for i in tri])
                    face.smooth = True
                    face.material_index = tmd_mesh.materialIndex
                    
                    for i, uv in enumerate(uv_layers):
                        if i == 0:
                            face.loops[0][uv].uv = (tmd_mesh.vertices[tri[0]].uv[0], 1 - tmd_mesh.vertices[tri[0]].uv[1])
                            face.loops[1][uv].uv = (tmd_mesh.vertices[tri[1]].uv[0], 1 - tmd_mesh.vertices[tri[1]].uv[1])
                            face.loops[2][uv].uv = (tmd_mesh.vertices[tri[2]].uv[0], 1 - tmd_mesh.vertices[tri[2]].uv[1])
                        elif i == 1:
                            face.loops[0][uv].uv = (tmd_mesh.vertices[tri[0]].uv2[0], 1 - tmd_mesh.vertices[tri[0]].uv2[1])
                            face.loops[1][uv].uv = (tmd_mesh.vertices[tri[1]].uv2[0], 1 - tmd_mesh.vertices[tri[1]].uv2[1])
                            face.loops[2][uv].uv = (tmd_mesh.vertices[tri[2]].uv2[0], 1 - tmd_mesh.vertices[tri[2]].uv2[1])
                        elif i == 2:
                            face.loops[0][uv].uv = (tmd_mesh.vertices[tri[0]].uv3[0], 1 - tmd_mesh.vertices[tri[0]].uv3[1])
                            face.loops[1][uv].uv = (tmd_mesh.vertices[tri[1]].uv3[0], 1 - tmd_mesh.vertices[tri[1]].uv3[1])
                            face.loops[2][uv].uv = (tmd_mesh.vertices[tri[2]].uv3[0], 1 - tmd_mesh.vertices[tri[2]].uv3[1])
                        
                    
                    for col_idx, col in enumerate(color_layers):
                        if col_idx == 0:
                            face.loops[0][col] = [x for x in tmd_mesh.vertices[tri[0]].color]
                            face.loops[1][col] = [x for x in tmd_mesh.vertices[tri[1]].color]
                            face.loops[2][col] = [x for x in tmd_mesh.vertices[tri[2]].color]
                        elif col_idx == 1:
                            face.loops[0][col] = [x for x in tmd_mesh.vertices[tri[0]].color2]
                            face.loops[1][col] = [x for x in tmd_mesh.vertices[tri[1]].color2]
                            face.loops[2][col] = [x for x in tmd_mesh.vertices[tri[2]].color2]

                bm.verts.ensure_lookup_table()
            
            bm.to_mesh(mesh)
            bm.free()
            if self.tmd2.modelFlags & 0x4:
                mesh.normals_split_custom_set_from_vertices(custom_normals)
            
            #set active color
            mesh.color_attributes.render_color_index = 0
            mesh.color_attributes.active_color_index = 0
            
                
            mesh.transform(YUP_TO_ZUP)


def create_BSS1(mat_name="BSS1_Material", tm_material: TMD2Material = TMD2Material, textures = []):
    path = os.path.dirname(os.path.realpath(__file__))
    
    material = bpy.data.materials.get('BSS1')
    if not material:
        material_path = f'{path}/materials/materials.blend'
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
    
    tex7_node = material.node_tree.nodes.get('Texture 7')
    if len(textures) >= 5:
        tmat_texture: TMD2MatTexture = tm_material.textures[6]
        texture = tmat_texture.texture
        image = textures[texture.index]
        tex7_node.image = image
        tex7_node.image.colorspace_settings.name = 'Non-Color'
    

    return material


def importLDS(file_path, return_tex = False):
    lds = readLDS(file_path)

    images_list = []
    
    for i, texture in enumerate(lds.textures):
        tex_name = f"{lds.name}_{i}"
        
        
        if bpy.data.images.get(tex_name):
            #update existing image
            image = bpy.data.images[tex_name]
            image.pack(data=texture, data_len=len(texture))
            image.source = 'FILE'
            image.use_fake_user = True

        else:
            #create new image
            dds_path = os.path.join(tempfile.gettempdir(), f"{tex_name}.dds")
            with open(dds_path, 'wb') as f:
                f.write(texture)
            image = bpy.data.images.load(dds_path)
            image.pack()
            image.use_fake_user = True
        
        images_list.append(image)
    
    if return_tex:
        return images_list

def menu_func_import(self, context):
    self.layout.operator(TMD2_IMPORTER_OT_IMPORT.bl_idname,
                        text='TamSoft TMD2 (.tmd2)',
                        icon='IMPORT')
