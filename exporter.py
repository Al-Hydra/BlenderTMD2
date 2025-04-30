import bpy, bmesh
import os, time
from time import perf_counter
from bpy.props import CollectionProperty, StringProperty, BoolProperty
from bpy.types import Operator, MeshLoopTriangle
from mathutils import Vector, Quaternion, Matrix, Euler
from bpy_extras.io_utils import ExportHelper
from math import radians, tan
from .reader import readTMD2, writeTMD2, writeLDS
from .tamLib.tmd2 import *
from .tamLib.lds import LDS
from collections import defaultdict
from .panels import TMD2MaterialProperties, TMD2MeshProperties, TMD2MaterialTexture
import numpy as np
from math import pi, copysign

class TMD2_EXPORTER_OT_EXPORT(Operator, ExportHelper):
    bl_idname = 'export_scene.tmd2'
    bl_label = 'Export TMD2'
    filename_ext = '.tmd2'
    
    directory: bpy.props.StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    
    collection: StringProperty(
        name='Collection',
        description='The collection to be exported.',
    )
    
    export_textures: BoolProperty(
        name= "Export Textures",
        default=True,
        description= "Export Textures in .lds format "
    )
    
    export_original_bone_data: bpy.props.BoolProperty(
        name="Use Original Bone Data",
        default=True,
        description="Export bone data using stored bone properties whenever possible")

    compress_files: BoolProperty(
        name= "Compress Exported Files",
        default= True,
        description="Apply PZZE/Zlib Compression to models and textures")

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, 'collection', bpy.data, 'collections')
        layout.prop(self, "export_textures")
        layout.prop(self, "export_original_bone_data")
        layout.prop(self, "compress_files")
    
    
    def invoke(self, context, event):
        # Set the collection to the active collection if no collection has been selected
        if not self.collection:
            if bpy.context.collection.name in bpy.data.collections:
                self.collection = bpy.context.collection.name
            else:
                #set the collection to the first collection in the list if the active collection is not in the list
                self.collection = ''
        
        # set the file name to the collection name if no file name has been set
        if not self.filepath:
            self.filepath = self.collection + '.tmd2' if self.collection else 'untitled.tmd2'
        
        # open the file browser
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
    def execute(self, context):
        start_time = time.time()

        collection = bpy.data.collections[self.collection]
        self.tmd2 = TMD2()
        self.tmd2.version = 0x209

        ZUP_TO_YUP = Matrix.Rotation(radians(-90), 4, 'X')
        YUP_3X3 = ZUP_TO_YUP.to_3x3()

        bbmin, bbmax = get_collection_bbox(collection)
        self.tmd2.boundingBox = list(bbmin) + list(bbmax)

        armature, meshes = None, []
        for obj in collection.objects:
            if obj.type == "ARMATURE":
                if armature is not None:
                    raise Exception("THERE CAN ONLY BE 1 ARMATURE IN A TMD2 FILE")
                armature = obj
            elif obj.type == "MESH":
                meshes.append(obj)

        # Armature Export
        if armature:
            if self.export_original_bone_data:
                self.make_bones_original(armature, ZUP_TO_YUP)
            else:
                self.make_bones(armature, ZUP_TO_YUP)

        # Material and Texture Caching
        materials = {}
        textures = {}
        def get_or_create_material(material):
            if material.name in materials:
                return materials[material.name]
            mat_props = material.tmd2_material
            tmd2_mat = TMD2Material()
            tmd2_mat.hash = int(mat_props.material_hash)
            tmd2_mat.shaderID = mat_props.shader_id
            tmd2_mat.shaderParams = [p.value for p in mat_props.param_values]
            tmd2_mat.textures = []
            for i, tex in enumerate(mat_props.textures):
                t2tex = textures.get(int(tex.texture_hash))
                if not t2tex:
                    t2tex = TMD2Texture()
                    t2tex.hash = int(tex.texture_hash)
                    t2tex.width, t2tex.height = tex.image.size if tex.image else (0, 0)
                    tex.image.pack()
                    t2tex.data = tex.image.packed_file.data
                    t2tex.index = len(textures)
                    t2tex.format = 0x5252
                    textures[t2tex.hash] = t2tex
                t2mattex = TMD2MatTexture()
                t2mattex.texture = t2tex
                t2mattex.textureHash = int(tex.texture_hash)
                t2mattex.unk1 = tex.value1
                t2mattex.unk2 = tex.value2
                t2mattex.slot = i
                tmd2_mat.textures.append(t2mattex)
            materials[material.name] = tmd2_mat
            return tmd2_mat

        for mesh_obj in meshes:
            mesh_data = mesh_obj.data
            mesh_data.calc_loop_triangles()
            mesh_data.calc_tangents()

            model = TMD2Model()
            model.name = mesh_obj.name
            mesh_props = mesh_obj.tmd2_mesh
            
            if mesh_props.has_hash:
                model.hashFlag = 1

            if mesh_props.has_name:
                model.nameFlag = 4

            hashed_name = tamCRC32(mesh_obj.name)
            if mesh_props.has_hash and int(mesh_props.name_hash) != hashed_name:
                model.hash = hashed_name
            elif not mesh_props.has_hash:
                model.hashFlag = 0
                model.hash = 0
            else:
                model.hash = int(mesh_props.name_hash)

            uv_layers = mesh_data.uv_layers
            color_layers = mesh_data.color_attributes

            self.tmd2.modelFlags |= 0x1 | 0x2 | 0x4 | 0x8 |  0x100 | 0x1000
            uv_count = 0
            color_count = 0
            if len(uv_layers) >= 1:
                self.tmd2.modelFlags |= 0x10
                uv_count = 1
            if len(uv_layers) >= 2:
                self.tmd2.modelFlags |= 0x20
                uv_count = 2
            if len(uv_layers) >= 3:
                self.tmd2.modelFlags |= 0x40
                uv_count = 3

            if len(color_layers) >= 1:
                self.tmd2.modelFlags |= 0x80
                color_count = 1
            if len(color_layers) >= 2:
                self.tmd2.modelFlags |= 0x200
                color_count = 2

            world_bbox = [ZUP_TO_YUP @ (mesh_obj.matrix_world @ Vector(corner)) for corner in mesh_obj.bound_box]
            min_corner = Vector((min(v[i] for v in world_bbox) for i in range(3)))
            max_corner = Vector((max(v[i] for v in world_bbox) for i in range(3)))
            model.boundingBox = list(min_corner) + list(max_corner)

            vgroup_names = {i: g.name for i, g in enumerate(mesh_obj.vertex_groups)}
            if vgroup_names:
                self.tmd2.modelFlags |= 0x400
            used_bone_ids = set()

            tris_by_mat = defaultdict(list)
            for tri in mesh_data.loop_triangles:
                tris_by_mat[tri.material_index].append(tri)

            for mat_index, tri_group in tris_by_mat.items():
                submesh = TMD2Submesh()
                material = mesh_data.materials[mat_index]
                submesh.material = get_or_create_material(material)

                vertex_cache = {}
                vertex_index = 0
                for tri in tri_group:
                    triangle = []
                    for loop_idx in tri.loops:
                        loop = mesh_data.loops[loop_idx]
                        vert = mesh_data.vertices[loop.vertex_index]
                        uvs = tuple(tuple(uv_layers[i].data[loop_idx].uv) for i in range(uv_count))
                        colors = tuple(tuple(color_layers[i].data[loop_idx].color) for i in range(color_count))
                        weights_key = ()
                        if armature:
                            groups = sorted(vert.groups, key=lambda g: 1 - g.weight)
                            b_weights = [(vgroup_names[g.group], g.weight)
                                        for g in groups if vgroup_names[g.group] in armature.data.bones]
                            b_weights = (b_weights + [(None, 0.0)] * 8)[:8]

                            total = sum(w for _, w in b_weights)
                            bone_ids = [armature.data.bones.find(name) if name else 0 for name, _ in b_weights]
                            weights = [(w / total) if total > 0 else default for (_, w), default in zip(b_weights, [1, 0, 0, 0, 0, 0, 0, 0])]

                            ids = bone_ids + [0] * (8 - len(bone_ids))
                            weights += [0.0] * (8 - len(weights))
                            weights_key = tuple(ids + weights)
                            

                        key = hash((
                            loop.vertex_index,
                            tuple(loop.normal),
                            tuple(loop.tangent),
                            tuple(loop.bitangent),
                            uvs,
                            colors,
                            weights_key
                        ))

                        if key not in vertex_cache:
                            v = TMD2Vertex()
                            co = mesh_obj.matrix_world @ vert.co
                            v.position = list(ZUP_TO_YUP @ co)
                            v.normal = list(Vector(YUP_3X3 @ loop.normal).normalized())
                            v.normal2 = list(Vector(YUP_3X3 @ vert.normal).normalized())
                            v.tangent = list(Vector(YUP_3X3 @ loop.tangent).normalized())
                            v.binormal = list(Vector(YUP_3X3 @ loop.bitangent).normalized())
                            for i in range(uv_count):
                                uv = uv_layers[i].data[loop_idx].uv
                                uv = [uv[0], 1 - uv[1]]
                                setattr(v, f"uv{i+1 if i else ''}", list(uv))
                            for i in range(color_count):
                                col = color_layers[i].data[loop_idx].color_srgb
                                setattr(v, f"color{i+1 if i else ''}", list(col))
                            if armature:
                                v.boneIDs, v.boneWeights = ids[:4], weights[:4]
                                v.boneIDs2, v.boneWeights2 = ids[4:], weights[4:]
                                if len(ids) > 4:
                                    self.tmd2.modelFlags |= 0x8000
                            vertex_cache[key] = vertex_index
                            submesh.vertices.append(v)
                            vertex_index += 1
                        triangle.append(vertex_cache[key])
                    submesh.triangles.append(triangle)
                model.meshes.append(submesh)
            self.tmd2.models.append(model)

        self.tmd2.materials = list(materials.values())
        self.tmd2.textures = list(textures.values())
        self.tmd2.unkSections = []
        for i in range(len(self.tmd2.models) + 1):
            unkSec = TMD2Unk()
            unkSec.values = [0] * 24
            self.tmd2.unkSections.append(unkSec)
        writeTMD2(self.tmd2, self.filepath, self.compress_files)
        
        #export textures
        if self.export_textures:
            tex_path = f"{self.filepath[:-5]}.lds"
            
            lds = LDS()
            lds.textures = [tex.data for tex in textures.values()]
            
            #get textures object
            texobj = None
            for obj in collection.objects:
                if obj.name.startswith("TMD2 TEXTURE PROPERTIES"):
                    texobj = obj
            
            if texobj:
                lds.unk = texobj.tmd2_texture.texture_flags
            
            writeLDS(lds, tex_path, self.compress_files)
        
        self.report({'INFO'}, f"Export completed in {time.time() - start_time} seconds")
        return {'FINISHED'}
    
    
    def make_bones(self, armature, ZUP_TO_YUP):
        pose_values = []
        self.tmd2.modelFlags |= 0x2000
        bone_indices = {b.name: i for i, b in enumerate(armature.data.bones)}
        for bone in armature.data.bones:
            tmbone = TMD2Bone()
            tmbone.name = bone.name
            tmbone.hash = int(bone.get("hash", tamCRC32(bone.name)))
            tmbone.matrix = (ZUP_TO_YUP @ bone.matrix_local).inverted().transposed()
            
            
            #pose bone
            pbone = armature.pose.bones[bone.name]
            if pbone.rotation_quaternion != Quaternion(): #quick check to see if the bone is rotatedroot
                quat = pbone.rotation_quaternion
                angle = quat.angle
                sign = copysign(1.0, quat.z)
                tmbone.offset = [0,0, angle * -sign]
                tmbone.extra = len(pose_values)
                pose_values.append(tmbone.offset)
            else:
                tmbone.extra = -1
                
            
            if bone.parent:
                tmbone.parentIndex = bone_indices[bone.parent.name]
                local_pos = pbone.head - pbone.parent.head
            else:
                tmbone.parentIndex = -1
                local_pos = pbone.head
            
            tmbone.posedLocation = list(ZUP_TO_YUP @ local_pos)
            
            self.tmd2.bones.append(tmbone)


    def make_bones_original(self, armature, ZUP_TO_YUP):
        pose_index = 0
        self.tmd2.modelFlags |= 0x2000
        bone_indices = {b.name: i for i, b in enumerate(armature.data.bones)}
        for bone in armature.data.bones:
            tmbone = TMD2Bone()
            tmbone.name = bone.name
            tmbone.hash = int(bone.get("hash", tamCRC32(bone.name)))
            tmbone.matrix = Matrix(bone["matrix"]).inverted().transposed()
            
            
            #pose bone
            pbone = armature.pose.bones[bone.name]
            if bone.get("extra") is not None and bone.get("extra") > -1:
                tmbone.offset = list(bone["offset"])
                tmbone.extra = pose_index
                pose_index += 1
            else:
                tmbone.extra = -1
                
            
            if bone.parent:
                tmbone.parentIndex = bone_indices[bone.parent.name]
                local_pos = pbone.head - pbone.parent.head
            else:
                tmbone.parentIndex = -1
                local_pos = pbone.head
            
            if bone.get("posedLoc"):
                tmbone.posedLocation = list(bone["posedLoc"])
            else:
                tmbone.posedLocation = list(ZUP_TO_YUP @ local_pos)
            
            self.tmd2.bones.append(tmbone)



def get_collection_bbox(collection):
    ZUP_TO_YUP = Matrix.Rotation(radians(-90), 4, 'X')
    all_world_points = []

    for obj in collection.objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            corrected_corner = ZUP_TO_YUP @ world_corner
            all_world_points.append(corrected_corner)

    if not all_world_points:
        return None

    min_corner = Vector((min(v[i] for v in all_world_points) for i in range(3)))
    max_corner = Vector((max(v[i] for v in all_world_points) for i in range(3)))
    return min_corner, max_corner



def menu_func_export(self, context):
    self.layout.operator(TMD2_EXPORTER_OT_EXPORT.bl_idname,
                        text='TamSoft TMD2 Exporter (.tmd2)',
                        icon='EXPORT')