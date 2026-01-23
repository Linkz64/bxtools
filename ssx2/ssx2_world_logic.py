import bpy
from bpy.utils import register_class, unregister_class

from bpy.types import PropertyGroup, Operator
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    # FloatVectorProperty,
    IntProperty,
    IntVectorProperty,
    PointerProperty,
    StringProperty,

)

def update_sequence_name(self, context):
	print(self, context.scene)


def draw_undefined(layout, scene, index):
	effect = scene.ssx2_Effects.undefined[index]

	col = layout.column()
	col.prop(effect, "checked", text="JSON")
	# col.label(text="Undefined")

	col.prop(effect, "json_string", text="", expand=True)




def draw_dead_node(layout, scene, index):
	effect = scene.ssx2_Effects.dead_node[index]
	layout.prop(effect, "checked", text="Dead Node")
	# layout.label(text="Dead Node")
	layout.prop(effect, "mode", text="Mode")

def draw_wait(layout, scene, index):
	effect = scene.ssx2_Effects.wait[index]
	layout.prop(effect, "checked", text="Wait")
	# layout.label(text="Wait")
	layout.prop(effect, "time", text="Time")

def draw_texture_flip(layout, scene, index):
	effect = scene.ssx2_Effects.texture_flip[index]

	col = layout.column()

	col.prop(effect, "checked", text="Texture Flip")
	# layout.label(text="Texture Flip")

	col.prop(effect, "u0", text="Unknown 0")
	col.prop(effect, "direction", text="Direction")
	col.prop(effect, "speed", text="Speed")
	col.prop(effect, "length", text="Length")
	col.prop(effect, "u4", text="Unknown 4")


enum_ssx2_effect_types = ( # move to constants?
	('undefined', "UNDEFINED", ""),
	('dead_node', "Dead Node", ""),
	('wait', "Wait", ""), # aka sleep
	('texture_flip', "Texture Flip", "")
)

effect_type_draws = {
	"undefined": draw_undefined,
	"dead_node": draw_dead_node,
	"wait": draw_wait,
	"texture_flip": draw_texture_flip,
}


class SSX2_WorldEffectUndefined(PropertyGroup):
	checked: BoolProperty()
	json_string: StringProperty()

class SSX2_WorldEffectDeadNode(PropertyGroup):
	checked: BoolProperty()
	mode: IntProperty() # TODO: Convert to Enum

class SSX2_WorldEffectTextureFlip(PropertyGroup):
	checked: BoolProperty()
	u0: IntProperty()
	direction: IntProperty()
	speed: FloatProperty()
	length: FloatProperty()
	u4: IntProperty()

class SSX2_WorldEffectWait(PropertyGroup):
	checked: BoolProperty()
	time: FloatProperty()


class SSX2_WorldEffects(PropertyGroup):

	undefined: CollectionProperty(type=SSX2_WorldEffectUndefined)

	# type 0
	# t0_s0: CollectionProperty(type=)
	# t0_s2: CollectionProperty(type=)
	dead_node: CollectionProperty(type=SSX2_WorldEffectDeadNode)
	# counter: CollectionProperty(type=)
	# t0_s7: CollectionProperty(type=)
	# uv_scroll: CollectionProperty(type=)
	texture_flip: CollectionProperty(type=SSX2_WorldEffectTextureFlip)
	# fence_flex: CollectionProperty(type=)
	# t0_s13: CollectionProperty(type=)
	# t0_s14: CollectionProperty(type=)
	# t0_s15: CollectionProperty(type=)
	# crowd: CollectionProperty(type=)
	# t0_s18: CollectionProperty(type=)
	# t0_s20: CollectionProperty(type=)
	# t0_s23: CollectionProperty(type=)
	# t0_s24: CollectionProperty(type=)
	# anim_object: CollectionProperty(type=)
	# t0_s257: CollectionProperty(type=)
	# t0_s258: CollectionProperty(type=)


	# # type 2
	# emitter: CollectionProperty(type=)
	# t1_s1: CollectionProperty(type=)
	# t1_s2: CollectionProperty(type=)


	# # type 3
	# t3_s0: CollectionProperty(type=)
	# # type 4
	wait: CollectionProperty(type=SSX2_WorldEffectWait)
	# # type 5
	# t5_s0: CollectionProperty(type=)

	# # type 7
	# instance_effect: CollectionProperty(type=)
	# # type 8
	# play_sound: CollectionProperty(type=)
	# # type 9

	# # type 13
	# reset: CollectionProperty(type=)
	# # type 14
	# multiplier: CollectionProperty(type=)
	# # type 17
	# boost: CollectionProperty(type=)
	# # type 18
	# trick_boost: CollectionProperty(type=)
	# # type 21
	# function_run: CollectionProperty(type=)
	# # type 24
	# teleport: CollectionProperty(type=)
	# # type 25
	# spline_effect: CollectionProperty(type=)



	"""
	├── Type 0
	│   ├── Sub 0
	│   ├── Sub 2
	│   ├── Sub 5 (Dead Node)
	│   ├── Sub 6 (Counter)
	│   ├── Sub 7
	│   ├── Sub 10 (UV Scroll)
	│   ├── Sub 11 (Texture Flip)
	│   ├── Sub 12 (Fence Flex)
	│   ├── Sub 13
	│   ├── Sub 14
	│   ├── Sub 15
	│   ├── Sub 17 (Crowd)
	│   ├── Sub 18
	│   ├── Sub 20
	│   ├── Sub 23
	│   ├── Sub 24
	│   ├── Sub 256 (AnimObject)
	│   ├── Sub 257
	│   └── Sub 258
	├── Type 2
	│   ├── Sub 0 (Emitter)
	│   ├── Sub 1
	│   └── Sub 2
	├── Type 3
	├── Type 4 (Wait)
	├── Type 5
	├── Type 7 (Instance Effect)
	├── Type 8 (Play Sound)
	├── Type 9
	├── Type 13 (Reset)
	├── Type 14 (Multiplier)
	├── Type 17 (Boost)
	├── Type 18 (Trick Boost)
	├── Type 21 (Function Run)
	├── Type 24 (Teleport)
	└── Type 25 (Spline Effect)
	
	"""

class SSX2_WorldEffectRef(PropertyGroup):
	index: IntProperty()
	kind: EnumProperty(items=enum_ssx2_effect_types)


class SSX2_WorldLogicSequence(PropertyGroup):
	name: StringProperty(update=update_sequence_name)
	expanded: BoolProperty() 
	# checked: BoolProperty()
	effects: CollectionProperty(type=SSX2_WorldEffectRef)
	
	# I could do it with indices:
	# checked: CollectionProperty(type=?)



class SSX2_OP_EffectMoveUpDown(Operator):
	bl_idname = 'scene.ssx2_effect_move_up_down'
	bl_label = "Effect Move Up/Down"
	bl_description = "Move effect up or down"
	bl_options = {'UNDO'}

	vals: IntVectorProperty()

	def execute(self, context):
		scene = context.scene

		print(self.vals[0], self.vals[1], self.vals[2])

		seq_idx = self.vals[1]
		fx_idx = self.vals[2]

		effects_prop = scene.ssx2_LogicSequences[seq_idx].effects

		if self.vals[0] == 0: # UP
			if fx_idx == 0:
				return {'CANCELLED'} # TODO? move to end

			other_idx = fx_idx - 1

		else: # DOWN
			if fx_idx == len(effects_prop) - 1:
				return {'CANCELLED'} # TODO? move to start

			other_idx = fx_idx + 1

		current = (effects_prop[fx_idx].index, effects_prop[fx_idx].kind)
		other = (effects_prop[other_idx].index, effects_prop[other_idx].kind)

		effects_prop[fx_idx].index = other[0]
		effects_prop[fx_idx].kind = other[1]


		effects_prop[other_idx].index = current[0]
		effects_prop[other_idx].kind = current[1]

		return {'FINISHED'}

class SSX2_OP_LogicTest(Operator):
	bl_idname = 'scene.ssx2_logic_test'
	bl_label = "Logic Test"
	# bl_description = 'Logic Test'
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		scene = context.scene

		num_seq = len(scene.ssx2_LogicSequences)

		scene.ssx2_LogicSequences.add()

		scene.ssx2_LogicSequences[num_seq].name = "Sequence " + str(num_seq)

		num_fx = len(scene.ssx2_LogicSequences[num_seq].effects)
		num_dead_node = len(scene.ssx2_Effects.dead_node)
		num_wait = len(scene.ssx2_Effects.wait)

		scene.ssx2_LogicSequences[num_seq].effects.add()
		scene.ssx2_LogicSequences[num_seq].effects[num_fx].index = num_dead_node
		scene.ssx2_LogicSequences[num_seq].effects[num_fx].kind = 'dead_node'

		scene.ssx2_Effects.dead_node.add()
		scene.ssx2_Effects.dead_node[num_dead_node].mode = 5



		scene.ssx2_LogicSequences[num_seq].effects.add()
		scene.ssx2_LogicSequences[num_seq].effects[num_fx + 1].index = num_wait
		scene.ssx2_LogicSequences[num_seq].effects[num_fx + 1].kind = 'wait'

		scene.ssx2_Effects.wait.add()
		scene.ssx2_Effects.wait[num_wait].time = 3.33



		scene.ssx2_LogicSequences[num_seq].effects.add()
		scene.ssx2_LogicSequences[num_seq].effects[num_fx + 2].index = num_dead_node + 1
		scene.ssx2_LogicSequences[num_seq].effects[num_fx + 2].kind = 'dead_node'

		scene.ssx2_Effects.dead_node.add()
		scene.ssx2_Effects.dead_node[num_dead_node + 1].mode = 77



		# for seq in scene.ssx2_LogicSequences:
		# 	print("\n", seq.name)
		# 	for fx_ref in seq.effects:
		# 		print(fx_ref.index, fx_ref.kind)



		# prints custom props within the class:
		# for prop in SSX2_WorldEffects.bl_rna.properties:
		# 	if prop.is_runtime:
		# 		print(prop.identifier)



		return {'FINISHED'}




classes = (
	SSX2_WorldEffectUndefined,
	SSX2_WorldEffectDeadNode,
	SSX2_WorldEffectWait,
	SSX2_WorldEffectTextureFlip,

	SSX2_WorldEffectRef,
	SSX2_WorldEffects,

	SSX2_WorldLogicSequence,

	SSX2_OP_EffectMoveUpDown,
	SSX2_OP_LogicTest,
)

def ssx2_world_logic_register():
	for c in classes:
		register_class(c)

	bpy.types.Scene.ssx2_Effects = PointerProperty(type=SSX2_WorldEffects)
	bpy.types.Scene.ssx2_LogicSequences = CollectionProperty(type=SSX2_WorldLogicSequence)

def ssx2_world_logic_unregister():

	del bpy.types.Scene.ssx2_LogicSequences

	for c in classes:
		unregister_class(c)