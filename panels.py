import bpy
from bpy.types import PropertyGroup, Panel
from bpy.props import (
    FloatProperty,
    IntProperty,
    StringProperty,
    CollectionProperty,
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
    def update_count(self, context):
        if self.param_count > len(self.param_values):
            for _ in range(self.param_count - len(self.param_values)):
                self.param_values.add()
        elif self.param_count < len(self.param_values):
            for _ in range(len(self.param_values) - self.param_count):
                self.param_values.remove(len(self.param_values) - 1)

    material_hash: StringProperty(default= "0")
    shader_id: StringProperty()

    param_count: IntProperty(update=update_count)
    param_values: CollectionProperty(type=TMD2ShaderParam)
    param_index: bpy.props.IntProperty()

    textures: CollectionProperty(type=TMD2MaterialTexture)
    texture_index: bpy.props.IntProperty()  
    
    def init_data():
        pass
    

class TMD2_UL_Textures(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "texture_hash", text="Texture Hash", emboss=False)
            row.prop_search(item, "image", bpy.data, "images", text="")
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

        layout.prop(tmd2, "material_hash", text = "Material Hash")
        layout.prop(tmd2, "shader_id", text = "Shader ID")
        layout.prop(tmd2, "param_count", text = "Param Count")

        box = layout.box()
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
        row.template_ID_preview(tmd2.textures[tmd2.texture_index], 'image', hide_buttons=True)
        row.template_list("TMD2_UL_Textures", "", tmd2, "textures", tmd2, "texture_index")

        col = row.column(align=True)
        col.operator("tmd2.texture_add", icon="ADD", text="")
        col.operator("tmd2.texture_remove", icon="REMOVE", text="")
        col.separator()
        col.operator("tmd2.texture_move", icon="TRIA_UP", text="").direction = 'UP'
        col.operator("tmd2.texture_move", icon="TRIA_DOWN", text="").direction = 'DOWN'


material_properties = [
    TMD2ShaderParam,
    TMD2MaterialTexture,
    TMD2MaterialProperties,
    TMD2_UL_Textures,
    TMD2_OT_TextureAdd,
    TMD2_OT_TextureRemove,
    TMD2_OT_TextureMove,
    TMD2_UL_Params,
    TMD2_OT_ParamAdd,
    TMD2_OT_ParamRemove,
    TMD2_OT_ParamMove,
]

material_panels = [
    TMD2_PT_MaterialPanel
]