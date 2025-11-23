import json
import math
import mathutils
import xml.etree.ElementTree as ET

def _safe_vector_to_list(vec_prop):
    """Safely convert a Blender vector property to a Python list."""
    try:
        return list(vec_prop)
    except TypeError:
        try:
            return [vec_prop[i] for i in range(len(vec_prop))]
        except Exception:
            try:
                return [x for x in vec_prop]
            except Exception:
                return None

def _thruster_dict_to_xml_element(parent, thruster_data):
    """Convert a single thruster dict to KSA-format XML element."""
    thruster = ET.SubElement(parent, 'Thruster', Id=thruster_data.get('name', 'Unnamed'))

    # Location
    loc = thruster_data.get('location', [0.0, 0.0, 0.0])
    fx_offset = thruster_data.get('fx_location', [0.0, 0.0, 0.0])
    
    if loc and fx_offset:
        final_loc = [loc[0] + fx_offset[0], loc[1] + fx_offset[1], loc[2] + fx_offset[2]]
    else:
        final_loc = loc
        
    if final_loc:
        ET.SubElement(thruster, 'Location', X=str(final_loc[0]), Y=str(final_loc[1]), Z=str(final_loc[2]))

    # ExhaustDirection
    rotation = thruster_data.get('rotation', [0.0, 0.0, 0.0])  # Euler angles in radians (x, y, z)

    if rotation:
        try:
            eul = mathutils.Euler(rotation, 'XYZ')
            # Rotate local +Z to world space
            dir_vec = eul.to_matrix() @ mathutils.Vector((0.0, 0.0, 1.0))
            if dir_vec.length_squared > 0.0:
                dir_vec.normalize()
            ex_dir = [dir_vec.x, dir_vec.y, dir_vec.z]
        except Exception:
            # Fallback if mathutils is not available for some reason
            ex_dir = [1.0, 0.0, 0.0]
    else:
        # Default: forward in your KSA system
        ex_dir = [1.0, 0.0, 0.0]

    ET.SubElement(thruster, 'ExhaustDirection', X=str(ex_dir[0]), Y=str(ex_dir[1]), Z=str(ex_dir[2]))

    # ControlMap
    csv_parts = []
    trans_map = thruster_data.get('control_map_translation', [])
    rot_map = thruster_data.get('control_map_rotation', [])
    
    trans_labels = ["TranslateForward", "TranslateBackward", "TranslateLeft", "TranslateRight", "TranslateUp", "TranslateDown"]
    rot_labels = ["PitchUp", "PitchDown", "RollLeft", "RollRight", "YawLeft", "YawRight"]

    if trans_map:
        for i, enabled in enumerate(trans_map):
            if enabled and i < len(trans_labels):
                csv_parts.append(trans_labels[i])
                
    if rot_map:
        for i, enabled in enumerate(rot_map):
            if enabled and i < len(rot_labels):
                csv_parts.append(rot_labels[i])

    csv_value = ','.join(csv_parts) if csv_parts else ''
    ET.SubElement(thruster, 'ControlMap', CSV=csv_value)

    # Attributes
    ET.SubElement(thruster, 'Thrust', N=str(thruster_data.get('thrust_n', 40.0)))
    ET.SubElement(thruster, 'SpecificImpulse', Seconds=str(thruster_data.get('specific_impulse_seconds', 220.0)))
    ET.SubElement(thruster, 'MinimumPulseTime', Seconds=str(thruster_data.get('minimum_pulse_time_seconds', 0.008)))
    ET.SubElement(thruster, 'VolumetricExhaust', Id=thruster_data.get('volumetric_exhaust_id', 'ApolloRCS'))
    ET.SubElement(thruster, 'SoundEvent', Action='On', SoundId=thruster_data.get('sound_event_on', 'DefaultRcsThruster'))

def _engine_dict_to_xml_element(parent, engine_data):
    """Convert a single engine dict to KSA-format XML element."""
    engine = ET.SubElement(parent, 'Engine', Id=engine_data.get('name', 'Unnamed'))

    # Location
    loc = engine_data.get('location', [0.0, 0.0, 0.0])
    if loc:
        ET.SubElement(engine, 'Location', X=str(loc[0]), Y=str(loc[1]), Z=str(loc[2]))

    # ExhaustDirection
    rotation = engine_data.get('rotation', [0.0, 0.0, 0.0])
    if rotation:
        cos_y = math.cos(rotation[1])
        sin_y = math.sin(rotation[1])
        cos_z = math.cos(rotation[2])
        sin_z = math.sin(rotation[2])
        
        ex_dir = [
            cos_y * cos_z,
            cos_y * sin_z,
            sin_y
        ]
    else:
        ex_dir = [1.0, 0.0, 0.0]

    ET.SubElement(engine, 'ExhaustDirection', X=str(ex_dir[0]), Y=str(ex_dir[1]), Z=str(ex_dir[2]))

    # Attributes
    thrust_kn = engine_data.get('thrust_kn', 650.0)
    ET.SubElement(engine, 'Thrust', N=str(thrust_kn * 1000.0))
    ET.SubElement(engine, 'SpecificImpulse', Seconds=str(engine_data.get('specific_impulse_seconds', 452.0)))
    ET.SubElement(engine, 'MinimumThrottle', Value=str(engine_data.get('minimum_throttle', 0.05)))
    ET.SubElement(engine, 'VolumetricExhaust', Id=engine_data.get('volumetric_exhaust_id', 'ApolloCSM'))
    ET.SubElement(engine, 'SoundEvent', Action='On', SoundId=engine_data.get('sound_event_action_on', 'DefaultEngineSoundBehavior'))

def thrusters_list_to_xml_str(list_of_meta):
    root = ET.Element('Thrusters')
    for meta in list_of_meta:
        _thruster_dict_to_xml_element(root, meta)
    _indent_xml(root)
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    return xml_str.replace('\n', '\r\n')


def engines_list_to_xml_str(list_of_meta):
    root = ET.Element('Engines')
    for meta in list_of_meta:
        _engine_dict_to_xml_element(root, meta)
    _indent_xml(root)
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    return xml_str.replace('\n', '\r\n')

def meta_dict_to_xml_str(meta_dict):
    root = ET.Element('metadata')
    for k, v in meta_dict.items():
        if isinstance(v, (list, tuple)):
            sub = ET.SubElement(root, k)
            for item in v:
                ET.SubElement(sub, 'item').text = str(item)
        else:
            ET.SubElement(root, k).text = str(v)
    return ET.tostring(root, encoding='utf-8').decode('utf-8')

def _element_to_dict(elem):
    d = {}
    for child in elem:
        if len(child):
            tags = [c.tag for c in child]
            texts = [c.text for c in child]
            if set(tags) <= {'r', 'g', 'b'}:
                d[child.tag] = [float(t) for t in texts]
            elif set(tags) <= {'x', 'y', 'z'}:
                d[child.tag] = [float(t) for t in texts]
            else:
                vals = []
                for t in texts:
                    if t is None:
                        vals.append(None)
                    else:
                        try:
                            if '.' in t: vals.append(float(t))
                            else: vals.append(int(t))
                        except Exception:
                            if t.lower() in ('true', 'false'): vals.append(t.lower() == 'true')
                            else: vals.append(t)
                d[child.tag] = vals
        else:
            t = child.text
            if t is None:
                d[child.tag] = None
            else:
                if t.lower() in ('true', 'false'):
                    d[child.tag] = t.lower() == 'true'
                else:
                    try:
                        if '.' in t: d[child.tag] = float(t)
                        else: d[child.tag] = int(t)
                    except Exception:
                        d[child.tag] = t
    return d

def parse_meta_string(s):
    if not s: return None
    s = s.strip()
    if s.startswith('<'):
        try:
            root = ET.fromstring(s)
            if root.tag == 'thruster': return _element_to_dict(root)
            if root.tag == 'thrusters': return [_element_to_dict(child) for child in root]
        except Exception:
            pass
    try:
        return json.loads(s)
    except Exception:
        return None


def sanitize_filename(name: str) -> str:
    """Sanitize object or image names for safe filesystem usage.
    Replaces disallowed characters with underscore and trims length. Guarantees non-empty.
    """
    import re
    if not name:
        return "unnamed"
    # Replace path separators and any char not in whitelist with '_'
    cleaned = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    # Avoid leading dots (hidden files on some OS)
    cleaned = cleaned.lstrip('.')
    if not cleaned:
        cleaned = 'unnamed'
    # Trim very long names to a reasonable length
    if len(cleaned) > 128:
        cleaned = cleaned[:128]
    return cleaned


def _indent_xml(elem, level=0):
    """In-place pretty formatter for an ElementTree element.
    Adds indentation and newlines so the XML is human-readable.
    """
    indent = "\n" + ("  " * level)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        for child in elem:
            _indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent + "  "
        # Trim last child's tail to single indent
        if elem[-1].tail:
            elem[-1].tail = indent
    else:
        if not elem.text or not elem.text.strip():
            elem.text = ''


def _extract_material_maps(mat):
    """Extract diffuse, normal, and combined rough/metal/ao images from a material.
    Returns a dict with optional keys: 'diffuse', 'normal', 'roughmetaao'.
    Heuristics:
    - Diffuse: image node whose name contains diffuse|albedo|basecolor|base_color or linked to Principled Base Color.
    - Normal: image node whose name contains normal or feeding into a Normal Map node.
    - RoughMetaAo: first image whose name contains rough|metal|ao|orm|rma.
    Safe against missing node trees; always returns dict (possibly empty)."""
    result = {}
    try:
        if not getattr(mat, 'use_nodes', False):
            return result
        nt = getattr(mat, 'node_tree', None)
        if nt is None:
            return result
        nodes = list(getattr(nt, 'nodes', []) or [])
        links = list(getattr(nt, 'links', []) or [])
        principled = [n for n in nodes if getattr(n, 'type', '') == 'BSDF_PRINCIPLED']
        normal_maps = [n for n in nodes if getattr(n, 'type', '') == 'NORMAL_MAP']
        for node in nodes:
            if getattr(node, 'type', '') != 'TEX_IMAGE':
                continue
            img = getattr(node, 'image', None)
            if img is None:
                continue
            lower = (getattr(img, 'name', '') or '').lower()
            # Diffuse by name
            if any(key in lower for key in ['diffuse', 'albedo', 'basecolor', 'base_color']) and 'diffuse' not in result:
                result['diffuse'] = img
            # Diffuse by link into Principled Base Color
            if 'diffuse' not in result:
                try:
                    for pnode in principled:
                        for inp in getattr(pnode, 'inputs', []) or []:
                            if getattr(inp, 'name', '').lower() in ['base color', 'basecolor']:
                                for link in links:
                                    if link.to_socket == inp and link.from_node == node:
                                        result['diffuse'] = img
                                        break
                        if 'diffuse' in result:
                            break
                except Exception:
                    pass
            # Normal by name
            if 'normal' not in result and 'normal' in lower:
                result['normal'] = img
            # Normal via Normal Map node link
            if 'normal' not in result:
                try:
                    for nmap in normal_maps:
                        for inp in getattr(nmap, 'inputs', []) or []:
                            if getattr(inp, 'name', '').lower() in ['color', 'image']:
                                for link in links:
                                    if link.to_socket == inp and link.from_node == node:
                                        result['normal'] = img
                                        break
                        if 'normal' in result:
                            break
                except Exception:
                    pass
            # Rough/Metal/AO packed
            if 'roughmetaao' not in result and any(key in lower for key in ['rough', 'metal', 'ao', 'orm', 'rma']):
                result['roughmetaao'] = img
        return result
    except Exception:
        return result
