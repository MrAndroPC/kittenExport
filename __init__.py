bl_info = {
    "name": "Kitten export",
    "blender": (4, 50, 0),
    "category": "Import-Export",
}

import bpy
from . import properties
from . import operators
from . import ui

classes = (
    properties.ThrusterProperties,
    properties.EngineProperties,
    operators.OBJECT_OT_add_thruster,
    operators.OBJECT_OT_add_engine,
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
