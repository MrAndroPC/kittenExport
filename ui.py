import bpy

class OBJECT_PT_thruster_panel(bpy.types.Panel):
    bl_label = "Thruster Properties"
    bl_idname = "OBJECT_PT_thruster_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        obj = getattr(context, 'object', None)
        if obj is None: return False
        return obj.get('_is_thruster') is not None or obj.get('_thruster_meta') is not None or obj.name.startswith('Thruster')

    def draw(self, context):
        layout = self.layout
        obj = context.object
        props = obj.thruster_props

        col = layout.column()
        col.prop(props, "fx_location")
        col.prop(props, "thrust_n")
        col.prop(props, "specific_impulse_seconds")
        col.prop(props, "minimum_pulse_time_seconds")
        col.prop(props, "volumetric_exhaust_id")
        col.prop(props, "sound_event_on")

        col.separator()
        box = col.box()
        box.label(text="Translation Control Map:")
        translation_labels = ["Forward", "Backward", "Left", "Right", "Up", "Down"]
        for i, label in enumerate(translation_labels):
            box.prop(props, "control_map_translation", index=i, text=label)

        col.separator()
        box = col.box()
        box.label(text="Rotation Control Map:")
        rotation_labels = ["Pitch Up", "Pitch Down", "Roll Left", "Roll Right", "Yaw Left", "Yaw Right"]
        for i, label in enumerate(rotation_labels):
            box.prop(props, "control_map_rotation", index=i, text=label)

        col.separator()
        col.prop(props, "exportable")

class OBJECT_PT_engine_panel(bpy.types.Panel):
    bl_label = "Engine Properties"
    bl_idname = "OBJECT_PT_engine_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        obj = getattr(context, 'object', None)
        if obj is None: return False
        return obj.get('_is_engine') is not None or obj.get('_engine_meta') is not None or obj.name.startswith('Engine')

    def draw(self, context):
        layout = self.layout
        obj = context.object
        props = obj.engine_props

        col = layout.column()
        col.prop(props, "thrust_kn")
        col.prop(props, "specific_impulse_seconds")
        col.prop(props, "minimum_throttle")
        col.prop(props, "volumetric_exhaust_id")
        col.prop(props, "sound_event_action_on")
        col.prop(props, "exportable")

class VIEW3D_MT_ksa_add(bpy.types.Menu):
    bl_label = "KSA"
    bl_idname = "VIEW3D_MT_ksa_add"

    def draw(self, context):
        layout = self.layout
        
        # Object Mode Additions
        layout.operator("object.add_thruster", text="Thruster", icon='EMPTY_SINGLE_ARROW')
        layout.operator("object.add_engine", text="Engine", icon='CONE')
        
        layout.separator()
        
        # Edit Mode Additions (Only enabled if in Edit Mode)
        op_t = layout.operator("object.place_at_selection", text="Thruster on Selection", icon='SNAP_FACE')
        op_t.type = 'THRUSTER'
        
        op_e = layout.operator("object.place_at_selection", text="Engine on Selection", icon='SNAP_FACE')
        op_e.type = 'ENGINE'

def menu_func(self, context):
    self.layout.menu(VIEW3D_MT_ksa_add.bl_idname)

def export_menu_func(self, context):
    self.layout.operator("export_scene.ksa_metadata", text="KSA Metadata (.xml)")
