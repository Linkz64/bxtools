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
	if self.disable_name_update_func:
		self.disable_name_update_func = False
		return

	name = self.name
	name_list = [seq.name for seq in context.scene.ssx2_LogicSequences]

	if name_list.count(name) > 1:
		count = 1
		new_name = f"{name}.{count:03}"

		while new_name in name_list:
			count += 1
			new_name = f"{name}.{count:03}"

		self.disable_name_update_func = True
		self.name = new_name



class LogicImporters:
	def __init__(self, scene, sequences, effects, data):
		self.scene = scene
		self.sequences = sequences
		self.effects = effects
		self.data = data

		self.num_seq_start = len(sequences)
		self.defer_refs_run_on_target = []
		self.defer_refs_teleport = []

		self.importers = {
			0: {
				5: self.import_dead_node,
				11: self.import_texture_flip,
			},

			4: self.import_wait,
			7: self.import_run_on_target,
			14: self.import_multiplier,
			24: self.import_teleport,

		}

		self.import_all(data)

		# TODO: remove self.scene 

	def import_all(self, json_string):
		num_seq = self.num_seq_start
		num_fx_undef = len(self.effects.undefined)

		for i, json_seq in enumerate(self.data["EffectHeaders"]):
			seq_name = json_seq["EffectName"]
			print("\n seq:", i, "name:", seq_name)

			seq = self.sequences.add()

			# seq.disable_name_update_func = True

			seq.name = "Sequence " + str(num_seq) \
				if seq_name == "Effect " + str(i) \
				else seq_name


			for j, json_fx in enumerate(json_seq["Effects"]):
				# print("json_fx", json_fx)

				type_found = False

				main_type = json_fx["MainType"]

				_main = self.importers.get(main_type)

				if type(_main) is not dict and _main is not None:
					_main(seq, json_fx)
					type_found = True
				else:
					if json_fx["MainType"] == 0:
						# sub_type = json_fx["type0"]["SubType"]

						import_func = _main.get(json_fx["type0"]["SubType"])

						if import_func is not None:
							import_func(seq, json_fx)

							type_found = True


				
				if type_found == False:

					fx = self.effects.undefined.add()
					fx.json_string = str(json_fx).replace("'", '"')
					# fx.json_string = "Hello there!"

					fx_ref = seq.effect_refs.add()
					fx_ref.index = num_fx_undef
					fx_ref.kind = 'undefined'

					num_fx_undef += 1


			num_seq += 1

			# if i == 1:
			# 	break

	def import_dead_node(self, seq, json_fx):
		fx_index = len(self.effects.dead_node)

		fx = self.effects.dead_node.add()
		fx.mode = json_fx["type0"]["DeadNodeMode"]

		fx_ref = seq.effect_refs.add()
		fx_ref.index = fx_index
		fx_ref.kind = 'dead_node'

	def import_wait(self, seq, json_fx):
		fx_index = len(self.effects.wait)

		fx = self.effects.wait.add()
		fx.time = json_fx["WaitTime"]

		fx_ref = seq.effect_refs.add()
		fx_ref.index = fx_index
		fx_ref.kind = 'wait'

	def import_run_on_target(self, seq, json_fx):
		fx_index = len(self.effects.run_on_target)

		self.effects.run_on_target.add()

		fx_ref = seq.effect_refs.add()
		fx_ref.index = fx_index
		fx_ref.kind = 'run_on_target'

		json_fx = json_fx["Instance"]
		self.defer_refs_run_on_target.append((fx_index, json_fx["InstanceIndex"], json_fx["EffectIndex"]))

	def import_texture_flip(self, seq, json_fx):
		json_fx = json_fx["type0"]["TextureFlip"]
		fx_index = len(self.effects.texture_flip)

		fx = self.effects.texture_flip.add()
		fx.u0 = json_fx["U0"]
		fx.direction = json_fx["Direction"]
		fx.speed = json_fx["Speed"]
		fx.length = json_fx["Length"]
		fx.u4 = json_fx["U4"]

		fx_ref = seq.effect_refs.add()
		fx_ref.index = fx_index
		fx_ref.kind = 'texture_flip'

	def import_multiplier(self, seq, json_fx):
		fx_index = len(self.effects.multiplier)

		fx = self.effects.multiplier.add()
		fx.factor = json_fx["MultiplierScore"]

		fx_ref = seq.effect_refs.add()
		fx_ref.index = fx_index
		fx_ref.kind = 'multiplier'

	def import_teleport(self, seq, json_fx):
		fx_index = len(self.effects.teleport)

		self.effects.teleport.add()

		fx_ref = seq.effect_refs.add()
		fx_ref.index = fx_index
		fx_ref.kind = 'teleport'

		self.defer_refs_teleport.append((fx_index, json_fx["TeleportInstanceIndex"]))






class LogicDraw:
	def __init__(self, scene):
		self.scene = scene
		self.effects = scene.ssx2_Effects


	effect_drawers = {}


	def draw_kind(self, layout, kind, index):
		draw_func = self.effect_drawers.get(kind)

		if draw_func is not None:
			draw_func(self, layout, index)


	def draw_undefined(self, layout, index):
		effect = self.effects.undefined[index]

		layout.prop(effect, "checked", text="JSON")
		layout.prop(effect, "json_string", text="", expand=True)

	def draw_dead_node(self, layout, index):
		effect = self.effects.dead_node[index]
		layout.prop(effect, "checked", text="Dead Node")
		layout.prop(effect, "mode", text="Mode")

	def draw_wait(self, layout, index):
		effect = self.effects.wait[index]
		layout.prop(effect, "checked", text="Wait")
		layout.prop(effect, "time", text="Time")

	def draw_run_on_target(self, layout, index):
		effect = self.effects.run_on_target[index]
		layout.prop(effect, "checked", text="Run on Target")
		layout.prop(effect, "target_instance", text="")
		layout.prop_search(
			effect,
			"target_sequence",
			bpy.context.scene,
			"ssx2_LogicSequences",
			icon='VIEWZOOM',
			text="",
		)

	def draw_texture_flip(self, layout, index):
		effect = self.effects.texture_flip[index]

		col = layout.column()

		col.prop(effect, "checked", text="Texture Flip")

		col.prop(effect, "u0", text="Unknown 0")
		col.prop(effect, "direction", text="Direction")
		col.prop(effect, "speed", text="Speed")
		col.prop(effect, "length", text="Length")
		col.prop(effect, "u4", text="Unknown 4")

	def draw_multiplier(self, layout, index):
		effect = self.effects.multiplier[index]
		layout.prop(effect, "checked", text="Multiplier")
		layout.prop(effect, "factor", text="Factor")

	def draw_teleport(self, layout, index):
		effect = self.effects.teleport[index]
		layout.prop(effect, "checked", text="Teleport")
		layout.prop(effect, "target", text="Target")


LogicDraw.effect_drawers = {
	"undefined": LogicDraw.draw_undefined,
	"dead_node": LogicDraw.draw_dead_node,
	"wait": LogicDraw.draw_wait,
	"run_on_target": LogicDraw.draw_run_on_target,
	"texture_flip": LogicDraw.draw_texture_flip,
	"multiplier": LogicDraw.draw_multiplier,
	"teleport": LogicDraw.draw_teleport,
}

enum_ssx2_effect_types = (
	('undefined', "UNDEFINED", ""),
	('dead_node', "Dead Node", ""),
	('wait', "Wait", ""),
	('run_on_target', "Run on Target", ""),
	('texture_flip', "Texture Flip", ""),
	('multiplier', "Multiplier", ""),
	('teleport', "Teleport", ""),
)



### Properties

class SSX2_PG_WorldEffectRef(PropertyGroup):
	index: IntProperty()
	kind: EnumProperty(items=enum_ssx2_effect_types)


class SSX2_PG_WorldLogicSequence(PropertyGroup):
	name: StringProperty(update=update_sequence_name)
	disable_name_update_func: BoolProperty()
	expanded: BoolProperty()
	effect_refs: CollectionProperty(type=SSX2_PG_WorldEffectRef)
	
	# I could do it with indices:
	# checked: CollectionProperty(type=?)


class SSX2_PG_WorldLogicSlotsSet(PropertyGroup):
	constant: IntProperty(default=-1)
	collision: IntProperty(default=-1)
	slot3: IntProperty(default=-1)
	slot4: IntProperty(default=-1)
	logic_trigger: IntProperty(default=-1)
	slot6: IntProperty(default=-1)
	slot7: IntProperty(default=-1)


class SSX2_PG_WorldEffectUndefined(PropertyGroup):
	checked: BoolProperty(options={'SKIP_SAVE'})
	json_string: StringProperty()

class SSX2_PG_WorldEffectDeadNode(PropertyGroup):
	checked: BoolProperty(options={'SKIP_SAVE'})
	mode: IntProperty() # TODO: Convert to Enum

class SSX2_PG_WorldEffectTextureFlip(PropertyGroup):
	checked: BoolProperty(options={'SKIP_SAVE'})
	u0: IntProperty()
	direction: IntProperty()
	speed: FloatProperty()
	length: FloatProperty()
	u4: IntProperty()

class SSX2_PG_WorldEffectWait(PropertyGroup):
	checked: BoolProperty(options={'SKIP_SAVE'})
	time: FloatProperty()

class SSX2_PG_WorldEffectRunOnTarget(PropertyGroup):
	checked: BoolProperty(options={'SKIP_SAVE'})
	target_instance: PointerProperty(type=bpy.types.Object)
	target_sequence: StringProperty()

class SSX2_PG_WorldEffectMultiplier(PropertyGroup):
	checked: BoolProperty(options={'SKIP_SAVE'})
	factor: FloatProperty()

class SSX2_PG_WorldEffectTeleport(PropertyGroup):
	checked: BoolProperty(options={'SKIP_SAVE'})
	target: PointerProperty(type=bpy.types.Object)




class SSX2_PG_WorldEffects(PropertyGroup):

	undefined: CollectionProperty(type=SSX2_PG_WorldEffectUndefined) # aka JSON

	# type 0
	# t0_s0: CollectionProperty(type=)
	# t0_s2: CollectionProperty(type=)
	dead_node: CollectionProperty(type=SSX2_PG_WorldEffectDeadNode)
	# counter: CollectionProperty(type=)
	# t0_s7: CollectionProperty(type=)
	# uv_scroll: CollectionProperty(type=)
	texture_flip: CollectionProperty(type=SSX2_PG_WorldEffectTextureFlip)
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
	wait: CollectionProperty(type=SSX2_PG_WorldEffectWait)
	# # type 5
	# t5_s0: CollectionProperty(type=)

	# # type 7
	run_on_target: CollectionProperty(type=SSX2_PG_WorldEffectRunOnTarget) # aka Script?
	# # type 8
	# play_sound: CollectionProperty(type=)
	# # type 9

	# # type 13
	# reset: CollectionProperty(type=)
	# # type 14
	multiplier: CollectionProperty(type=SSX2_PG_WorldEffectMultiplier)
	# # type 17
	# boost: CollectionProperty(type=)
	# # type 18
	# trick_boost: CollectionProperty(type=)
	# # type 21
	# function_run: CollectionProperty(type=)
	# # type 24
	teleport: CollectionProperty(type=SSX2_PG_WorldEffectTeleport)
	# # type 25
	# spline_effect: CollectionProperty(type=)



	"""
	├── Type 0
	│   ├── Sub 0
	│   ├── Sub 2
	│   ├── Sub 5 (Dead Node) --------------------
	│   ├── Sub 6 (Counter)
	│   ├── Sub 7
	│   ├── Sub 10 (UV Scroll)
	│   ├── Sub 11 (Texture Flip) --------------------
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
	├── Type 4 (Wait) --------------------
	├── Type 5
	├── Type 7 (Instance Effect, Run on Target)  --------------------
	├── Type 8 (Play Sound)
	├── Type 9
	├── Type 13 (Reset)
	├── Type 14 (Multiplier)
	├── Type 17 (Boost)
	├── Type 18 (Trick Boost)
	├── Type 21 (Function Run)
	├── Type 24 (Teleport) --------------------
	└── Type 25 (Spline Effect)
	
	"""












### Operators

class SSX2_OP_EffectMoveUpDown(Operator):
	bl_idname = 'scene.ssx2_effect_move_up_down'
	bl_label = "Effect Move Up/Down"
	bl_description = "Move effect up or down"
	bl_options = {'UNDO'}

	vals: IntVectorProperty()

	def execute(self, context):
		scene = context.scene

		seq_idx = self.vals[1]
		fx_idx = self.vals[2]

		effect_refs = scene.ssx2_LogicSequences[seq_idx].effect_refs

		if self.vals[0] == 0: # UP
			if fx_idx == 0:
				return {'CANCELLED'} # TODO? move to end

			other_idx = fx_idx - 1

		else: # DOWN
			if fx_idx == len(effect_refs) - 1:
				return {'CANCELLED'} # TODO? move to start

			other_idx = fx_idx + 1

		current = (effect_refs[fx_idx].index, effect_refs[fx_idx].kind)
		other = (effect_refs[other_idx].index, effect_refs[other_idx].kind)

		effect_refs[fx_idx].index = other[0]
		effect_refs[fx_idx].kind = other[1]


		effect_refs[other_idx].index = current[0]
		effect_refs[other_idx].kind = current[1]

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

		seq = scene.ssx2_LogicSequences[num_seq]
		effect_refs = seq.effect_refs

		seq.name = "Sequence " + str(num_seq)

		num_fx = len(effect_refs)
		num_dead_node = len(scene.ssx2_Effects.dead_node)
		num_wait = len(scene.ssx2_Effects.wait)

		effect_refs.add()
		effect_refs[num_fx].index = num_dead_node
		effect_refs[num_fx].kind = 'dead_node'

		scene.ssx2_Effects.dead_node.add()
		scene.ssx2_Effects.dead_node[num_dead_node].mode = 5



		effect_refs.add()
		effect_refs[num_fx + 1].index = num_wait
		effect_refs[num_fx + 1].kind = 'wait'

		scene.ssx2_Effects.wait.add()
		scene.ssx2_Effects.wait[num_wait].time = 3.33



		effect_refs.add()
		effect_refs[num_fx + 2].index = num_dead_node + 1
		effect_refs[num_fx + 2].kind = 'dead_node'

		scene.ssx2_Effects.dead_node.add()
		scene.ssx2_Effects.dead_node[num_dead_node + 1].mode = 77





		obj = bpy.data.objects.new("LogicTestObject", None)
		obj.ssx2_EmptyMode = 'INSTANCE'
		context.collection.objects.link(obj)


		slots_set = obj.ssx2_LogicSlotsSet

		slots_set.constant = num_seq
		slots_set.collision = -1
		# slots_set.slot3 = 
		# slots_set.slot4 = 
		# slots_set.logic_trigger = 
		# slots_set.slot6 = 
		# slots_set.slot7 = 


		logic_choice_test = scene.ssx2_LogicSequenceChoiceConstant
		logic_choice_test = seq.name


		# for seq in scene.ssx2_LogicSequences:
		# 	print("\n", seq.name)
		# 	for fx_ref in seq.effect_refs:
		# 		print(fx_ref.index, fx_ref.kind)



		# prints custom props within the class:
		# for prop in SSX2_WorldEffects.bl_rna.properties:
		# 	if prop.is_runtime:
		# 		print(prop.identifier)



		return {'FINISHED'}



### Functions

def update_sequence_choice_constant(self, context):
	choice_name = self.ssx2_LogicSequenceChoiceConstant

	if choice_name != "":
		for i, seq in enumerate(self.ssx2_LogicSequences):
			if seq.name == choice_name:
				bpy.context.active_object.ssx2_LogicSlotsSet.constant = i
				break
		self.ssx2_LogicSequenceChoiceConstant = ""

def update_sequence_choice_collision(self, context):
	choice_name = self.ssx2_LogicSequenceChoiceCollision

	if choice_name != "":
		for i, seq in enumerate(self.ssx2_LogicSequences):
			if seq.name == choice_name:
				bpy.context.active_object.ssx2_LogicSlotsSet.collision = i
				break
		self.ssx2_LogicSequenceChoiceCollision = ""

def update_sequence_choice_slot3(self, context):
	choice_name = self.ssx2_LogicSequenceChoiceSlot3

	if choice_name != "":
		for i, seq in enumerate(self.ssx2_LogicSequences):
			if seq.name == choice_name:
				bpy.context.active_object.ssx2_LogicSlotsSet.slot3 = i
				break
		self.ssx2_LogicSequenceChoiceSlot3 = ""

def update_sequence_choice_slot4(self, context):
	choice_name = self.ssx2_LogicSequenceChoiceSlot4

	if choice_name != "":
		for i, seq in enumerate(self.ssx2_LogicSequences):
			if seq.name == choice_name:
				bpy.context.active_object.ssx2_LogicSlotsSet.slot4 = i
				break
		self.ssx2_LogicSequenceChoiceSlot4 = ""

def update_sequence_choice_logic_trigger(self, context):
	choice_name = self.ssx2_LogicSequenceChoiceLogicTrigger

	if choice_name != "":
		for i, seq in enumerate(self.ssx2_LogicSequences):
			if seq.name == choice_name:
				bpy.context.active_object.ssx2_LogicSlotsSet.logic_trigger = i
				break
		self.ssx2_LogicSequenceChoiceLogicTrigger = ""

def update_sequence_choice_slot6(self, context):
	choice_name = self.ssx2_LogicSequenceChoiceSlot6

	if choice_name != "":
		for i, seq in enumerate(self.ssx2_LogicSequences):
			if seq.name == choice_name:
				bpy.context.active_object.ssx2_LogicSlotsSet.slot6 = i
				break
		self.ssx2_LogicSequenceChoiceSlot6 = ""

def update_sequence_choice_slot7(self, context):
	choice_name = self.ssx2_LogicSequenceChoiceSlot7

	if choice_name != "":
		for i, seq in enumerate(self.ssx2_LogicSequences):
			if seq.name == choice_name:
				bpy.context.active_object.ssx2_LogicSlotsSet.slot7 = i
				break
		self.ssx2_LogicSequenceChoiceSlot7 = ""


classes = (
	SSX2_PG_WorldEffectRef,
	SSX2_PG_WorldLogicSequence,
	SSX2_PG_WorldLogicSlotsSet,

	SSX2_PG_WorldEffectUndefined,
	SSX2_PG_WorldEffectDeadNode,
	SSX2_PG_WorldEffectTextureFlip,
	SSX2_PG_WorldEffectWait,
	SSX2_PG_WorldEffectRunOnTarget,
	SSX2_PG_WorldEffectMultiplier,
	SSX2_PG_WorldEffectTeleport,

	SSX2_PG_WorldEffects,

	SSX2_OP_EffectMoveUpDown,
	SSX2_OP_LogicTest,
)




def ssx2_world_logic_register():
	for c in classes:
		register_class(c)


	bpy.types.Scene.ssx2_Effects = PointerProperty(type=SSX2_PG_WorldEffects)
	bpy.types.Scene.ssx2_LogicSequences = CollectionProperty(type=SSX2_PG_WorldLogicSequence)
	bpy.types.Object.ssx2_LogicSlotsSet = PointerProperty(type=SSX2_PG_WorldLogicSlotsSet)

	bpy.types.Scene.ssx2_LogicSequenceChoiceConstant = StringProperty(name="Choice Constant", update=update_sequence_choice_constant)
	bpy.types.Scene.ssx2_LogicSequenceChoiceCollision = StringProperty(name="Choice Collision", update=update_sequence_choice_collision)
	bpy.types.Scene.ssx2_LogicSequenceChoiceSlot3 = StringProperty(name="Choice Slot3", update=update_sequence_choice_slot3)
	bpy.types.Scene.ssx2_LogicSequenceChoiceSlot4 = StringProperty(name="Choice Slot4", update=update_sequence_choice_slot4)
	bpy.types.Scene.ssx2_LogicSequenceChoiceLogicTrigger = StringProperty(name="Choice LogicTrigger", update=update_sequence_choice_logic_trigger)
	bpy.types.Scene.ssx2_LogicSequenceChoiceSlot6 = StringProperty(name="Choice Slot6", update=update_sequence_choice_slot6)
	bpy.types.Scene.ssx2_LogicSequenceChoiceSlot7 = StringProperty(name="Choice Slot7", update=update_sequence_choice_slot7)


def ssx2_world_logic_unregister():

	del bpy.types.Scene.ssx2_LogicSequenceChoiceConstant
	del bpy.types.Scene.ssx2_LogicSequenceChoiceCollision
	del bpy.types.Scene.ssx2_LogicSequenceChoiceSlot3
	del bpy.types.Scene.ssx2_LogicSequenceChoiceSlot4
	del bpy.types.Scene.ssx2_LogicSequenceChoiceLogicTrigger
	del bpy.types.Scene.ssx2_LogicSequenceChoiceSlot6
	del bpy.types.Scene.ssx2_LogicSequenceChoiceSlot7

	del bpy.types.Object.ssx2_LogicSlotsSet
	del bpy.types.Scene.ssx2_LogicSequences
	del bpy.types.Scene.ssx2_Effects

	for c in classes:
		unregister_class(c)