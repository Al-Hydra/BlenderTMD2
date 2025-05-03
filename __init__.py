
bl_info = {
    "name" : "TMD2 Importer",
    "author" : "HydraBladeZ",
    "description" : "Importer/Exporter for Tamsoft TMD2 files",
    "blender" : (4, 2, 0),
    "version" : (1, 0, 0),
    "location" : "View3D",
    "warning" : "",
    "category" : "Import"
}

import bpy

from .importer import *

from .exporter import *
from .panels import material_properties, material_panels, TMD2MaterialProperties, TMD2MeshProperties, TMD2TextureProperties
from bpy.props import PointerProperty

classes = [
    *material_properties,
    *material_panels
    
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Material.tmd2_material = PointerProperty(type=TMD2MaterialProperties)
    bpy.types.Object.tmd2_mesh = PointerProperty(type=TMD2MeshProperties)
    bpy.types.Object.tmd2_texture = PointerProperty(type=TMD2TextureProperties)
    
    bpy.utils.register_class(TMD2_IMPORTER_OT_IMPORT)
    bpy.utils.register_class(TMD2_EXPORTER_OT_EXPORT)
    bpy.utils.register_class(DropTMD2)
    bpy.utils.register_class(TMD2_FH_import)
    bpy.utils.register_class(DropTMD)
    bpy.utils.register_class(TMD_FH_import)
    bpy.utils.register_class(DropLDS)
    bpy.utils.register_class(LDS_FH_import)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Material.tmd2_material
    del bpy.types.Object.tmd2_mesh
    del bpy.types.Object.tmd2_texture
    
    bpy.utils.unregister_class(TMD2_IMPORTER_OT_IMPORT)
    bpy.utils.unregister_class(TMD2_EXPORTER_OT_EXPORT)
    bpy.utils.unregister_class(DropTMD2)
    bpy.utils.unregister_class(TMD2_FH_import)
    bpy.utils.unregister_class(DropTMD)
    bpy.utils.unregister_class(TMD_FH_import)
    bpy.utils.unregister_class(DropLDS)
    bpy.utils.unregister_class(LDS_FH_import)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)