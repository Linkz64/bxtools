import bpy
from bpy.utils import register_class, unregister_class

from bpy.types import PropertyGroup, Operator


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


enum_ssx2_effect_types = ( # move to constants?
	("dead_node", "Dead Node", ""),
	("wait", "Wait", ""), # aka sleep
)

effect_type_draws = {
	"dead_node": draw_dead_node,
	"wait": draw_wait,
}



class SSX2_WorldEffectDeadNodePropGroup(PropertyGroup):
	checked: bpy.props.BoolProperty()
	mode: bpy.props.IntProperty() # TODO: Convert to Enum

class SSX2_WorldEffectWaitPropGroup(PropertyGroup):
	checked: bpy.props.BoolProperty()
	time: bpy.props.FloatProperty()


class SSX2_WorldEffectsPropGroup(PropertyGroup):
	# type 0
	# t0_s0: bpy.props.CollectionProperty(type=)
	# t0_s2: bpy.props.CollectionProperty(type=)
	dead_node: bpy.props.CollectionProperty(type=SSX2_WorldEffectDeadNodePropGroup)
	# counter: bpy.props.CollectionProperty(type=)
	# t0_s7: bpy.props.CollectionProperty(type=)
	# uv_scroll: bpy.props.CollectionProperty(type=)
	# texture_flip: bpy.props.CollectionProperty(type=)
	# fence_flex: bpy.props.CollectionProperty(type=)
	# t0_s13: bpy.props.CollectionProperty(type=)
	# t0_s14: bpy.props.CollectionProperty(type=)
	# t0_s15: bpy.props.CollectionProperty(type=)
	# crowd: bpy.props.CollectionProperty(type=)
	# t0_s18: bpy.props.CollectionProperty(type=)
	# t0_s20: bpy.props.CollectionProperty(type=)
	# t0_s23: bpy.props.CollectionProperty(type=)
	# t0_s24: bpy.props.CollectionProperty(type=)
	# anim_object: bpy.props.CollectionProperty(type=)
	# t0_s257: bpy.props.CollectionProperty(type=)
	# t0_s258: bpy.props.CollectionProperty(type=)


	# # type 2
	# emitter: bpy.props.CollectionProperty(type=)
	# t1_s1: bpy.props.CollectionProperty(type=)
	# t1_s2: bpy.props.CollectionProperty(type=)


	# # type 3
	# t3_s0: bpy.props.CollectionProperty(type=)
	# # type 4
	wait: bpy.props.CollectionProperty(type=SSX2_WorldEffectWaitPropGroup)
	# # type 5
	# t5_s0: bpy.props.CollectionProperty(type=)

	# # type 7
	# instance_effect: bpy.props.CollectionProperty(type=)
	# # type 8
	# play_sound: bpy.props.CollectionProperty(type=)
	# # type 9

	# # type 13
	# reset: bpy.props.CollectionProperty(type=)
	# # type 14
	# multiplier: bpy.props.CollectionProperty(type=)
	# # type 17
	# boost: bpy.props.CollectionProperty(type=)
	# # type 18
	# trick_boost: bpy.props.CollectionProperty(type=)
	# # type 21
	# function_run: bpy.props.CollectionProperty(type=)
	# # type 24
	# teleport: bpy.props.CollectionProperty(type=)
	# # type 25
	# spline_effect: bpy.props.CollectionProperty(type=)



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

class SSX2_WorldEffectRefPropGroup(PropertyGroup):
	index: bpy.props.IntProperty()
	kind: bpy.props.EnumProperty(items = enum_ssx2_effect_types)


class SSX2_WorldLogicSequencePropGroup(PropertyGroup):
	# name: <- already built-in
	expanded: bpy.props.BoolProperty() 
	# checked: bpy.props.BoolProperty()
	effects: bpy.props.CollectionProperty(type=SSX2_WorldEffectRefPropGroup)
	
	# I could do it with indices:
	# checked: bpy.props.CollectionProperty(type=?)



class SSX2_OP_EffectMoveUpDown(Operator):
	bl_idname = 'scene.ssx2_effect_move_up_down'
	bl_label = "Effect Move Up/Down"
	bl_description = "Move effect up or down"
	bl_options = {'UNDO'}

	vals: bpy.props.IntVectorProperty()

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
		# for prop in SSX2_WorldEffectsPropGroup.bl_rna.properties:
		# 	if prop.is_runtime:
		# 		print(prop.identifier)



		return {'FINISHED'}




classes = (
	SSX2_WorldEffectDeadNodePropGroup,
	SSX2_WorldEffectWaitPropGroup,

	SSX2_WorldEffectRefPropGroup,
	SSX2_WorldEffectsPropGroup,

	SSX2_WorldLogicSequencePropGroup,

	SSX2_OP_EffectMoveUpDown,
	SSX2_OP_LogicTest,
)

def ssx2_world_logic_register():
	for c in classes:
		register_class(c)

	bpy.types.Scene.ssx2_Effects = bpy.props.PointerProperty(type=SSX2_WorldEffectsPropGroup)
	bpy.types.Scene.ssx2_LogicSequences = bpy.props.CollectionProperty(type=SSX2_WorldLogicSequencePropGroup)

def ssx2_world_logic_unregister():

	del bpy.types.Scene.ssx2_LogicSequences

	for c in classes:
		unregister_class(c)