import bpy

class ThrusterProperties(bpy.types.PropertyGroup):
    """Holds editable parameters for a 'Kitten' object that will be used by the exporter."""
    
    fx_location: bpy.props.FloatVectorProperty(
        name="FxLocation",
        description="Origin of the thruster effect",
        default=(0.0, 0.0, 0.0),
    )
    
    thrust_n: bpy.props.FloatProperty(
        name="Thrust N",
        description="Thrust in Newtons",
        default=40,
        min=0.00,
    )
    
    specific_impulse_seconds: bpy.props.FloatProperty(
        name="Specific impulse seconds",
        description="Isp in seconds",
        default=0.0,
        min=0.00,
    )
    
    minimum_pulse_time_seconds: bpy.props.FloatProperty(
        name="Minimum pulse time seconds",
        description="Min pulse duration",
        default=0.0,
        min=0.00,
    )
    
    volumetric_exhaust_id: bpy.props.StringProperty(
        name="VolumetricExhaust_id",
        description="",
        default="ApolloRCS"
    )
    
    sound_event_on: bpy.props.StringProperty(
        name="Sound event on",
        description="",
        default="DefaultRcdThruster"
    )
    
    control_map_translation: bpy.props.BoolVectorProperty(
        name="control_map_translation",
        description="Set if thruster should fire on translation input. [Fwd, Bwd, Left, Right, Up, Down]",
        default=[False, False, False, False, False, False],
        size=6
    )
    
    control_map_rotation: bpy.props.BoolVectorProperty(
        name="control_map_rotation",
        description="Set if thruster should fire on rotation input. [PitchUp, PitchDown, RollLeft, RollRight, YawLeft, YawRight]",
        default=[False, False, False, False, False, False],
        size=6
    )
    
    exportable: bpy.props.BoolProperty(
        name="Export",
        description="Include this object in custom exports",
        default=True,
    )

class EngineProperties(bpy.types.PropertyGroup):
    """Holds editable parameters for an 'Engine' object that will be used by the exporter."""
    
    thrust_kn: bpy.props.FloatProperty(
        name="Thrust kN",
        description="Engine thrust in kilonewtons",
        default=650.0,
        min=0.00,
    )
    
    specific_impulse_seconds: bpy.props.FloatProperty(
        name="Specific Impulse Seconds",
        description="Specific impulse in seconds",
        default=10000.0,
        min=0.00,
    )
    
    minimum_throttle: bpy.props.FloatProperty(
        name="Minimum Throttle",
        description="Minimum throttle value (0-1)",
        default=0.05,
        min=0.00,
        max=1.00,
    )
    
    volumetric_exhaust_id: bpy.props.StringProperty(
        name="VolumetricExhaust_id",
        description="",
        default="ApolloCSM"
    )
    
    sound_event_action_on: bpy.props.StringProperty(
        name="SoundEventAction_On",
        description="",
        default="DefaultEngineSoundBehavior"
    )
    
    exportable: bpy.props.BoolProperty(
        name="Export",
        description="Include this object in custom exports",
        default=True,
    )
