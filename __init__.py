"""
    KittenExport plugin for blender
    Copyright (C) 2025  Marcus Zuber

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import bpy
from . import properties
from . import operators
from . import ui

bl_info = {
    "name": "Kitten export",
    "blender": (4, 50, 0),
    "category": "Import-Export",
}

classes = (
    properties.ThrusterProperties,
    properties.EngineProperties,
    operators.OBJECT_OT_add_thruster,
    operators.OBJECT_OT_add_engine,
    operators.OBJECT_OT_place_at_selection,
    ui.OBJECT_PT_thruster_panel,
    ui.OBJECT_PT_engine_panel,
    operators.OBJECT_OT_export_ksa_metadata,
    operators.OBJECT_OT_export_glb_with_meta,
    operators.OBJECT_OT_export_thrusters_OLD,
    operators.OBJECT_OT_bake_thruster_meta,
    operators.OBJECT_OT_export_engines,
    operators.OBJECT_OT_bake_engine_meta,
    ui.VIEW3D_MT_ksa_add,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass

    try:
        bpy.types.Object.thruster_props = bpy.props.PointerProperty(type=properties.ThrusterProperties)
        bpy.types.Object.engine_props = bpy.props.PointerProperty(type=properties.EngineProperties)
    except Exception:
        pass

    try:
        bpy.types.VIEW3D_MT_add.append(ui.menu_func)
        bpy.types.VIEW3D_MT_mesh_add.append(ui.menu_func)
        bpy.types.TOPBAR_MT_file_export.append(ui.export_menu_func)
    except Exception:
        pass

    print("Kitten export addon registered")

def unregister():
    try:
        bpy.types.VIEW3D_MT_add.remove(ui.menu_func)
        bpy.types.TOPBAR_MT_file_export.remove(ui.export_menu_func)
    except Exception:
        pass

    try:
        del bpy.types.Object.thruster_props
        del bpy.types.Object.engine_props
    except Exception:
        pass

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

    print("Kitten export addon unregistered")

if __name__ == "__main__":
    register()
