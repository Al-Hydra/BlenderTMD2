import bpy, bmesh
import os, time
from time import perf_counter
from bpy.props import CollectionProperty, StringProperty, BoolProperty
from bpy.types import Operator, MeshLoopTriangle
from mathutils import Vector, Quaternion, Matrix, Euler
from bpy_extras.io_utils import ExportHelper, axis_conversion
from math import radians, tan
from .reader import readTMD2, readTMD, writeTMD2, writeTMD, writeLDS
from .tamLib.tmd2 import *
from .tamLib.tmd import *
from .tamLib.lds import LDS
from collections import defaultdict
from .panels import TMD2MaterialProperties, TMD2MeshProperties, TMD2MaterialTexture
import numpy as np
from math import pi, copysign

class TMD2_EXPORTER_OT_EXPORT(Operator, ExportHelper):
    bl_idname = 'export_scene.tmd2'
    bl_label = 'Export TMD2'
    filename_ext = ''
    
    directory: bpy.props.StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    
    collection: StringProperty(
        name='Collection',
        description='The collection to be exported.',
    )
    
    tmd_version: bpy.props.EnumProperty(
        name="Version",
        items=[
            ('0x209', "TMD2 0x209", "TMD2"),
            ('0x208', "TMD2 0x208", "TMD2"),
            ('0x207', "TMD2 0x207", "TMD2"),
            ('0x206', "TMD2 0x206", "TMD2"),
            ('0x205', "TMD2 0x205", "TMD2"),
            ('0x204', "TMD2 0x204", "TMD2"),
            ('0x201', "TMD 0x201", "TMD"),
        ],
        default='0x209',
        description="Select the TMD version to export to. TMD2 is the default."
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
    
    inject: BoolProperty(
        name="Inject into Existing TMD",
        default=False,
        description="Inject exported data into an existing file"
    )

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, 'collection', bpy.data, 'collections')
        layout.prop(self, "tmd_version")
        layout.prop(self, "inject")
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
            #self.filepath = self.collection + '.tmd2' if self.collection else 'untitled.tmd2'
            self.filepath = self.collection if self.collection else 'untitled'
        
        # open the file browser
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
    def execute(self, context):
        start_time = time.time()

        collection = bpy.data.collections[self.collection]
        
        if int(self.tmd_version, 16) > 0x201:
            self.tmd = TMD2()
            self.tmd.version = int(self.tmd_version, 16)
            self.export_tmd2(collection)
        else:
            self.tmd = TMD()
            self.tmd.version = int(self.tmd_version, 16)
            
            if self.inject:
                existing_tmd: TMD = readTMD(self.filepath + ".tmd")
                self.tmd = existing_tmd
                self.tmd.models = []
                #self.tmd.materials = []
                #self.tmd.materialTextures = []
                #self.tmd.textures = []
                self.export_tmd(collection, self.tmd)
            
            else:
                self.tmd.TransformationFramesCount = 0
                self.export_tmd(collection)
        
        self.report({'INFO'}, f"Export completed in {time.time() - start_time} seconds")
        return {'FINISHED'}
    
    
    def export_tmd2(self, collection):
        

        ZUP_TO_YUP = Matrix.Rotation(radians(-90), 4, 'X')
        YUP_3X3 = ZUP_TO_YUP.to_3x3()
        
        #get textures object
        props_obj = None
        for obj in collection.objects:
            if "#TMD PROPERTIES" in obj.name:
                props_obj = obj
                break
        if not props_obj:
            #we'll set those values to 0x00
            self.tmd.flag1 = 0x00
            self.tmd.flag2 = 0x00
            self.tmd.animFlag = 0x00
            self.tmd.afterImageValue = 0x00
        else:
            self.tmd.flag1 = props_obj.tmd2_props.flag1
            self.tmd.flag2 = props_obj.tmd2_props.flag2
            self.tmd.animFlag = props_obj.tmd2_props.flag3
            self.tmd.afterImageValue = props_obj.tmd2_props.after_image


        bbmin, bbmax, bbcorners = get_collection_bbox(collection)
        self.tmd.boundingBox = list(bbmin) + list(bbmax)
        bboxcorners = TMD2BoundingBox()
        bboxcorners.corners = bbcorners
        self.tmd.BBoxCorners.append(bboxcorners)
        
        
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
                #t2tex = textures.get(int(tex.texture_hash))
                t2tex = textures.get(tamCRC32(tex.image.name) if tex.image else 0)
                if not t2tex:
                    t2tex = TMD2Texture()
                    #t2tex.hash = int(tex.texture_hash)
                    t2tex.hash = tamCRC32(tex.image.name) if tex.image else 0
                    t2tex.width, t2tex.height = tex.image.size if tex.image else (0, 0)
                    if tex.image and self.export_textures:
                        tex.image.pack()
                        t2tex.data = tex.image.packed_file.data
                        
                    t2tex.index = len(textures)
                    t2tex.format = 0x5252
                    textures[t2tex.hash] = t2tex
                t2mattex = TMD2MatTexture()
                t2mattex.texture = t2tex
               # t2mattex.textureHash = int(tex.texture_hash)
                t2mattex.textureHash = tamCRC32(tex.image.name) if tex.image else 0
                t2mattex.unk1 = tex.value1
                t2mattex.unk2 = tex.value2
                t2mattex.slot = i
                tmd2_mat.textures.append(t2mattex)
            materials[material.name] = tmd2_mat
            return tmd2_mat

        global_vertex_buffer = []
        global_face_buffer = []
        global_vertex_count = 0
        global_face_count = 0
        for mesh_obj in meshes:
            mesh_data = mesh_obj.data
            mesh_data.calc_loop_triangles()
            mesh_data.calc_tangents()

            model = TMD2Model()
            #remove anythinng after .
            model.name = mesh_obj.name.split(".")[0]
            mesh_props = mesh_obj.tmd2_mesh
            
            if mesh_props.has_hash:
                model.hashFlag = 1

            if mesh_props.has_name:
                model.nameFlag = 4
                
            if mesh_props.has_extra:
                model.nameFlag = 3
                model.unk1 = mesh_props.unk1
                model.unk2 = mesh_props.unk2
                model.unk3 = mesh_props.unk3

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

            self.tmd.modelFlags |= 0x1 | 0x2 | 0x4 | 0x8 |  0x100 | 0x1000
            uv_count = 0
            color_count = 0
            if len(uv_layers) >= 1:
                self.tmd.modelFlags |= 0x10
                uv_count = 1
            if len(uv_layers) >= 2:
                self.tmd.modelFlags |= 0x20
                uv_count = 2
            if len(uv_layers) >= 3:
                self.tmd.modelFlags |= 0x40
                uv_count = 3

            if len(color_layers) >= 1:
                self.tmd.modelFlags |= 0x80
                color_count = 1
            if len(color_layers) >= 2:
                self.tmd.modelFlags |= 0x200
                color_count = 2

            world_bbox = [ZUP_TO_YUP @ (mesh_obj.matrix_world @ Vector(corner)) for corner in mesh_obj.bound_box]
            min_corner = Vector((min(v[i] for v in world_bbox) for i in range(3)))
            max_corner = Vector((max(v[i] for v in world_bbox) for i in range(3)))
            model.boundingBox = list(min_corner) + list(max_corner)
            bboxcorners = TMD2BoundingBox()
            bboxcorners.corners = [list(world_bbox[i]) for i in [6, 2, 7, 3, 4, 0, 5, 1]]
            self.tmd.BBoxCorners.append(bboxcorners)

            vgroup_names = {i: g.name for i, g in enumerate(mesh_obj.vertex_groups)}
            if vgroup_names:
                self.tmd.modelFlags |= 0x400
                # Enable 8 bone influences (flag 0x8000)
                self.tmd.modelFlags |= 0x8000
            used_bone_ids = set()
            
            loop_data = extract_loop_data_numpy(mesh_obj, {b.name: i for i, b in enumerate(armature.data.bones)} if armature else {}, max_influences=8)
            
            #create a structured array from the loop data
            vertex_data = [loop_data["position"]] # positions are always there
            vertex_attributes = ["position"]
            # weights next
            if self.tmd.modelFlags & 0x400:
                vertex_data.append(loop_data["weights"])
                vertex_attributes.append("weights")
                vertex_data.append(loop_data["boneIDs"])
                vertex_attributes.append("boneIDs")
            
            # custom normals
            vertex_data.append(loop_data["custom_normal"])
            vertex_attributes.append("custom_normal")
            # tangents and bitangents
            if "tangent" in loop_data:
                vertex_data.append(loop_data["tangent"])
                vertex_data.append(loop_data["tangent_sign"])
                vertex_attributes.extend(["tangent", "tangent_sign"])
            if "bitangent" in loop_data:
                vertex_data.append(loop_data["bitangent"])
                vertex_data.append(loop_data["bitangent_sign"])
                vertex_attributes.extend(["bitangent", "bitangent_sign"])
            if "color0" in loop_data:
                vertex_data.append(loop_data["color0"])
                vertex_attributes.append("color0")
            if "real_normal" in loop_data:
                vertex_data.append(loop_data["real_normal"])
                vertex_attributes.append("real_normal")
            if "color1" in loop_data:
                vertex_data.append(loop_data["color1"])
                vertex_attributes.append("color1")
            if "uv0" in loop_data:
                vertex_data.append(loop_data["uv0"])
                vertex_attributes.append("uv0")
            if "uv1" in loop_data:
                vertex_data.append(loop_data["uv1"])
                vertex_attributes.append("uv1")
            if "uv2" in loop_data:
                vertex_data.append(loop_data["uv2"])
                vertex_attributes.append("uv2")
            
            # make a big structured array
            # build dtype with shapes
            fields = []
            for name, data in zip(vertex_attributes, vertex_data):
                fields.append((name, data.dtype, data.shape[1:]))

            vertex_dtype = np.dtype(fields)

            # allocate array
            vertex_array = np.empty(len(loop_data["position"]), dtype=vertex_dtype)

            # fill in
            for name, data in zip(vertex_attributes, vertex_data):
                vertex_array[name] = data
            
            triangles = loop_data['loop_tri_indices']
            material_indices = loop_data['material_indices']
            
            vertex_array, triangles, material_indices = dedupe_vertices_structured(vertex_array, loop_data['loop_tri_indices'], loop_data['material_indices'])
            
            sorted_materials = np.argsort(material_indices)
            sorted_materials_indices = material_indices[sorted_materials]
            sorted_triangles = triangles[sorted_materials]
            
            #remap triangle indices to global
            sorted_triangles += global_vertex_count
            
            global_vertex_buffer.append(vertex_array)
            global_vertex_count += len(vertex_array)
                        
            global_face_buffer.extend(sorted_triangles)
            global_face_count += len(sorted_triangles)
            
            
            # find the boundaries where the material index changes
            change_indices = np.where(np.diff(sorted_materials_indices) != 0)[0] + 1
            material_boundaries = np.split(sorted_triangles, change_indices)
            

            # make the submeshes
            submeshes = []
            for i, tri_group in enumerate(material_boundaries):
                submesh = TMD2Submesh()
                material = mesh_obj.material_slots[i].material
                submesh.material = get_or_create_material(material)
                submesh.triangles = tri_group
                submeshes.append(submesh)
            
            model.meshes = submeshes
            self.tmd.models.append(model)
            

        self.tmd.materials = list(materials.values())
        self.tmd.textures = list(textures.values())
        
        #combine global vertex and face buffers
        self.tmd.vertices = np.concatenate(global_vertex_buffer)
        if len(self.tmd.vertices) > 0xFFFF:
            self.tmd.modelFlags |= 0x800
        
        self.tmd.triangles = np.array(global_face_buffer, dtype=np.uint32)
        
        writeTMD2(self.tmd, f"{self.filepath}.tmd2", self.compress_files)
        
        #export textures
        if self.export_textures:
            tex_path = f"{self.filepath}.lds"
            
            lds = LDS()
            lds.textures = [tex.data for tex in textures.values()]
            
            writeLDS(lds, tex_path, self.compress_files)

    
    
    def make_bones(self, armature, ZUP_TO_YUP):
        pose_values = []
        self.tmd.modelFlags |= 0x2000
        bone_indices = {b.name: i for i, b in enumerate(armature.data.bones)}
        up_matrix = axis_conversion(from_forward='Y', from_up='Z', to_forward='-Z', to_up='Y').to_4x4()
        
        
        for bone in armature.data.bones:
            tmbone = TMD2Bone()
            tmbone.name = bone.name
            tmbone.hash = int(bone.get("hash", tamCRC32(bone.name)))
            tmbone.matrix = (up_matrix @ bone.matrix_local).inverted().transposed()
            
            
            #pose bone
            pbone = armature.pose.bones[bone.name]
            if pbone.rotation_quaternion != Quaternion(): #quick check to see if the bone is rotated
                quat = pbone.rotation_quaternion.inverted()
                rotation = quat.to_euler()
                tmbone.offset = [rotation.x, rotation.y, rotation.z]
                tmbone.extra = len(pose_values)
                pose_values.append(tmbone.offset)
            
            elif pbone.rotation_euler != Euler(): #check if the bone is rotated with euler angles
                rotation = pbone.rotation_euler
                tmbone.offset = [rotation.x, rotation.y, rotation.z]
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
            
            tmbone.posedLocation = list(up_matrix @ local_pos)
            
            self.tmd.bones.append(tmbone)


    def make_bones_original(self, armature, ZUP_TO_YUP):
        pose_index = 0
        self.tmd.modelFlags |= 0x2000
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
            
            self.tmd.bones.append(tmbone)
        
    
    
    def make_bones_TMD(self, armature, ZUP_TO_YUP):
        pose_values = []
        self.tmd.modelFlags |= 0x2000
        bone_indices = {b.name: i for i, b in enumerate(armature.data.bones)}
        for bone in armature.data.bones:
            tmbone = TMDBone()
            tmbone.name = bone.name
            tmbone.hash = int(bone.get("hash", tamCRC32(bone.name)))
            tmbone.matrix = (ZUP_TO_YUP @ bone.matrix_local).inverted().transposed()
            
            
            #pose bone
            pbone = armature.pose.bones[bone.name]
            if pbone.rotation_quaternion != Quaternion(): #quick check to see if the bone is rotated
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
            
            self.tmd.bones.append(tmbone)


    def make_bones_original_TMD(self, armature, ZUP_TO_YUP):
        pose_index = 0
        self.tmd.modelFlags |= 0x2000
        bone_indices = {b.name: i for i, b in enumerate(armature.data.bones)}
        for bone in armature.data.bones:
            tmbone = TMDBone()
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
            
            self.tmd.bones.append(tmbone)
    
    
    def export_tmd(self, collection, tmd = None):

        ZUP_TO_YUP = Matrix.Rotation(radians(-90), 4, 'X')
        YUP_3X3 = ZUP_TO_YUP.to_3x3()

        bbmin, bbmax, corners = get_collection_bbox(collection)
        self.tmd.boundingBox = list(bbmin) + list(bbmax)
        
        if not tmd:
            self.tmd.animFlag = 0
            self.tmd.TransformationFramesCount = 0
            self.tmd.TransformationFrames = []

        armature, meshes = None, []
        for obj in collection.objects:
            if obj.type == "ARMATURE":
                if armature is not None:
                    raise Exception("THERE CAN ONLY BE 1 ARMATURE IN A TMD FILE")
                armature = obj
            elif obj.type == "MESH":
                meshes.append(obj)

        # Armature Export
        if armature and not tmd:
            if self.export_original_bone_data:
                self.make_bones_original_TMD(armature, ZUP_TO_YUP)
            else:
                self.make_bones_original_TMD(armature, ZUP_TO_YUP)

        # Material and Texture Caching
        if tmd:
            materials = {mat.hash: mat for mat in tmd.materials}
            textures = {tex.hash: tex for tex in tmd.textures}
            materialTextures = [mt for mt in tmd.materialTextures]
        else:
            materials = {}
            textures = {}
            materialTextures = []
        
        def get_or_create_material(material):
            if material.name in materials:
                return materials[material.name]
            mat_props = material.tmd2_material
            tmd2_mat = TMDMaterial()
            #tmd2_mat.hash = tamCRC32(material.name)#int(mat_props.material_hash)
            tmd2_mat.hash = int(mat_props.material_hash)
            tmd2_mat.shaderID = mat_props.shader_id
            tmd2_mat.shaderParams = [p.value for p in mat_props.param_values]
            tmd2_mat.textures = []
            for i, tex in enumerate(mat_props.textures):
                #t2tex = textures.get(tamCRC32(tex.image.name) if tex.image else int(tex.texture_hash)) #textures.get(int(tex.texture_hash))
                t2tex = textures.get(int(tex.texture_hash))
                if not t2tex:
                    t2tex = TMDTexture()
                    #t2tex.hash = tamCRC32(tex.image.name) if tex.image else int(tex.texture_hash)
                    t2tex.hash = int(tex.texture_hash)
                    t2tex.width, t2tex.height = tex.image.size if tex.image else (0, 0)
                    try:
                        tex.image.pack()
                        t2tex.data = tex.image.packed_file.data
                    except:
                        t2tex.data = b""
                    t2tex.index = len(textures)
                    t2tex.format = 0x5252
                    textures[t2tex.hash] = t2tex
                t2mattex = TMDMatTexture()
                t2mattex.texture = t2tex
                t2mattex.textureHash = tamCRC32(tex.image.name) if tex.image else int(tex.texture_hash)
                t2mattex.unk1 = tex.value1
                t2mattex.unk2 = tex.value2
                t2mattex.slot = i
                tmd2_mat.textures.append(t2mattex)
                materialTextures.append(t2mattex)
            materials[material.name] = tmd2_mat
            return tmd2_mat

        global_vertex_buffer = []
        global_face_buffer = []
        global_vertex_count = 0
        global_face_count = 0
        for mesh_obj in meshes:
            mesh_data = mesh_obj.data
            mesh_data.calc_loop_triangles()
            mesh_data.calc_tangents()

            model = TMDModel()
            #remove anythinng after .
            model.name = mesh_obj.name.split(".")[0]
            model.name = mesh_obj.tmd2_mesh.name
            mesh_props = mesh_obj.tmd2_mesh
            
            if mesh_props.has_hash:
                model.hashFlag = 1

            if mesh_props.has_name:
                model.nameFlag = 4
                
            if mesh_props.has_extra:
                model.nameFlag = 3
                model.unk1 = mesh_props.unk1
                model.unk2 = mesh_props.unk2
                model.unk3 = mesh_props.unk3

            hashed_name = tamCRC32(mesh_obj.name)
            if mesh_props.has_hash and int(mesh_props.name_hash) != hashed_name and not mesh_props.has_extra:
                model.hash = hashed_name
            elif not mesh_props.has_hash:
                model.hashFlag = 0
                model.hash = int(mesh_props.name_hash) if mesh_props.name_hash else 0
            else:
                model.hash = int(mesh_props.name_hash) if mesh_props.name_hash else 0

            uv_layers = mesh_data.uv_layers
            color_layers = mesh_data.color_attributes

            self.tmd.modelFlags |= 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x4000
            uv_count = 0
            color_count = 0
            if len(uv_layers) >= 1:
                self.tmd.modelFlags |= 0x10
                uv_count = 1
            if len(uv_layers) >= 2:
                self.tmd.modelFlags |= 0x20
                uv_count = 2
            if len(uv_layers) >= 3:
                self.tmd.modelFlags |= 0x40
                uv_count = 3

            if len(color_layers) >= 1:
                self.tmd.modelFlags |= 0x80
                color_count = 1
            if len(color_layers) >= 2:
                self.tmd.modelFlags |= 0x200
                color_count = 2

            world_bbox = [ZUP_TO_YUP @ (mesh_obj.matrix_world @ Vector(corner)) for corner in mesh_obj.bound_box]
            min_corner = Vector((min(v[i] for v in world_bbox) for i in range(3)))
            max_corner = Vector((max(v[i] for v in world_bbox) for i in range(3)))
            model.boundingBox = list(min_corner) + list(max_corner)

            vgroup_names = {i: g.name for i, g in enumerate(mesh_obj.vertex_groups)}
            if vgroup_names:
                self.tmd.modelFlags |= 0x400
            used_bone_ids = set()

            loop_data = extract_loop_data_numpy(mesh_obj, {b.name: i for i, b in enumerate(armature.data.bones)} if armature else {}, max_influences=4)
            
            #create a structured array from the loop data
            vertex_data = [loop_data["position"]] # positions are always there
            vertex_attributes = ["position"]
            # weights next
            if self.tmd.modelFlags & 0x400:
                vertex_data.append(loop_data["weights"])
                vertex_attributes.append("weights")
                vertex_data.append(loop_data["boneIDs"])
                vertex_attributes.append("boneIDs")
            
            # custom normals
            vertex_data.append(loop_data["custom_normal"])
            vertex_attributes.append("custom_normal")
            # tangents and bitangents
            if "tangent" in loop_data:
                vertex_data.append(loop_data["tangent"])
                vertex_data.append(loop_data["tangent_sign"])
                vertex_attributes.extend(["tangent", "tangent_sign"])
            if "bitangent" in loop_data:
                vertex_data.append(loop_data["bitangent"])
                vertex_data.append(loop_data["bitangent_sign"])
                vertex_attributes.extend(["bitangent", "bitangent_sign"])
            if "color0" in loop_data:
                vertex_data.append(loop_data["color0"])
                vertex_attributes.append("color0")
            if "real_normal" in loop_data:
                vertex_data.append(loop_data["real_normal"])
                vertex_attributes.append("real_normal")
            if "color1" in loop_data:
                vertex_data.append(loop_data["color1"])
                vertex_attributes.append("color1")
            if "uv0" in loop_data:
                vertex_data.append(loop_data["uv0"])
                vertex_attributes.append("uv0")
            if "uv1" in loop_data:
                vertex_data.append(loop_data["uv1"])
                vertex_attributes.append("uv1")
            if "uv2" in loop_data:
                vertex_data.append(loop_data["uv2"])
                vertex_attributes.append("uv2")
            
            # make a big structured array
            # build dtype with shapes
            fields = []
            for name, data in zip(vertex_attributes, vertex_data):
                fields.append((name, data.dtype, data.shape[1:]))

            vertex_dtype = np.dtype(fields)

            # allocate array
            vertex_array = np.empty(len(loop_data["position"]), dtype=vertex_dtype)

            # fill in
            for name, data in zip(vertex_attributes, vertex_data):
                vertex_array[name] = data
            
            triangles = loop_data['loop_tri_indices']
            material_indices = loop_data['material_indices']
            
            vertex_array, triangles, material_indices = dedupe_vertices_structured(vertex_array, loop_data['loop_tri_indices'], loop_data['material_indices'])
            
            sorted_materials = np.argsort(material_indices)
            sorted_materials_indices = material_indices[sorted_materials]
            sorted_triangles = triangles[sorted_materials]
            
            #remap triangle indices to global
            sorted_triangles += global_vertex_count
            
            global_vertex_buffer.append(vertex_array)
            global_vertex_count += len(vertex_array)
                        
            global_face_buffer.extend(sorted_triangles)
            global_face_count += len(sorted_triangles)
            
            
            # find the boundaries where the material index changes
            change_indices = np.where(np.diff(sorted_materials_indices) != 0)[0] + 1
            material_boundaries = np.split(sorted_triangles, change_indices)
            

            # make the submeshes
            submeshes = []
            for i, tri_group in enumerate(material_boundaries):
                submesh = TMDSubmesh()
                material = mesh_obj.material_slots[i].material
                if self.inject:
                    #find existing material by hash
                    existing_mat = None
                    for mat in self.tmd.materials:
                        if mat.hash == int(material.tmd2_material.material_hash):
                            existing_mat = mat
                            break
                    if existing_mat:
                        submesh.material = existing_mat
                    else:
                        submesh.material = get_or_create_material(material)
                else:
                    submesh.material = get_or_create_material(material)
                submesh.triangles = tri_group
                submeshes.append(submesh)
            
            model.meshes = submeshes
            self.tmd.models.append(model)
            
        if not self.inject:
            self.tmd.materials = list(materials.values())
            self.tmd.textures = list(textures.values())
        
        #combine global vertex and face buffers
        self.tmd.vertices = np.concatenate(global_vertex_buffer)
        if len(self.tmd.vertices) > 0xFFFF:
            self.tmd.modelFlags |= 0x800
        
        self.tmd.triangles = np.array(global_face_buffer, dtype=np.uint32)

        writeTMD(self.tmd, f"{self.filepath}.tmd")


def extract_loop_data_numpy(mesh_obj, bone_name_to_index, max_influences=4):    
    mesh = mesh_obj.data
    mesh.calc_loop_triangles()
    
    # mesh 2 is gonna be used to get normals tangent data since we have to triangulate the mesh with bmesh
    mesh2 = mesh.copy()
    if mesh2.attributes.get("custom_normal"):
        mesh2.attributes.remove(mesh2.attributes["custom_normal"])
    
    bm = bmesh.new()
    bm.from_mesh(mesh2)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh2)
    mesh2.calc_loop_triangles()
    mesh2.calc_tangents()
    
    
    num_loops = len(mesh.loops)
    num_verts = len(mesh.vertices)
    num_tris = len(mesh.loop_triangles)

    # === Allocate NumPy arrays ===
    vertex_indices = np.empty(num_loops, dtype=np.int32)
    positions = np.empty((num_loops, 3), dtype=np.float32)
    custom_normals = np.empty((num_loops, 3), dtype=np.float32)
    real_normals = np.empty((num_loops, 3), dtype=np.float32)
    tangents = np.empty((num_loops, 3), dtype=np.float32)
    tangent_signs = np.empty(num_loops, dtype=np.float32)
    bitangents = np.empty((num_loops, 3), dtype=np.float32)
    bitangent_signs = np.empty(num_loops, dtype=np.float32)


    mesh.loops.foreach_get("vertex_index", vertex_indices)

    # we can have up to 3 uv layers and 2 color layers
    # we need to create arrays for each layer
    
    # === UV Layers ===
    uv_layers = mesh.uv_layers
    num_uv_layers = min(3, len(uv_layers))
    uv_arrays = []
    for i in range(num_uv_layers):
        uv_array = np.zeros((num_loops, 2), dtype=np.float32)
        uv_layers[i].data.foreach_get("uv", uv_array.ravel())
        uv_array[:, 1] = 1.0 - uv_array[:, 1]  # Flip V coordinate
        uv_arrays.append(uv_array)

    # === Color Layers ===
    color_layers = mesh.color_attributes
    num_color_layers = min(2, len(color_layers))
    color_arrays = []
    for i in range(num_color_layers):
        color_array = np.zeros((num_loops, 4), dtype=np.float32)
        color_layers[i].data.foreach_get("color_srgb", color_array.ravel())
        color_arrays.append(color_array)


    # === Vertex positions (transformed) ===
    vert_positions = np.empty((num_verts, 3), dtype=np.float32)
    mesh.vertices.foreach_get("co", vert_positions.ravel())
    
    vert_positions = vert_positions[:, [0, 2, 1]]
    vert_positions[:, 2] *= -1.0
    positions = vert_positions[vertex_indices]
    del vert_positions
    
    
    # === Custom Normals ===
    mesh.loops.foreach_get("normal", custom_normals.ravel())
    custom_normals = custom_normals[:, [0, 2, 1]]
    custom_normals[:, 2] *= -1.0
    
    # === Real Normals from triangulated mesh ===
    mesh2.loops.foreach_get("normal", real_normals.ravel())
    real_normals = real_normals[:, [0, 2, 1]]
    real_normals[:, 2] *= -1.0

    # === Tangents and Bitangents from triangulated mesh ===
    mesh.loops.foreach_get("tangent", tangents.ravel())
    tangents = tangents[:, [0, 2, 1]]
    tangents[:, 2] *= -1.0
    mesh.loops.foreach_get("bitangent_sign", tangent_signs)
    
    mesh.loops.foreach_get("bitangent", bitangents.ravel())
    bitangents = bitangents[:, [0, 2, 1]]
    bitangents[:, 2] *= -1.0
    mesh.loops.foreach_get("bitangent_sign", bitangent_signs)
    
    # remove mesh2 as it's no longer needed
    bpy.data.meshes.remove(mesh2)

    # === Fast Bone Weights ===
    vertex_groups = mesh_obj.vertex_groups
    bone_ids = np.zeros((num_loops, max_influences), dtype=np.uint16)
    weights = np.zeros((num_loops, max_influences), dtype=np.float32)

    if bone_name_to_index:
        # Build per-vertex weight lists
        v_bone_ids = np.zeros((num_verts, max_influences), dtype=np.uint16)
        v_weights = np.zeros((num_verts, max_influences), dtype=np.float32)

        for v in mesh.vertices:
            # Collect all weights for this vertex
            vertex_weights = []
            for g in v.groups:
                name = vertex_groups[g.group].name
                if name in bone_name_to_index:
                    vertex_weights.append((bone_name_to_index[name], g.weight))
            
            if vertex_weights:
                # Sort by weight descending
                vertex_weights.sort(key=lambda x: x[1], reverse=True)
                
                # Take top max_influences
                vertex_weights = vertex_weights[:max_influences]
                
                # Extract bone IDs and weights
                for i, (bone_id, weight) in enumerate(vertex_weights):
                    v_bone_ids[v.index, i] = bone_id
                    v_weights[v.index, i] = weight
                
                # Normalize weights
                total = v_weights[v.index].sum()
                if total > 0:
                    v_weights[v.index] /= total
                else:
                    # If no valid weights, default to first bone
                    v_weights[v.index, 0] = 1.0
            else:
                # No weights for this vertex
                v_weights[v.index, 0] = 1.0

        # Broadcast to loops
        bone_ids[:] = v_bone_ids[vertex_indices]
        weights[:] = v_weights[vertex_indices]
    else:
        # No armature - default to first bone with full weight
        weights[:, 0] = 1.0

    # === Triangle index data ===
    loop_tri_indices = np.empty((num_tris, 3), dtype=np.uint32)
    material_indices = np.empty(num_tris, dtype=np.uint8)
    mesh.loop_triangles.foreach_get("loops", loop_tri_indices.ravel())
    mesh.loop_triangles.foreach_get("material_index", material_indices)
    
    mesh_dict = {}
    mesh_dict['position'] = positions
    mesh_dict['custom_normal'] = custom_normals
    mesh_dict['real_normal'] = real_normals
    mesh_dict['tangent'] = tangents
    mesh_dict['tangent_sign'] = tangent_signs
    mesh_dict['bitangent'] = bitangents
    mesh_dict['bitangent_sign'] = bitangent_signs
    mesh_dict['boneIDs'] = bone_ids
    mesh_dict['weights'] = weights
    mesh_dict['loop_tri_indices'] = loop_tri_indices
    mesh_dict['material_indices'] = material_indices
    
    for i, uv_array in enumerate(uv_arrays):
        mesh_dict[f'uv{i}'] = uv_array
    for i, color_array in enumerate(color_arrays):
        mesh_dict[f'color{i}'] = color_array

    return mesh_dict

def dedupe_vertices_structured(verts, tri_indices, material_indices):
    """
    verts: structured numpy array, shape (num_loops,)
    tri_indices: (num_tris, 3) int array referring to loop indices
    material_indices: (num_tris,) int array
    """

    raw = verts.view(np.void)  # shape (num_loops,)

    unique_raw, unique_index, inverse_map = np.unique(
        raw, return_index=True, return_inverse=True
    )

    unique_verts = verts[unique_index]

    unique_tris = inverse_map[tri_indices]

    return unique_verts, unique_tris, material_indices


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

    #create 8 points from the bounding box

    min_corner = Vector((min(v[i] for v in all_world_points) for i in range(3)))
    max_corner = Vector((max(v[i] for v in all_world_points) for i in range(3)))
    
    corners = [
        ( max_corner.x, max_corner.y, min_corner.z ),  # corner[0]
        ( min_corner.x, max_corner.y, min_corner.z ),  # corner[1]
        ( max_corner.x, max_corner.y, max_corner.z ),  # corner[2]
        ( min_corner.x, max_corner.y, max_corner.z ),  # corner[3]
        ( max_corner.x, min_corner.y, min_corner.z ),  # corner[4]
        ( min_corner.x, min_corner.y, min_corner.z ),  # corner[5]
        ( max_corner.x, min_corner.y, max_corner.z ),  # corner[6]
        ( min_corner.x, min_corner.y, max_corner.z ),  # corner[7]
    ]
    
    return min_corner, max_corner, corners



def menu_func_export(self, context):
    self.layout.operator(TMD2_EXPORTER_OT_EXPORT.bl_idname,
                        text='TamSoft TMD2 Exporter (.tmd2)',
                        icon='EXPORT')