import bpy, bmesh, math, mathutils
from mathutils import Vector, Quaternion, Matrix, Euler
from math import radians
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, CollectionProperty
from bpy.types import Operator
from .reader import *
from .tamLib.tmd2 import *
from .tamLib.tmo import *
from .tamLib.lds import LDS
from .tamLib.utils.PyBinaryReader.binary_reader import *
import os, tempfile
import numpy as np
from .materials.shaders import shaders_dict
from collections import defaultdict
from time import perf_counter
import json
from cProfile import Profile
hashes = json.load(open(os.path.join(os.path.dirname(__file__), "hashes.json")))

class TMD2_IMPORTER_OT_IMPORT(Operator, ImportHelper):
    bl_label = "Import TMD2"
    bl_idname = "import_scene.tmd2"


    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    filter_glob: StringProperty(default="*.tmd2;*.lds;*.tmd", options={"HIDDEN"}) # type: ignore
    filename_ext = ".tmd2"
    filepath: StringProperty(subtype='FILE_PATH') # type: ignore
    auto_find_textures: BoolProperty(default=True) # type: ignore
    texture_path: StringProperty(subtype='FILE_PATH') # type: ignore

    def execute(self, context):
        # Split files by type
        tmd2_files = {}
        tmd_files = {}
        lds_files = {}

        for file in self.files:
            full_path = os.path.join(self.directory, file.name)
            base_name, ext = os.path.splitext(file.name.lower())

            if ext == ".tmd2":
                tmd2_files[base_name] = full_path
            elif ext == ".lds":
                lds_files[base_name] = full_path
            elif ext == ".tmd":
                tmd_files[base_name] = full_path

        print(f"🟦 TMD2 files: {list(tmd2_files.keys())}")
        print(f"🟩 TMD files: {list(tmd_files.keys())}")
        print(f"🟨 LDS files: {list(lds_files.keys())}")


        if tmd2_files:
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
                importer = importTMD2(self, tmd2_path, self.as_keywords(ignore=("filter_glob",)), tmd2, {})

                # Store texture path for later use
                importer.texture_path = texture_path

                importer.read(context)
        
        
        if tmd_files:
            # Collect DDS files
            dds_files = {}
            hashed_names = {}
            for file in os.listdir(self.directory):
                if file.lower().endswith(".dds"):
                    base_name, _ = os.path.splitext(file)
                    hashed_name = tamCRC32(base_name)
                    dds_files[base_name] = os.path.join(self.directory, file)
                    hashed_names[hashed_name] = base_name

            # Import TMD files
        
            for base_name, tmd_path in tmd_files.items():
                # Read and import TMD
                tmd = readTMD(tmd_path, hashed_names)
                importer = importTMD(self, tmd_path, self.as_keywords(ignore=("filter_glob",)), tmd, dds_files)
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
        # Collect LDS files
        lds_files = {}
        for file in os.listdir(self.directory):
            if file.lower().endswith(".lds"):
                base_name, _ = os.path.splitext(file.lower())
                lds_files[base_name] = os.path.join(self.directory, file)


        start_time = perf_counter()

        for file in self.files:
            tmd2_path = os.path.join(self.directory, file.name)
            base_name, _ = os.path.splitext(file.name.lower())

            # Try to find matching LDS
            texture_path = ""
            if base_name in lds_files:
                texture_path = lds_files[base_name]
                print(f"✅ Using matching LDS file for {base_name}: {texture_path}")
            else:
                fallback = os.path.join(self.directory, base_name + ".lds")
                if os.path.exists(fallback):
                    texture_path = fallback
                    print(f"📁 Found fallback LDS file for {base_name}: {texture_path}")
                else:
                    print(f"❌ No LDS found for {base_name}, importing TMD2 without texture.")

            # Import TMD2
            #prfl = Profile()
            #prfl.enable()

            tmd2 = readTMD2(tmd2_path)

            #prfl.disable()
            #prfl.print_stats(sort="cumtime")

            importer = importTMD2(self, tmd2_path, self.as_keywords(ignore=("filter_glob",)), tmd2, {})
            importer.texture_path = texture_path
            importer.read(context)
            
        end_time = perf_counter()
        elapsed_time = end_time - start_time
        self.report({'INFO'}, f"Imported {len(self.files)} TMD2 files in {elapsed_time:.2f} seconds.")

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


class DropTMD(Operator):
    """Allows TMD files to be dropped into the viewport to import them"""
    bl_idname = "import_scene.drop_tmd"
    bl_label = "Import TMD"

    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    filter_glob: StringProperty(default="*.tmd2", options={"HIDDEN"}) # type: ignore
    filename_ext = ".tmd2"
    filepath: StringProperty(subtype='FILE_PATH') # type: ignore

    def execute(self, context):
        # Collect DDS files
        dds_files = {}
        hashed_names = {}
        for file in os.listdir(self.directory):
            if file.lower().endswith(".dds"):
                base_name, _ = os.path.splitext(file)
                hashed_name = tamCRC32(base_name)
                dds_files[base_name] = os.path.join(self.directory, file)
                hashed_names[hashed_name] = base_name
        

        for file in self.files:
            tmd_path = os.path.join(self.directory, file.name)

            # Import TMD2
            tmd = readTMD(tmd_path, hashed_names)
            importer = importTMD(self, tmd_path, self.as_keywords(ignore=("filter_glob",)), tmd, dds_files)
            importer.read(context)

        return {'FINISHED'}


class TMD_FH_import(bpy.types.FileHandler):
    bl_idname = "TMD_FH_import"
    bl_label = "File handler for TMD files"
    bl_import_operator = "import_scene.drop_tmd"
    bl_file_extensions = ".tmd"

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


class DropCAT(Operator):
    """Allows cat files to be dropped into the viewport to import them"""
    bl_idname = "import_scene.drop_cat"
    bl_label = "Import cat"

    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    filter_glob: StringProperty(default="*.tmd2", options={"HIDDEN"}) # type: ignore
    filename_ext = ".cat"
    filepath: StringProperty(subtype='FILE_PATH') # type: ignore
    def execute(self, context):
        for file in self.files:
            self.filepath = os.path.join(self.directory, file.name)

            # Read and import CAT
            cat = readCATS(self.filepath)
            for c in cat.subCATS:
                if c.name == "mdl.cat":
                    for i in range(c.catCount):
                        mdl = c.subData[i]
                        name = c.subNames[i]
                        # Read and import TMD2
                        br = BinaryReader(mdl, Endian.LITTLE)
                        tmd2 = br.read_struct(TMD2)
                        print(name)
                        tmd2.name = name
                        importer = importTMD2(self, self.filepath, self.as_keywords(ignore=("filter_glob",)), tmd2, {})
                        importer.read(context)
        
        return {'FINISHED'}

class CAT_FH_import(bpy.types.FileHandler):
    bl_idname = "CAT_FH_import"
    bl_label = "File handler for CAT files"
    bl_import_operator = "import_scene.drop_cat"
    bl_file_extensions = ".cat"

    @classmethod
    def poll_drop(cls, context):
        return (context.area and context.area.type == 'VIEW_3D')
    
    def draw():
        pass


class DropTMO(Operator):
    """Allows cat files to be dropped into the viewport to import them"""
    bl_idname = "import_scene.drop_tmo"
    bl_label = "Import tmo"

    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    filter_glob: StringProperty(default="*.tmo", options={"HIDDEN"}) # type: ignore
    filename_ext = ".tmo"
    filepath: StringProperty(subtype='FILE_PATH') # type: ignore
    def execute(self, context):
        for file in self.files:
            self.filepath = os.path.join(self.directory, file.name)

            tmofile = readTMO(self.filepath)
            
            importer = importTMO(self, self.filepath, self.as_keywords(ignore=("filter_glob",)), tmofile)
            importer.read(context)
        
        return {'FINISHED'}

class TMO_FH_import(bpy.types.FileHandler):
    bl_idname = "TMO_FH_import"
    bl_label = "File handler for TMO files"
    bl_import_operator = "import_scene.drop_tmo"
    bl_file_extensions = ".tmo"

    @classmethod
    def poll_drop(cls, context):
        return (context.area and context.area.type == 'VIEW_3D')
    
    def draw():
        pass


class importTMO:
    def __init__(self, operator: Operator, filepath, import_settings: dict, tmofile):
        self.operator = operator
        self.filepath = filepath
        for key, value in import_settings.items():
            setattr(self, key, value)
        
        self.tmo: TMO = tmofile
    
    
    def read(self, context):
        target = bpy.context.object
        if not target or target.type != 'ARMATURE':
            self.operator.report({'ERROR'}, "No armature selected.")
            return {'CANCELLED'}
        if not target.data:
            self.operator.report({'ERROR'}, "No armature data found.")
            return {'CANCELLED'}
        
        
        index_dict = {0: "location",
                      1: "location",
                      2: "location",
                      3: "rotation_euler",
                      4: "rotation_euler",
                      5: "rotation_euler",
                      6: "scale",
                      7: "scale",
                      8: "scale"}
        
        
        # Create a new action
        action = bpy.data.actions.new(name=f"{self.tmo.name}_action")
        target.animation_data_create()
        target.animation_data.action = action
        
        #create a hash dict for bones
        bone_hashes = {}
        for bone in target.data.bones:
            if "hash" in bone.keys():
                bone_hashes[bone["hash"]] = bone.name
            else:
                bone_hashes[tamCRC32(bone.name)] = bone.name
            
        
        # loop over bones, get their hash and find the corresponding bone in the armature
        for bidx, tmbone in enumerate(self.tmo.hashes):
            bone = target.data.bones.get(bone_hashes.get(str(tmbone), ""))
            if not bone:
                self.operator.report({'ERROR'}, f"Bone {tmbone} not found in armature.")
                continue
            else:
                target.pose.bones[bone.name].rotation_mode = "XYZ"
            index = 0
            
            for i in range(9):
                # Create a new F-Curve for each property
                path = index_dict[i]
                fcurve = action.fcurves.new(data_path=f'pose.bones["{bone.name}"].{path}', index=index)
                index += 1
                if index == 3:
                    index = 0
                # Set the keyframes
                start_frame = self.tmo.offsets[i + bidx * 9]["startFrame"]
                frame_count = self.tmo.offsets[i + bidx * 9]["frameCount"]
                #print(bidx)
                if path == "location":
                    for j in range(frame_count):
                        frame_dict = self.tmo.keyframes[start_frame + j]
                        frame, value = next(iter(frame_dict.items()))
                        
                        # Add keyframe points
                        fcurve.keyframe_points.insert(frame, value * 0.001)
                        fcurve.update()
                
                elif path == "rotation_euler":
                    for j in range(frame_count):
                        frame_dict = self.tmo.keyframes[start_frame + j]
                        frame, value = next(iter(frame_dict.items()))
                        
                        # Add keyframe points
                        fcurve.keyframe_points.insert(frame, float(value))
                        fcurve.update()
                


class importTMD2:
    def __init__(self, operator: Operator, filepath, import_settings: dict, tmd2file, dds_paths = {}):
        self.operator = operator
        self.filepath = filepath
        self.texture_path = ""
        for key, value in import_settings.items():
            setattr(self, key, value)
        
        self.tmd2: TMD2 = tmd2file
        self.dds_paths = dds_paths
    
    
    def read(self, context):
        collection = bpy.data.collections.new(f"{self.tmd2.name}")
        context.collection.children.link(collection)
        
        #Create an empty object to hold important flags
        empty = bpy.data.objects.new(f"#TMD PROPERTIES [{self.tmd2.name}]", None)
        empty.empty_display_size = 0.01
        empty.tmd2_props.flag1 = self.tmd2.flag1
        empty.tmd2_props.flag2 = self.tmd2.flag2
        empty.tmd2_props.flag3 = self.tmd2.animFlag
        empty.tmd2_props.after_image = self.tmd2.afterImageValue
        collection.objects.link(empty)
        
        #import and process materials and textures
        if self.texture_path:
            lds = importLDS(self.texture_path, True) 
            images_list = lds.images
        elif self.dds_paths:
            #load dds files using the same name in the tmd file
            images_list = []
            for i, texture in enumerate(self.tmd2.textures):
                
                #we'll try to find it in bpy.data.images first
                image = bpy.data.images.get(texture.name)
                if image:
                    images_list.append(image)
                
                elif texture.name in self.dds_paths:
                    #try to get the texture name from the dds_paths dict
                    tex_path = self.dds_paths[texture.name]
                    #load the dds file
                    image = bpy.data.images.load(tex_path)
                    image.pack()
                    image.use_fake_user = True
                    images_list.append(image)
                    
                else:
                    # texture not found, we'll create a placeholder image
                    tex_name = f"{self.tmd2.name}_{i}"
                    image = bpy.data.images.new(tex_name, width=texture.width, height=texture.height)
                    images_list.append(image)
        else:
            images_list = []
            for i, texture in enumerate(self.tmd2.textures):
                tex_name = f"{self.tmd2.name}_{i}.dds"
                #we'll try to find it in bpy.data.images first
                image = bpy.data.images.get(tex_name)
                if image:
                    images_list.append(image)
        
        materials_dict = {}
        for i, tm_mat in enumerate(self.tmd2.materials):
            tm_mat: TMD2Material
            
            if tm_mat.shaderID in shaders_dict:
                blender_mat = shaders_dict[tm_mat.shaderID](f"{self.tmd2.name}_{i}", tm_mat, images_list)
            else:
                blender_mat = shaders_dict["Default"](f"{self.tmd2.name}_{i}", tm_mat, images_list)
            bmat_props = blender_mat.tmd2_material
            
            bmat_props.material_hash = str(tm_mat.hash)
            bmat_props.shader_id = tm_mat.shaderID
            
            bmat_props.param_values.clear()
            for i in range(tm_mat.shaderParamsCount):
                param = bmat_props.param_values.add()
                param.value = tm_mat.shaderParams[i]
            
            bmat_props.textures.clear()
            for tmat_texture in tm_mat.textures:
                tmat_texture: TMD2MatTexture
                tm_texture: TMD2Texture = tmat_texture.texture
                t = bmat_props.textures.add()
                t.texture_hash = str(tm_texture.hash)
                t.value1 = tmat_texture.unk1
                t.value2 = tmat_texture.unk2
                
                if images_list:
                    t.image = images_list[tm_texture.index]
            
            bmat_props.unk = tm_mat.unk
            
            materials_dict[tm_mat] = blender_mat
        
        # Create a new mesh
        YUP_TO_ZUP = Matrix.Rotation(radians(90), 4, 'X')        
        
        bones_to_pose = {}
        
        if self.tmd2.modelFlags & 0x2000:
            #skeleton data
            armature = bpy.data.armatures.new(self.tmd2.name)
            armature_obj = bpy.data.objects.new(self.tmd2.name, armature)
            collection.objects.link(armature_obj)
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            armature_obj.data.display_type = 'STICK'
            
            for tmbone in self.tmd2.bones:
                tmbone: TMD2Bone
                
                if str(tmbone.hash) in hashes:
                    tmbone.name = hashes[str(tmbone.hash)]
                bbone = armature_obj.data.edit_bones.new(tmbone.name)
                
                matrix = Matrix(tmbone.matrix).transposed().inverted()
                matrix_up = YUP_TO_ZUP @ matrix
                
                bbone.matrix = matrix_up
                bbone.tail += Vector((0, 0, 0.01)) # Set the tail position to be 1 unit along the Z axis
                
                #set parent
                if tmbone.parentIndex != -1:
                    parent_bone = armature_obj.data.edit_bones[tmbone.parentIndex]
                    bbone.parent = parent_bone
                
                if tmbone.extra > -1:
                    bones_to_pose[bbone.name] =  tmbone.offset
                
                #set custom props
                bbone["hash"] = str(tmbone.hash)
                bbone["extra"] = tmbone.extra
                bbone["offset"] = tmbone.offset
                bbone["posed_loc"] = tmbone.posedLocation
                bbone["unk1"] = tmbone.unk1
                bbone["matrix"] = matrix
                bbone["matrix_up"] = matrix_up
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            #pose the armature
            if armature and bones_to_pose:
                #rotate bones
                for bname, rotation in bones_to_pose.items():
                    p = armature_obj.pose.bones[bname]
                    if not p.parent:
                        continue

                    axes = p.bone.matrix_local.to_3x3().transposed()
                    space = p.parent.matrix.to_3x3()
                    x, y, z = (space @ v for v in axes)

                    p.rotation_mode = 'QUATERNION'
                    p.rotation_quaternion = Quaternion(z, rotation[2]) @ Quaternion(y, rotation[1]) @ Quaternion(x, rotation[0])
        
        
        for tmd_model in self.tmd2.models:
            tmd_model: TMD2Model
            mesh = bpy.data.meshes.new(tmd_model.name)
            mesh_obj = bpy.data.objects.new(tmd_model.name, mesh)
            collection.objects.link(mesh_obj)
            
            #add mesh properties
            mesh_props = mesh_obj.tmd2_mesh
            if tmd_model.hashFlag:
                mesh_props.has_hash = True
                mesh_props.name_hash = str(tmd_model.hash)
            
            if tmd_model.nameFlag & 4:
                mesh_props.has_name = True
                mesh_props.name = tmd_model.name

            
            #create materials
            model_mats = {}
            for i, mesh_mat in enumerate(tmd_model.materials):
                mesh.materials.append(materials_dict[mesh_mat])
                model_mats[mesh_mat] = i
            

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
            
            uv0_list = []
            uv1_list = []
            uv2_list = []
            color1_list = []
            color2_list = []
            
            for tmd_mesh in tmd_model.meshes:
                tmd_mesh: TMD2Submesh
                
                mesh_vertices = self.tmd2.vertices[tmd_mesh.vertexIndices]
                
                bm_verts = []
                if self.tmd2.modelFlags & 0x8000:
                    bone_ids = np.concatenate([mesh_vertices["boneIDs"], mesh_vertices["boneIDs2"]], axis=1)
                    bone_weights = np.concatenate([mesh_vertices["boneWeights"], mesh_vertices["boneWeights2"]], axis=1)
                else:
                    bone_ids = mesh_vertices["boneIDs"]
                    bone_weights = mesh_vertices["boneWeights"]
                
                
                bm_verts = [bm.verts.new(vertex["position"]) for vertex in mesh_vertices]
                
                
                if self.tmd2.modelFlags & 0x400:
                    for i, v in enumerate(bm_verts):
                        for boneID, weight in zip(bone_ids[i], bone_weights[i]):
                            v[vgroup_layer][tmd_mesh.indexTable[boneID]] = weight
                
                bm.verts.ensure_lookup_table()

                for tri in tmd_mesh.triangles:
                    try:
                        face = bm.faces.new([bm_verts[i] for i in tri])
                        face.smooth = True
                        face.material_index = model_mats[tmd_mesh.material]
                    except ValueError:
                        # face exists already, skip
                        pass
                
                custom_normals.extend(self.tmd2.vertices[tmd_mesh.vertexIndices]["normal"][:, :3].tolist())
                
                if self.tmd2.modelFlags & 0x10:
                    # 1. UV0
                    uvs = mesh_vertices["uv"]
                    uv_flat = uvs[tmd_mesh.triangles]
                    uv_flat[..., 1] = 1.0 - uv_flat[..., 1]
                    uv0_list.extend(uv_flat.flatten())
                if self.tmd2.modelFlags & 0x20:
                    # 2. UV1
                    uvs = mesh_vertices["uv2"]
                    uv_flat = uvs[tmd_mesh.triangles]
                    uv_flat[..., 1] = 1.0 - uv_flat[..., 1]
                    uv1_list.extend(uv_flat.flatten())
                if self.tmd2.modelFlags & 0x40:
                    # 3. UV2
                    uvs = mesh_vertices["uv3"]
                    uv_flat = uvs[tmd_mesh.triangles]
                    uv_flat[..., 1] = 1.0 - uv_flat[..., 1]
                    uv2_list.extend(uv_flat.flatten())
                if self.tmd2.modelFlags & 0x80:
                    # 4. Color1
                    colors = mesh_vertices["color"]
                    color_flat = colors[tmd_mesh.triangles]
                    color1_list.extend(color_flat.flatten())
                if self.tmd2.modelFlags & 0x200:
                    # 5. Color2
                    colors = mesh_vertices["color2"]
                    color_flat = colors[tmd_mesh.triangles]
                    color2_list.extend(color_flat.flatten())
                    
                
            bm.to_mesh(mesh)
            bm.free()
            if self.tmd2.modelFlags & 0x4:
                mesh.normals_split_custom_set_from_vertices(custom_normals)
            
            if uv0_list:
                uv0_layer = mesh.uv_layers[0]
                uv0_layer.data.foreach_set("uv", uv0_list)
                
            if uv1_list:
                uv1_layer = mesh.uv_layers[1]
                uv1_layer.data.foreach_set("uv", uv1_list)
            if uv2_list:
                uv2_layer = mesh.uv_layers[2]
                uv2_layer.data.foreach_set("uv", uv2_list)
            if color1_list:
                col1_layer = mesh.vertex_colors[0]
                col1_layer.data.foreach_set("color", color1_list)
            if color2_list:
                col2_layer = mesh.vertex_colors[1]
                col2_layer.data.foreach_set("color", color2_list)
            mesh.update()
            #set active color
            mesh.color_attributes.render_color_index = 0
            mesh.color_attributes.active_color_index = 0
            
                
            mesh.transform(YUP_TO_ZUP)
            



class importTMD:
    def __init__(self, operator: Operator, filepath, import_settings: dict, tmdfile, dds_paths = {}):
        self.operator = operator
        self.filepath = filepath
        self.texture_path = ""
        for key, value in import_settings.items():
            setattr(self, key, value)
        
        self.tmd: TMD = tmdfile
        self.dds_paths = dds_paths
    
    
    def read(self, context):
        collection = bpy.data.collections.new(f"{self.tmd.name}")
        context.collection.children.link(collection)
        
        if self.dds_paths:
            #load dds files using the same name in the tmd file
            images_list = []
            for i, texture in enumerate(self.tmd.textures):
                
                #we'll try to find it in bpy.data.images first
                image = bpy.data.images.get(texture.name)
                if image:
                    images_list.append(image)
                
                elif texture.name in self.dds_paths:
                    #try to get the texture name from the dds_paths dict
                    tex_path = self.dds_paths[texture.name]
                    #load the dds file
                    image = bpy.data.images.load(tex_path)
                    image.pack()
                    image.use_fake_user = True
                    images_list.append(image)
                    
                else:
                    # texture not found, we'll create a placeholder image
                    tex_name = f"{self.tmd.name}_{i}"
                    image = bpy.data.images.new(tex_name, width=texture.width, height=texture.height)
                    images_list.append(image)
        else:
            images_list = []
            for i, texture in enumerate(self.tmd.textures):
                tex_name = f"{self.tmd.name}_{i}.dds"
                #we'll try to find it in bpy.data.images first
                image = bpy.data.images.get(tex_name)
                if image:
                    images_list.append(image)
        
        materials_dict = {}
        for i, tm_mat in enumerate(self.tmd.materials):
            tm_mat: TMDMaterial
            
            if tm_mat.shaderID in shaders_dict:
                blender_mat = shaders_dict[tm_mat.shaderID](f"{self.tmd.name}_{i}", tm_mat, images_list)
            else:
                blender_mat = shaders_dict["Default"](f"{self.tmd.name}_{i}", tm_mat, images_list)
            bmat_props = blender_mat.tmd2_material
            
            bmat_props.material_hash = str(tm_mat.hash)
            bmat_props.shader_id = tm_mat.shaderID
            
            bmat_props.param_values.clear()
            for i in range(tm_mat.shaderParamsCount):
                param = bmat_props.param_values.add()
                param.value = tm_mat.shaderParams[i]
            
            bmat_props.textures.clear()
            for tmat_texture in tm_mat.textures:
                tmat_texture: TMDMatTexture
                tm_texture: TMDTexture = tmat_texture.texture
                t = bmat_props.textures.add()
                t.texture_hash = str(tm_texture.hash)
                t.value1 = tmat_texture.unk1
                t.value2 = tmat_texture.unk2
                
                if images_list:
                    t.image = images_list[tm_texture.index]
            
            bmat_props.unk = tm_mat.unk
            
            materials_dict[tm_mat] = blender_mat
        
        # Create a new mesh
        YUP_TO_ZUP = Matrix.Rotation(radians(90), 4, 'X')        
        
        
        if self.tmd.modelFlags & 0x2000:
            #skeleton data
            armature = bpy.data.armatures.new(self.tmd.name)
            armature_obj = bpy.data.objects.new(self.tmd.name, armature)
            collection.objects.link(armature_obj)
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            armature_obj.data.display_type = 'STICK'
            
            for tmbone in self.tmd.bones:
                tmbone: TMDBone
                
                if str(tmbone.hash) in hashes:
                    tmbone.name = hashes[str(tmbone.hash)]
                bbone = armature_obj.data.edit_bones.new(tmbone.name)
                
                matrix = Matrix(tmbone.matrix).transposed().inverted()
                matrix_up = YUP_TO_ZUP @ matrix
                
                bbone.matrix = matrix_up
                bbone.tail += Vector((0, 0, 0.01)) # Set the tail position to be 1 unit along the Z axis
                
                #set parent
                if tmbone.parentIndex != -1:
                    parent_bone = armature_obj.data.edit_bones[tmbone.parentIndex]
                    bbone.parent = parent_bone
                
                #set custom props
                bbone["hash"] = str(tmbone.hash)
                bbone["extra"] = tmbone.extra
                bbone["offset"] = tmbone.offset
                bbone["posed_loc"] = tmbone.posedLocation
                bbone["unk1"] = tmbone.unk1
                bbone["matrix"] = matrix
                bbone["matrix_up"] = matrix_up
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
        
        for tmd_model in self.tmd.models:
            tmd_model: TMDModel
            mesh = bpy.data.meshes.new(tmd_model.name)
            mesh_obj = bpy.data.objects.new(tmd_model.name, mesh)
            collection.objects.link(mesh_obj)
            
            #add mesh properties
            mesh_props = mesh_obj.tmd2_mesh
            mesh_props.has_hash = tmd_model.hashFlag
            mesh_props.name_hash = str(tmd_model.hash)
            
            if tmd_model.nameFlag & 4:
                mesh_props.has_name = True
                mesh_props.name = tmd_model.name
            
            if tmd_model.nameFlag == 3:
                mesh_props.has_extra = True
                mesh_props.has_name = True
                mesh_props.name = tmd_model.name
                mesh_props.unk1 = tmd_model.unk1
                mesh_props.unk2 = tmd_model.unk2
                mesh_props.unk3 = tmd_model.unk3

            
            #create materials
            model_mats = {}
            for i, mesh_mat in enumerate(tmd_model.materials):
                mesh.materials.append(materials_dict[mesh_mat])
                model_mats[mesh_mat] = i
            
            
            #rename the mesh to include the name of the first texture in the first material
            if tmd_model.materials:
                first_mat = tmd_model.materials[0]
                if first_mat.textures:
                    first_texture = first_mat.textures[0].texture
                    if first_texture:
                        mesh_obj.name = f"{first_texture.name}_{tmd_model.name}"
            

            # Create a new bmesh object
            bm = bmesh.new()

            # Create vertices
            custom_normals = []
            vgroups_count = 0
            if self.tmd.modelFlags & 0x400:
                vgroup_layer = bm.verts.layers.deform.new("Weights")
                vgroups_count = 4
                
                for bone in armature.bones:
                    mesh_obj.vertex_groups.new(name = bone.name)
                
                #add arnature modifier
                armature_modifier = mesh_obj.modifiers.new(name = armature.name, type = 'ARMATURE')
                armature_modifier.object = armature_obj
                
                mesh_obj.parent = armature_obj
                
                if self.tmd.modelFlags & 0x8000:
                    vgroups_count += 4
            
            uv_layers = []
            if self.tmd.modelFlags & 0x10:
                uv0_layer = bm.loops.layers.uv.new(f"UVMap")
                uv_layers.append(uv0_layer)
            
            if self.tmd.modelFlags & 0x20:
                uv1_layer = bm.loops.layers.uv.new(f"UVMap1")
                uv_layers.append(uv1_layer)
            
            if self.tmd.modelFlags & 0x40:
                uv2_layer = bm.loops.layers.uv.new(f"UVMap2")
                uv_layers.append(uv2_layer)
            
            color_layers = []
            if self.tmd.modelFlags & 0x80:
                col1_layer = bm.loops.layers.color.new(f"Color")
                color_layers.append(col1_layer)
            
            if self.tmd.modelFlags & 0x200:
                col2_layer = bm.loops.layers.color.new(f"Color2")
                color_layers.append(col2_layer)
            
            for tmd_mesh in tmd_model.meshes:
                tmd_mesh: TMDSubmesh
                #vertex data
                bm_verts = []
                if self.tmd.modelFlags & 0x2000:
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
                else:
                    for vertex in tmd_mesh.vertices:
                        v = bm.verts.new(vertex.position)
                        v.normal = vertex.normal
                        bm_verts.append(v)
                        custom_normals.append(vertex.normal)

                bm.verts.ensure_lookup_table()
                
                #face data
                for tri in tmd_mesh.triangles:
                    try:
                        face = bm.faces.new([bm_verts[i] for i in tri])
                    except:
                        continue
                    face.smooth = True
                    face.material_index = model_mats[tmd_mesh.material]
                    
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
            if self.tmd.modelFlags & 0x4:
                mesh.normals_split_custom_set_from_vertices(custom_normals)
            
            #set active color
            mesh.color_attributes.render_color_index = 0
            mesh.color_attributes.active_color_index = 0
            
                
            mesh.transform(YUP_TO_ZUP)



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
    
    lds.images = images_list
    
    if return_tex:
        return lds

def menu_func_import(self, context):
    self.layout.operator(TMD2_IMPORTER_OT_IMPORT.bl_idname,
                        text='TamSoft TMD Importer (.tmd2, .tmd)',
                        icon='IMPORT')
