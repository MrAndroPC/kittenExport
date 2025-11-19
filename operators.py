import bpy
import math
import os
import xml.etree.ElementTree as ET
from .utils import (
    _safe_vector_to_list, _thruster_dict_to_xml_element, _engine_dict_to_xml_element,
    thrusters_list_to_xml_str, engines_list_to_xml_str, meta_dict_to_xml_str,
    parse_meta_string
)

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

        # Collect all thrusters
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

        # Collect all engines
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
