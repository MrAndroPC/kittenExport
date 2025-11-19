import bpy
import bmesh
import math
import mathutils
import os
import xml.etree.ElementTree as ET
from .utils import (
    _safe_vector_to_list, _thruster_dict_to_xml_element, _engine_dict_to_xml_element,
    thrusters_list_to_xml_str, engines_list_to_xml_str, meta_dict_to_xml_str,
    parse_meta_string
)

class OBJECT_OT_place_at_selection(bpy.types.Operator):
    bl_idname = "object.place_at_selection"
    bl_label = "Place KSA Object at Selection"
    bl_description = "Place a Thruster or Engine at the center of selected vertices, aligned to their normal"
    bl_options = {'REGISTER', 'UNDO'}

    type: bpy.props.EnumProperty(
        items=[
            ('THRUSTER', "Thruster", "Add a Thruster"),
            ('ENGINE', "Engine", "Add an Engine"),
        ],
        name="Type",
        default='THRUSTER',
    )

    flip_normal: bpy.props.BoolProperty(
        name="Flip Direction",
        description="Invert the calculated normal direction",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        # Only allow in Edit Mode with an active mesh object
        return (context.mode == 'EDIT_MESH' and 
                context.object and 
                context.object.type == 'MESH')

    def execute(self, context):
        obj = context.object
        mw = obj.matrix_world
        mesh = obj.data
        
        # 1. Get Geometry from Edit Mode
        bm = bmesh.from_edit_mesh(mesh)
        selected_verts = [v for v in bm.verts if v.select]

        # 2. Validation
        if len(selected_verts) < 3:
            self.report({'ERROR'}, "Select at least 3 vertices to define a plane/ring.")
            return {'CANCELLED'}

        # 3. Calculate Center and Normal
        world_coords = [mw @ v.co for v in selected_verts]
        
        # Center is the average position
        center = sum(world_coords, mathutils.Vector()) / len(world_coords)
        
        # Calculate normal using Blender's internal robust method
        normal = mathutils.geometry.normal(world_coords)
        
        # Fallback for degenerate geometry (collinear points)
        if normal.length_squared < 1e-6:
            self.report({'ERROR'}, "Selection is collinear or degenerate; cannot calculate normal.")
            return {'CANCELLED'}
            
        # Check planarity (Standard Deviation of distance to plane)
        # Plane equation: normal . (p - center) = 0
        distances = [abs(normal.dot(p - center)) for p in world_coords]
        avg_deviation = sum(distances) / len(distances)
        
        if avg_deviation > 0.1: # Threshold in meters (adjust as needed)
            self.report({'WARNING'}, f"Selection is not planar (Avg Dev: {avg_deviation:.3f}m). Result might be inaccurate.")

        normal = -normal

        # 4. Switch to Object Mode to add the new object
        bpy.ops.object.mode_set(mode='OBJECT')

        # 5. Add the specific object type
        if self.type == 'THRUSTER':
            bpy.ops.object.add_thruster()
        else:
            bpy.ops.object.add_engine()
            
        new_obj = context.active_object
        
        # 6. Apply Transform
        new_obj.location = center
        
        # We want the object's local X axis (Exhaust) to point along the Normal.
        # 'Z' is the "Up" axis which we don't care about as much, but we need it stable.
        
        # Method: Construct a rotation matrix directly from the normal
        # If the normal is (0,0,1), we want local X to be (0,0,1).
        
        # Create a rotation that aligns the TRACK axis (X) to the vector (normal)
        rot_quat = normal.to_track_quat('X', 'Z')
        
        # If the previous code resulted in it lying flat, it means the object's 
        # internal geometry might be oriented along Z or Y, but we are aligning X.
        # However, assuming your Thruster empty is an arrow pointing +X or +Z:
        
        # FIX: If the object looks "aligned with the plane", it usually means 
        # we aligned the wrong local axis to the normal.
        
        # Let's try aligning the object's Z axis to the normal instead, 
        # or forcing the alignment more explicitly.
        
        # If your thruster visual (Arrow) points up (Z), use 'Z'.
        # If your thruster visual (Arrow) points forward (X), use 'X'.
        
        # Assuming your Empty displays as an Arrow pointing +Z (Blender default):
        # transform so Local Z matches Normal.
        
        # Re-evaluating based on your comment: 
        # "Aligned with vertices plane" means it is 90 degrees off.
        # If you used 'X' before and it laid flat, maybe the visual arrow is Z?
        
        # Let's align the Z-axis to the normal (Standard Blender "Up").
        rot_quat = normal.to_track_quat('Z', 'X')
        
        new_obj.rotation_euler = rot_quat.to_euler()

        self.report({'INFO'}, f"Placed {self.type} at selection center.")
        return {'FINISHED'}
# --- Existing Operators Below (Unchanged) ---

class OBJECT_OT_export_ksa_metadata(bpy.types.Operator):
    bl_idname = "export_scene.ksa_metadata"
    bl_label = "Export KSA Metadata"
    bl_description = "Export all thrusters and engines to KSA XML format"
    bl_options = {'REGISTER'}
    
    filepath: bpy.props.StringProperty(
        name="Filepath",
        description="Where to write the XML export",
        default="",
        subtype='FILE_PATH',
    )
    
    filter_glob: bpy.props.StringProperty(
        default="*.xml",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        try:
            self.filepath = "ksa_metadata.xml"
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            return self.execute(context)

    def execute(self, context):
        scene = getattr(context, 'scene', None)
        if scene is None:
            self.report({'ERROR'}, "No scene found")
            return {'CANCELLED'}

        thrusters = []
        for obj in scene.objects:
            if obj.get('_is_thruster') is None and not obj.name.startswith('Thruster'):
                continue
            tp = getattr(obj, 'thruster_props', None)
            if tp is None or not getattr(tp, 'exportable', False):
                continue

            entry = {
                'name': obj.name,
                'location': list(obj.location) if obj.location is not None else None,
                'rotation': list(obj.rotation_euler) if obj.rotation_euler is not None else None,
                'fx_location': _safe_vector_to_list(tp.fx_location),
                'thrust_n': tp.thrust_n,
                'specific_impulse_seconds': tp.specific_impulse_seconds,
                'minimum_pulse_time_seconds': tp.minimum_pulse_time_seconds,
                'volumetric_exhaust_id': tp.volumetric_exhaust_id,
                'sound_event_on': tp.sound_event_on,
                'control_map_translation': _safe_vector_to_list(tp.control_map_translation),
                'control_map_rotation': _safe_vector_to_list(tp.control_map_rotation),
                'exportable': tp.exportable,
            }
            thrusters.append(entry)

        engines = []
        for obj in scene.objects:
            if obj.get('_is_engine') is None and not obj.name.startswith('Engine'):
                continue
            ep = getattr(obj, 'engine_props', None)
            if ep is None or not getattr(ep, 'exportable', False):
                continue

            entry = {
                'name': obj.name,
                'location': list(obj.location) if obj.location is not None else None,
                'rotation': list(obj.rotation_euler) if obj.rotation_euler is not None else None,
                'thrust_kn': ep.thrust_kn,
                'specific_impulse_seconds': ep.specific_impulse_seconds,
                'minimum_throttle': ep.minimum_throttle,
                'volumetric_exhaust_id': ep.volumetric_exhaust_id,
                'sound_event_action_on': ep.sound_event_action_on,
                'exportable': ep.exportable,
            }
            engines.append(entry)

        root = ET.Element('KSAMetadata')
        for thruster_data in thrusters:
            _thruster_dict_to_xml_element(root, thruster_data)
        for engine_data in engines:
            _engine_dict_to_xml_element(root, engine_data)

        xml_text = ET.tostring(root, encoding='utf-8').decode('utf-8')

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write('\n')
                f.write(xml_text)
            self.report({'INFO'}, f"Exported {len(thrusters)} thrusters and {len(engines)} engines to {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

class OBJECT_OT_add_thruster(bpy.types.Operator):
    bl_idname = "object.add_thruster"
    bl_label = "Add Thruster"
    bl_description = "Create a thruster object (Empty with metadata)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.data.objects.new("Thruster", None)
        try:
            context.collection.objects.link(obj)
        except Exception:
            pass
        try:
            obj.empty_display_type = 'SINGLE_ARROW'
            obj.empty_display_size = 0.3
            obj.rotation_euler = (0, -math.pi / 2, 0)
        except Exception:
            pass
        try:
            obj['_is_thruster'] = True
            obj['_no_export'] = True
        except Exception:
            pass
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        except Exception:
            pass
        return {'FINISHED'}

class OBJECT_OT_add_engine(bpy.types.Operator):
    bl_idname = "object.add_engine"
    bl_label = "Add Engine"
    bl_description = "Create an engine object (Empty with metadata)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.data.objects.new("Engine", None)
        try:
            context.collection.objects.link(obj)
        except Exception:
            pass
        try:
            obj.empty_display_type = 'CONE'
            obj.empty_display_size = 0.5
            obj.rotation_euler = (0, -math.pi / 2, 0)
        except Exception:
            pass
        try:
            obj['_is_engine'] = True
            obj['_no_export'] = True
        except Exception:
            pass
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        except Exception:
            pass
        return {'FINISHED'}

class OBJECT_OT_export_thrusters_OLD(bpy.types.Operator):
    bl_idname = "object.export_thrusters_old"
    bl_label = "Export Selected Thrusters (Legacy)"
    bl_description = "Collect Thruster parameters from selected objects and export them"
    
    filepath: bpy.props.StringProperty(
        name="Filepath",
        description="Where to write the JSON export. If empty, print to console.",
        default="",
    )

    def invoke(self, context, event):
        try:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            return self.execute(context)

    def execute(self, context):
        data = []
        for obj in getattr(context, 'selected_objects', []):
            kp = getattr(obj, 'thruster_props', None)
            if kp is None or not getattr(kp, 'exportable', False):
                continue
            entry = {
                'name': getattr(obj, 'name', ''),
                'location': list(obj.location) if obj.location is not None else None,
                'rotation': list(obj.rotation_euler) if obj.rotation_euler is not None else None,
                'fx_location': _safe_vector_to_list(kp.fx_location),
                'thrust_n': kp.thrust_n,
                'specific_impulse_seconds': kp.specific_impulse_seconds,
                'minimum_pulse_time_seconds': kp.minimum_pulse_time_seconds,
                'volumetric_exhaust_id': kp.volumetric_exhaust_id,
                'sound_event_on': kp.sound_event_on,
                'control_map_translation': _safe_vector_to_list(kp.control_map_translation),
                'control_map_rotation': _safe_vector_to_list(kp.control_map_rotation),
                'exportable': kp.exportable,
            }
            data.append(entry)
        xml_text = thrusters_list_to_xml_str(data)
        if getattr(self, 'filepath', ''):
            try:
                path = self.filepath
                if path.lower().endswith('.json'):
                    path = path[:-5] + '.xml'
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(xml_text)
                self.report({'INFO'}, f"Exported {len(data)} items to {path}")
            except Exception as e:
                self.report({'ERROR'}, str(e))
                return {'CANCELLED'}
        else:
            print("Thruster export (XML):\n", xml_text)
            self.report({'INFO'}, f"Prepared export for {len(data)} objects (printed to console)")
        return {'FINISHED'}

class OBJECT_OT_bake_thruster_meta(bpy.types.Operator):
    bl_idname = "object.bake_thruster_meta"
    bl_label = "Bake Thruster Metadata"
    bl_description = "Write thruster properties into the object's custom property for external exporters"

    def execute(self, context):
        count = 0
        for obj in getattr(context, 'selected_objects', []):
            kp = getattr(obj, 'thruster_props', None)
            if kp is None: continue
            try:
                meta = {
                    'name': obj.name,
                    'thrust_n': kp.thrust_n,
                    'specific_impulse_seconds': kp.specific_impulse_seconds,
                    'minimum_pulse_time_seconds': kp.minimum_pulse_time_seconds,
                    'volumetric_exhaust_id': kp.volumetric_exhaust_id,
                    'sound_event_on': kp.sound_event_on,
                    'control_map_translation': _safe_vector_to_list(kp.control_map_translation),
                    'control_map_rotation': _safe_vector_to_list(kp.control_map_rotation),
                    'exportable': kp.exportable,
                    'location': list(obj.location) if obj.location is not None else None,
                }
                obj['_thruster_meta'] = meta_dict_to_xml_str(meta)
                obj['_no_export'] = True
                count += 1
            except Exception:
                pass
        self.report({'INFO'}, f"Baked metadata for {count} objects")
        return {'FINISHED'}

class OBJECT_OT_export_engines(bpy.types.Operator):
    bl_idname = "object.export_engines"
    bl_label = "Export Selected Engines"
    bl_description = "Collect Engine parameters from selected objects and export them as XML"
    
    filepath: bpy.props.StringProperty(
        name="Filepath",
        description="Where to write the XML export. If empty, print to console.",
        default="",
    )

    def invoke(self, context, event):
        try:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            return self.execute(context)

    def execute(self, context):
        data = []
        for obj in getattr(context, 'selected_objects', []):
            ep = getattr(obj, 'engine_props', None)
            if ep is None or not getattr(ep, 'exportable', False):
                continue
            entry = {
                'name': getattr(obj, 'name', ''),
                'location': list(obj.location) if obj.location is not None else None,
                'rotation': list(obj.rotation_euler) if obj.rotation_euler is not None else None,
                'thrust_kn': ep.thrust_kn,
                'specific_impulse_seconds': ep.specific_impulse_seconds,
                'minimum_throttle': ep.minimum_throttle,
                'volumetric_exhaust_id': ep.volumetric_exhaust_id,
                'sound_event_action_on': ep.sound_event_action_on,
                'exportable': ep.exportable,
            }
            data.append(entry)
        xml_text = engines_list_to_xml_str(data)
        if getattr(self, 'filepath', ''):
            try:
                path = self.filepath
                if path.lower().endswith('.json'):
                    path = path[:-5] + '.xml'
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(xml_text)
                self.report({'INFO'}, f"Exported {len(data)} engine items to {path}")
            except Exception as e:
                self.report({'ERROR'}, str(e))
                return {'CANCELLED'}
        else:
            print("Engine export (XML):\n", xml_text)
            self.report({'INFO'}, f"Prepared export for {len(data)} engine objects (printed to console)")
        return {'FINISHED'}

class OBJECT_OT_bake_engine_meta(bpy.types.Operator):
    bl_idname = "object.bake_engine_meta"
    bl_label = "Bake Engine Metadata"
    bl_description = "Write engine properties into the object's custom property for external exporters"

    def execute(self, context):
        count = 0
        for obj in getattr(context, 'selected_objects', []):
            ep = getattr(obj, 'engine_props', None)
            if ep is None: continue
            try:
                meta = {
                    'name': obj.name,
                    'thrust_kn': ep.thrust_kn,
                    'specific_impulse_seconds': ep.specific_impulse_seconds,
                    'minimum_throttle': ep.minimum_throttle,
                    'volumetric_exhaust_id': ep.volumetric_exhaust_id,
                    'sound_event_action_on': ep.sound_event_action_on,
                    'exportable': ep.exportable,
                    'location': list(obj.location) if obj.location is not None else None,
                }
                obj['_engine_meta'] = meta_dict_to_xml_str(meta)
                obj['_no_export'] = True
                count += 1
            except Exception:
                pass
        self.report({'INFO'}, f"Baked engine metadata for {count} objects")
        return {'FINISHED'}

class OBJECT_OT_export_glb_with_meta(bpy.types.Operator):
    bl_idname = "export.glb_with_meta"
    bl_label = "Export GLB + Thruster Metadata"
    bl_description = "Export scene to GLB excluding thruster objects and write thruster metadata JSON"
    
    filepath: bpy.props.StringProperty(
        name="Filepath",
        description="GLB output path",
        subtype='FILE_PATH',
        default="",
    )

    def invoke(self, context, event):
        try:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            return self.execute(context)

    def execute(self, context):
        scene = getattr(context, 'scene', None)
        if scene is None:
            self.report({'ERROR'}, "No scene found")
            return {'CANCELLED'}
        thrusters = [o for o in scene.objects if (o.get('_thruster_meta') is not None) or (getattr(o, 'thruster_props', None) is not None)]
        non_thrusters = [o for o in scene.objects if o not in thrusters]
        prev_selected = [o for o in context.selected_objects]
        prev_active = getattr(context.view_layer, 'objects', None) and context.view_layer.objects.active
        try:
            try:
                bpy.ops.object.select_all(action='DESELECT')
            except Exception: pass
            for o in non_thrusters:
                try: o.select_set(True)
                except Exception: pass
            if non_thrusters:
                try: context.view_layer.objects.active = non_thrusters[0]
                except Exception: pass
            try:
                bpy.ops.export_scene.gltf(filepath=self.filepath, export_format='GLB', use_selection=True)
            except Exception as e:
                self.report({'ERROR'}, f"GLB export failed: {e}")
                return {'CANCELLED'}
            meta_list = []
            for o in thrusters:
                jm = o.get('_thruster_meta')
                if jm:
                    parsed = parse_meta_string(jm)
                    if isinstance(parsed, dict):
                        meta_list.append(parsed)
                        continue
                    elif isinstance(parsed, list):
                        meta_list.extend(parsed)
                        continue
                kp = getattr(o, 'thruster_props', None)
                if kp is not None:
                    entry = {
                        'name': o.name,
                        'thrust_n': kp.thrust_n,
                        'specific_impulse_seconds': kp.specific_impulse_seconds,
                        'minimum_pulse_time_seconds': kp.minimum_pulse_time_seconds,
                        'volumetric_exhaust_id': kp.volumetric_exhaust_id,
                        'sound_event_on': kp.sound_event_on,
                        'control_map_translation': _safe_vector_to_list(kp.control_map_translation),
                        'control_map_rotation': _safe_vector_to_list(kp.control_map_rotation),
                        'exportable': kp.exportable,
                        'location': list(o.location) if o.location is not None else None,
                    }
                    meta_list.append(entry)
            base = os.path.splitext(self.filepath)[0]
            meta_path = base + '_meta.xml'
            try:
                xml_text = thrusters_list_to_xml_str(meta_list)
                with open(meta_path, 'w', encoding='utf-8') as f:
                    f.write(xml_text)
            except Exception as e:
                self.report({'WARNING'}, f"GLB exported but failed to write meta file: {e}")
                return {'FINISHED'}
            self.report({'INFO'}, f"Exported GLB and wrote {len(meta_list)} metadata entries to {meta_path}")
            return {'FINISHED'}
        finally:
            try: bpy.ops.object.select_all(action='DESELECT')
            except Exception: pass
            for o in prev_selected:
                try: o.select_set(True)
                except Exception: pass
            try:
                if prev_active is not None:
                    context.view_layer.objects.active = prev_active
            except Exception: pass
