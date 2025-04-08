
bl_info = {
    "name" : "TMD2 Importer",
    "author" : "HydraBladeZ",
    "description" : "Importer/Exporter for Tamsoft TMD2 files",
    "blender" : (4, 2, 0),
    "version" : (1, 2, 0),
    "location" : "View3D",
    "warning" : "",
    "category" : "Import"
}

import bpy

from .importer import *

from .exporter import *

