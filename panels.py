import bpy
from bpy.types import PropertyGroup, Panel
from bpy.props import (
    FloatProperty,
    IntProperty,
    StringProperty,
    CollectionProperty,
    BoolProperty,
    PointerProperty
)


class TMD2ShaderParam(PropertyGroup):
    value: FloatProperty()
    


class TMD2MaterialTexture(PropertyGroup):
    texture_hash: StringProperty(default= "0")
    width: IntProperty()
    height: IntProperty()
    value1: IntProperty()
    value2: IntProperty()
    value3: IntProperty()

    image: bpy.props.PointerProperty(
        name="DDS Texture",
        type=bpy.types.Image,
        description="Select a DDS image from Blender"
    )

class TMD2MaterialProperties(PropertyGroup):
    material_hash: StringProperty(default= "0")
    shader_id: StringProperty()

    param_values: CollectionProperty(type=TMD2ShaderParam)
    param_index: bpy.props.IntProperty()

    textures: CollectionProperty(type=TMD2MaterialTexture)
    texture_index: bpy.props.IntProperty()  
    
    unk: IntProperty()
    
    def init_data(tm_mat):
        pass

class TMD2MeshProperties(PropertyGroup):
    has_name: BoolProperty(default = 0)
    has_hash: BoolProperty(default = 0)
    
    name: StringProperty()
    name_hash: StringProperty()
    unk: IntProperty()


class TMD2TextureProperties(PropertyGroup):
    texture_flags: IntProperty()

class TMD2MaterialClipboard:
    material_hash = ""
    shader_id = ""
    unk = 0
    param_values = []
    textures = []

    @classmethod
    def copy(cls, src):
        cls.material_hash = src.material_hash
        cls.shader_id = src.shader_id
        cls.unk = src.unk
        cls.param_values = [p.value for p in src.param_values]
        cls.textures = [{
            "texture_hash": t.texture_hash,
            "width": t.width,
            "height": t.height,
            "value1": t.value1,
            "value2": t.value2,
            "value3": t.value3,
            "image": t.image
        } for t in src.textures]

    @classmethod
    def paste(cls, dst):
        dst.material_hash = cls.material_hash
        dst.shader_id = cls.shader_id
        dst.unk = cls.unk

        dst.param_values.clear()
        for value in cls.param_values:
            param = dst.param_values.add()
            param.value = value

        dst.textures.clear()
        for t in cls.textures:
            tex = dst.textures.add()
            tex.texture_hash = t["texture_hash"]
            tex.width = t["width"]
            tex.height = t["height"]
            tex.value1 = t["value1"]
            tex.value2 = t["value2"]
            tex.value3 = t["value3"]
            tex.image = t["image"]


class TMD2ParamClipboard:
    param_values = []

    @classmethod
    def copy(cls, param_collection):
        cls.param_values = [param.value for param in param_collection]

    @classmethod
    def paste(cls, param_collection):
        param_collection.clear()
        for val in cls.param_values:
            new_param = param_collection.add()
            new_param.value = val


class TMD2_OT_CopyParams(bpy.types.Operator):
    bl_idname = "tmd2.copy_params"
    bl_label = "Copy All Shader Parameters"

    def execute(self, context):
        mat = context.material.tmd2_material
        if not mat.param_values:
            self.report({'WARNING'}, "No parameters to copy.")
            return {'CANCELLED'}

        TMD2ParamClipboard.copy(mat.param_values)
        self.report({'INFO'}, f"Copied {len(mat.param_values)} parameters.")
        return {'FINISHED'}


class TMD2_OT_PasteParams(bpy.types.Operator):
    bl_idname = "tmd2.paste_params"
    bl_label = "Paste All Shader Parameters"

    def execute(self, context):
        mat = context.material.tmd2_material
        if not TMD2ParamClipboard.param_values:
            self.report({'WARNING'}, "No copied parameters to paste.")
            return {'CANCELLED'}

        TMD2ParamClipboard.paste(mat.param_values)
        mat.param_index = min(mat.param_index, len(mat.param_values) - 1)
        self.report({'INFO'}, f"Pasted {len(mat.param_values)} parameters.")
        return {'FINISHED'}



class TMD2_OT_CopyMaterialData(bpy.types.Operator):
    bl_idname = "tmd2.copy_material_data"
    bl_label = "Copy TMD2 Material Data"

    def execute(self, context):
        mat = context.material
        if not mat or not hasattr(mat, "tmd2_material"):
            self.report({'WARNING'}, "No TMD2 material to copy.")
            return {'CANCELLED'}
        TMD2MaterialClipboard.copy(mat.tmd2_material)
        self.report({'INFO'}, "TMD2 material data copied.")
        return {'FINISHED'}


class TMD2_OT_PasteMaterialData(bpy.types.Operator):
    bl_idname = "tmd2.paste_material_data"
    bl_label = "Paste TMD2 Material Data"

    def execute(self, context):
        mat = context.material
        if not mat or not hasattr(mat, "tmd2_material"):
            self.report({'WARNING'}, "No TMD2 material to paste into.")
            return {'CANCELLED'}
        TMD2MaterialClipboard.paste(mat.tmd2_material)
        self.report({'INFO'}, "TMD2 material data pasted.")
        return {'FINISHED'}


class TMD2_UL_Textures(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "texture_hash", text="Texture Hash", emboss=False)
            row.prop_search(item, "image", bpy.data, "images", text="")
            row.operator("tmd2.open_dds", text="", icon='FILE_FOLDER')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='TEXTURE')
            
class TMD2_OT_TextureAdd(bpy.types.Operator):
    bl_idname = "tmd2.texture_add"
    bl_label = "Add Texture"

    def execute(self, context):
        mat = context.material.tmd2_material
        mat.textures.add()
        mat.texture_index = len(mat.textures) - 1
        return {'FINISHED'}

class TMD2_OT_TextureRemove(bpy.types.Operator):
    bl_idname = "tmd2.texture_remove"
    bl_label = "Remove Texture"

    def execute(self, context):
        mat = context.material.tmd2_material
        if mat.textures:
            mat.textures.remove(mat.texture_index)
            mat.texture_index = max(0, mat.texture_index - 1)
        return {'FINISHED'}

class TMD2_OT_TextureMove(bpy.types.Operator):
    bl_idname = "tmd2.texture_move"
    bl_label = "Move Texture"
    direction: bpy.props.EnumProperty(
        items=[('UP', 'Up', ""), ('DOWN', 'Down', "")],
        name="Direction"
    )

    def execute(self, context):
        mat = context.material.tmd2_material
        idx = mat.texture_index
        new_idx = idx - 1 if self.direction == 'UP' else idx + 1
        if 0 <= new_idx < len(mat.textures):
            mat.textures.move(idx, new_idx)
            mat.texture_index = new_idx
        return {'FINISHED'}


class TMD2_UL_Params(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text = f"Param {index}")
            layout.prop(item, "value", text=f"Value")
        elif self.layout_type == 'GRID':
            layout.label(text=str(index))

class TMD2_OT_ParamAdd(bpy.types.Operator):
    bl_idname = "tmd2.param_add"
    bl_label = "Add Param"

    def execute(self, context):
        mat = context.material.tmd2_material
        mat.param_values.add()
        mat.param_index = len(mat.param_values) - 1
        return {'FINISHED'}

class TMD2_OT_ParamRemove(bpy.types.Operator):
    bl_idname = "tmd2.param_remove"
    bl_label = "Remove Param"

    def execute(self, context):
        mat = context.material.tmd2_material
        if mat.param_values:
            mat.param_values.remove(mat.param_index)
            mat.param_index = max(0, mat.param_index - 1)
        return {'FINISHED'}

class TMD2_OT_ParamMove(bpy.types.Operator):
    bl_idname = "tmd2.param_move"
    bl_label = "Move Param"
    direction: bpy.props.EnumProperty(
        items=[('UP', 'Up', ""), ('DOWN', 'Down', "")],
        name="Direction"
    )

    def execute(self, context):
        mat = context.material.tmd2_material
        idx = mat.param_index
        new_idx = idx - 1 if self.direction == 'UP' else idx + 1
        if 0 <= new_idx < len(mat.param_values):
            mat.param_values.move(idx, new_idx)
            mat.param_index = new_idx
        return {'FINISHED'}


class TMD2_PT_MaterialPanel(Panel):
    bl_idname = 'MATERIAL_PT_tmd2_material'
    bl_label = 'TMD2 Material Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    @classmethod
    def poll(cls, context):
        return context.material is not None

    def draw(self, context):
        layout = self.layout
        mat = context.material
        tmd2 = mat.tmd2_material
        
        row = layout.row(align=True)
        row.operator("tmd2.copy_material_data", icon="COPYDOWN", text="Copy TMD2")
        row.operator("tmd2.paste_material_data", icon="PASTEDOWN", text="Paste TMD2")
        
        row = layout.row(align=True)
        row.operator("tmd2.copy_params", icon="COPYDOWN", text="Copy All Params")
        row.operator("tmd2.paste_params", icon="PASTEDOWN", text="Paste All Params")

        row = layout.row()
        col1 = row.column()
        col2 = row.column()
        
        box1 = col1.box()
        row = box1.row()
        row.label(text="Material Hash:")
        row = box1.row()
        row.prop(tmd2, "material_hash", text = "")
        row = box1.row()
        row = box1.row() #this only done for spacing
        row.label(text="Shader ID:")
        row = box1.row()
        row.prop(tmd2, "shader_id", text = "")
        row = box1.row()
        row = box1.row() #this only done for spacing
        row.prop(tmd2, "unk", text = "Unknown")

        box = col2.box()
        box.label(text="Shader Parameters:")
        
        row = box.row()
        row.template_list("TMD2_UL_Params", "", tmd2, "param_values", tmd2, "param_index")
        
        col = row.column(align=True)
        col.operator("tmd2.param_add", icon="ADD", text="")
        col.operator("tmd2.param_remove", icon="REMOVE", text="")
        col.separator()
        col.operator("tmd2.param_move", icon="TRIA_UP", text="").direction = 'UP'
        col.operator("tmd2.param_move", icon="TRIA_DOWN", text="").direction = 'DOWN'


        box2 = layout.box()
        box2.label(text="Textures:")

        row = box2.row()
        if tmd2.textures:
            row.template_ID_preview(tmd2.textures[tmd2.texture_index], 'image', hide_buttons=True)
        row.template_list("TMD2_UL_Textures", "", tmd2, "textures", tmd2, "texture_index")

        col = row.column(align=True)
        col.operator("tmd2.texture_add", icon="ADD", text="")
        col.operator("tmd2.texture_remove", icon="REMOVE", text="")
        col.separator()
        col.operator("tmd2.texture_move", icon="TRIA_UP", text="").direction = 'UP'
        col.operator("tmd2.texture_move", icon="TRIA_DOWN", text="").direction = 'DOWN'
        
        row = box2.row()
        if tmd2.textures:
            row.prop(tmd2.textures[tmd2.texture_index], "value1",text = "Unknown 1")
            row.prop(tmd2.textures[tmd2.texture_index], "value2",text = "Unknown 1")


class TMD2_PT_MeshPanel(Panel):
    bl_idname = 'OBJECT_PT_tmd2_mesh'
    bl_label = 'TMD2 Mesh Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        obj = context.object
        tmd2mesh = obj.tmd2_mesh
        
        row = layout.row()
        row.prop(tmd2mesh, "has_name", text = "Has Name")
        row.prop(tmd2mesh, "has_hash", text = "Has Hash")
        
        row = layout.row()
        row.prop(tmd2mesh, "name", text = "Name")
        row.prop(tmd2mesh, "name_hash", text = "Name Hash")
        row.prop(tmd2mesh, "unk", text = "Unknown")
        
class TMD2_PT_TexturePanel(Panel):
    bl_idname = 'OBJECT_PT_tmd2_texture'
    bl_label = 'TMD2 Texture Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        return context.object and context.object.name.startswith("TMD2 TEXTURE PROPERTIES")

    def draw(self, context):
        layout = self.layout
        obj = context.object
        tmd2tex = obj.tmd2_texture
        
        row = layout.row()
        row.prop(tmd2tex, "texture_flags")



class TMD2_Texture_OT_OpenDDS(bpy.types.Operator):
    bl_idname = "tmd2.open_dds"
    bl_label = "Open DDS Texture"
    bl_options = {'REGISTER', 'UNDO'}

    # Filepath property for the file browser
    filepath: StringProperty(
        name="DDS File Path",
        description="Filepath used for opening a DDS image",
        subtype='FILE_PATH'
    )

    # Filter to show only .dds files
    filter_glob: StringProperty(
        default="*.dds",
        options={'HIDDEN'}
    )

    def invoke(self, context, event):
        # Open the file selector
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        mat = context.material.tmd2_material
        if not mat:
            self.report({'ERROR'}, "No TMD2 material found on active context")
            return {'CANCELLED'}

        # Load the selected DDS image
        try:
            img = bpy.data.images.load(self.filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load image: {e}")
            return {'CANCELLED'}

        # Assign or append the loaded image to the material's texture slots
        # Adjust this based on how textures are stored in tmd2_material
        if hasattr(mat, 'textures') and mat.textures:
            mat.textures[mat.texture_index].image = img
        else:
            # Fallback: create a new texture slot and assign
            tex_slot = mat.texture_slots.add()
            tex_slot.texture = bpy.data.textures.new(name="DDS_Texture", type='IMAGE')
            tex_slot.texture.image = img

        return {'FINISHED'}
            


material_properties = [
    TMD2ShaderParam,
    TMD2MaterialTexture,
    TMD2MaterialProperties,
    TMD2MeshProperties,
    TMD2TextureProperties,
    TMD2_UL_Textures,
    TMD2_OT_TextureAdd,
    TMD2_OT_TextureRemove,
    TMD2_OT_TextureMove,
    TMD2_UL_Params,
    TMD2_OT_ParamAdd,
    TMD2_OT_ParamRemove,
    TMD2_OT_ParamMove,
    TMD2_OT_CopyMaterialData,
    TMD2_OT_PasteMaterialData,
    TMD2_OT_CopyParams,
    TMD2_OT_PasteParams,
    TMD2_Texture_OT_OpenDDS
    
]

material_panels = [
    TMD2_PT_MaterialPanel,
    TMD2_PT_MeshPanel,
    TMD2_PT_TexturePanel
]