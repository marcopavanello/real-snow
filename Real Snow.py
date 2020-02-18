# Addon Info
bl_info = {
	"name": "Real Snow",
	"description": "Generate snow mesh",
	"author": "Wolf",
	"version": (1, 0),
	"blender": (2, 81, 0),
	"location": "View 3D > Properties Panel",
	"wiki_url": "https://3d-wolf.com/products/snow.html",
	"tracker_url": "https://3d-wolf.com/products/snow.html",
	"support": "COMMUNITY",
	"category": "Mesh"
	}

#Libraries
import bpy
import math
import bmesh
import os
from bpy.props import *
from random import randint
from bpy.types import Panel, Operator, PropertyGroup
from mathutils import Vector
import time


# Panel
class REAL_PT_snow(Panel):
	bl_space_type = "VIEW_3D"
	bl_context = "objectmode"
	bl_region_type = "UI"
	bl_label = "Snow"
	bl_category = "Real Snow"

	def draw(self, context):
		scn = context.scene
		settings = scn.snow
		layout = self.layout

		col = layout.column(align=True)
		col.prop(settings, 'coverage', slider=True)
		col.prop(settings, 'height')
		
		layout.use_property_split = True
		layout.use_property_decorate = False
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=True)
		col = flow.column()
		col.prop(settings, 'vertices')
		
		row = layout.row(align=True)
		row.scale_y = 1.5
		row.operator("snow.create", text="Add Snow", icon="FREEZE")


class SNOW_OT_Create(Operator):
	bl_idname = "snow.create"
	bl_label = "Create Snow"
	bl_description = "Create snow"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		coverage = context.scene.snow.coverage
		height = context.scene.snow.height
		vertices = context.scene.snow.vertices
		
		if (context.selected_objects):
			# get list of selected objects except non-mesh objects
			snow_objects = [o for o in context.selected_objects if o.type == 'MESH']
			snow_list = []
			# start progress bar
			lenght = len(snow_objects)
			context.window_manager.progress_begin(0, 10)
			timer=0
			for o in snow_objects:
				# timer
				context.window_manager.progress_update(timer)
				# duplicate mesh
				bpy.ops.object.select_all(action='DESELECT')
				o.select_set(True)
				context.view_layer.objects.active = o
				new_o = o.copy()
				new_o.data = o.data.copy()
				context.collection.objects.link(new_o)
				bpy.ops.object.select_all(action='DESELECT')
				context.view_layer.objects.active = new_o
				new_o.select_set(True)
				# apply modifiers
				bpy.ops.object.convert(target='MESH')
				# get faces data
				bpy.ops.object.mode_set(mode = 'EDIT')
				bm_orig = bmesh.from_edit_mesh(new_o.data)
				bm = bm_orig.copy()
				bm.transform(o.matrix_world)
				bm.normal_update()
				# find upper faces
				if vertices:
					selected_faces = [f.index for f in bm.faces if f.select]
				down_faces = [e.index for e in bm.faces if Vector((0, 0, -1.0)).angle(e.normal, 4.0) < (math.pi/2.0+0.5)]
				bm.free()
				bpy.ops.mesh.select_all(action='DESELECT')
				# select upper faces
				mesh = bmesh.from_edit_mesh(new_o.data)
				for f in mesh.faces:
					if vertices:
						if not f.index in selected_faces:
							f.select = True
					if f.index in down_faces:
						f.select = True
				# delete unneccessary faces
				faces_select = [f for f in mesh.faces if f.select]
				bmesh.ops.delete(mesh, geom=faces_select, context='FACES_KEEP_BOUNDARY')
				mesh.free()
				bpy.ops.object.mode_set(mode = 'OBJECT')
				# add metaball
				ball = bpy.data.metaballs.new("SnowBall")
				ballobj = bpy.data.objects.new("SnowBall", ball)
				bpy.context.scene.collection.objects.link(ballobj)
				ball.resolution = 0.7*height+0.3
				ball.threshold = 1.3
				element = ball.elements.new()
				element.radius = 1.5
				element.stiffness = 0.75
				ballobj.scale = [0.09, 0.09, 0.09]
				context.view_layer.objects.active = new_o
				a = area(new_o)
				# add particles
				number = int(a*50*(height**-2)*((coverage/100)**2))
				bpy.ops.object.particle_system_add()
				particles = new_o.particle_systems[0]
				psettings = particles.settings
				psettings.type = 'HAIR'
				psettings.render_type = 'OBJECT'
				# generate random number for seed
				random_seed = randint(0, 1000)
				particles.seed = random_seed
				# set particles object
				psettings.particle_size = height
				psettings.instance_object = ballobj
				psettings.count = number
				# convert particles to mesh
				bpy.ops.object.select_all(action='DESELECT')
				context.view_layer.objects.active = ballobj
				ballobj.select_set(True)
				bpy.ops.object.convert(target='MESH')
				snow = bpy.context.active_object
				snow.scale = [0.09, 0.09, 0.09]
				bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
				bpy.ops.object.select_all(action='DESELECT')
				new_o.select_set(True)
				bpy.ops.object.delete()
				snow.select_set(True)
				# add modifier
				bpy.ops.object.transform_apply(location=False, scale=True, rotation=False)
				snow.modifiers.new("Decimate", 'DECIMATE')
				snow.modifiers["Decimate"].ratio = 0.5
				snow.modifiers.new("Subdiv", "SUBSURF")
				snow.modifiers["Subdiv"].render_levels = 1
				snow.modifiers["Subdiv"].quality = 1
				snow.cycles.use_adaptive_subdivision = True
				# place inside collection
				context.view_layer.active_layer_collection = context.view_layer.layer_collection
				if not "Snow" in context.scene.collection.children:
					coll = bpy.data.collections.new("Snow")
					context.scene.collection.children.link(coll)
				else:
					coll = bpy.data.collections["Snow"]
				coll.objects.link(snow)
				context.view_layer.layer_collection.collection.objects.unlink(snow)
				# add snow material
				add_material(snow)
				# parent with object
				snow.parent = o
				snow.matrix_parent_inverse = o.matrix_world.inverted()
				# add snow to list
				snow_list.append(snow)
				# update progress bar
				timer=timer+((100/lenght)/1000)
			# select created snow
			for s in snow_list:
				s.select_set(True)
			# end progress bar
			context.window_manager.progress_end()

		return {'FINISHED'}


def area(obj):
	bm = bmesh.new()
	bm.from_mesh(obj.data)
	bm.transform(obj.matrix_world)
	area = sum(f.calc_area() for f in bm.faces)
	bm.free
	return area


def add_material(obj):
	mat_name = "Snow"
	# if material doesn't exist, create it
	if mat_name in bpy.data.materials:
		bpy.data.materials[mat_name].name = mat_name+".001"
	mat = bpy.data.materials.new(mat_name)
	mat.use_nodes = True
	nodes = mat.node_tree.nodes
	# delete all nodes
	for node in nodes:
		nodes.remove(node)
	# add nodes
	output = nodes.new('ShaderNodeOutputMaterial')
	principled = nodes.new('ShaderNodeBsdfPrincipled')
	vec_math = nodes.new('ShaderNodeVectorMath')
	com_xyz = nodes.new('ShaderNodeCombineXYZ')
	dis = nodes.new('ShaderNodeDisplacement')
	mul1 = nodes.new('ShaderNodeMath')
	add1 = nodes.new('ShaderNodeMath')
	add2 = nodes.new('ShaderNodeMath')
	mul2 = nodes.new('ShaderNodeMath')
	mul3 = nodes.new('ShaderNodeMath')
	ramp1 = nodes.new('ShaderNodeValToRGB')
	ramp2 = nodes.new('ShaderNodeValToRGB')
	ramp3 = nodes.new('ShaderNodeValToRGB')
	vor = nodes.new('ShaderNodeTexVoronoi')
	noise1 = nodes.new('ShaderNodeTexNoise')
	noise2 = nodes.new('ShaderNodeTexNoise')
	noise3 = nodes.new('ShaderNodeTexNoise')
	mapping = nodes.new('ShaderNodeMapping')
	coord = nodes.new('ShaderNodeTexCoord')
	# change location
	output.location = (100, 0)
	principled.location = (-200, 500)
	vec_math.location = (-400, 400)
	com_xyz.location = (-600, 400)
	dis.location = (-200, -100)
	mul1.location = (-400, -100)
	add1.location = (-600, -100)
	add2.location = (-800, -100)
	mul2.location = (-1000, -100)
	mul3.location = (-1000, -300)
	ramp1.location = (-500, 150)
	ramp2.location = (-1300, -300)
	ramp3.location = (-1000, -500)
	vor.location = (-1500, 200)
	noise1.location = (-1500, 0)
	noise2.location = (-1500, -200)
	noise3.location = (-1500, -400)
	mapping.location = (-1700, 0)
	coord.location = (-1900, 0)
	# change node parameters
	principled.distribution = "MULTI_GGX"
	principled.subsurface_method = "RANDOM_WALK"
	principled.inputs[0].default_value[0] = 0.904
	principled.inputs[0].default_value[1] = 0.904
	principled.inputs[0].default_value[2] = 0.904
	principled.inputs[1].default_value = 1
	principled.inputs[2].default_value[0] = 0.36
	principled.inputs[2].default_value[1] = 0.46
	principled.inputs[2].default_value[2] = 0.6
	principled.inputs[3].default_value[0] = 0.904
	principled.inputs[3].default_value[1] = 0.904
	principled.inputs[3].default_value[2] = 0.904
	principled.inputs[5].default_value = 0.224
	principled.inputs[7].default_value = 0.1
	principled.inputs[13].default_value = 0.1
	vec_math.operation = "MULTIPLY"
	vec_math.inputs[1].default_value[0] = 0.5
	vec_math.inputs[1].default_value[1] = 0.5
	vec_math.inputs[1].default_value[2] = 0.5
	com_xyz.inputs[0].default_value = 0.36
	com_xyz.inputs[1].default_value = 0.46
	com_xyz.inputs[2].default_value = 0.6
	dis.inputs[1].default_value = 0.1
	dis.inputs[2].default_value = 0.3
	mul1.operation = "MULTIPLY"
	mul1.inputs[1].default_value = 0.1
	mul2.operation = "MULTIPLY"
	mul2.inputs[1].default_value = 0.6
	mul3.operation = "MULTIPLY"
	mul3.inputs[1].default_value = 0.4
	ramp1.color_ramp.elements[0].position = 0.525
	ramp1.color_ramp.elements[1].position = 0.58
	ramp2.color_ramp.elements[0].position = 0.069
	ramp2.color_ramp.elements[1].position = 0.757
	ramp3.color_ramp.elements[0].position = 0.069
	ramp3.color_ramp.elements[1].position = 0.757
	vor.feature = "N_SPHERE_RADIUS"
	vor.inputs[2].default_value = 30
	noise1.inputs[2].default_value = 12
	noise2.inputs[2].default_value = 2
	noise2.inputs[3].default_value = 4
	noise3.inputs[2].default_value = 1
	noise3.inputs[3].default_value = 4
	mapping.inputs[3].default_value[0] = 12
	mapping.inputs[3].default_value[1] = 12
	mapping.inputs[3].default_value[2] = 12
	# link nodes
	link = mat.node_tree.links
	link.new(principled.outputs[0], output.inputs[0])
	link.new(vec_math.outputs[0], principled.inputs[2])
	link.new(com_xyz.outputs[0], vec_math.inputs[0])
	link.new(dis.outputs[0], output.inputs[2])
	link.new(mul1.outputs[0], dis.inputs[0])
	link.new(add1.outputs[0], mul1.inputs[0])
	link.new(add2.outputs[0], add1.inputs[0])
	link.new(mul2.outputs[0], add2.inputs[0])
	link.new(mul3.outputs[0], add2.inputs[1])
	link.new(ramp1.outputs[0], principled.inputs[12])
	link.new(ramp2.outputs[0], mul3.inputs[0])
	link.new(ramp3.outputs[0], add1.inputs[1])
	link.new(vor.outputs[4], ramp1.inputs[0])
	link.new(noise1.outputs[0], mul2.inputs[0])
	link.new(noise2.outputs[0], ramp2.inputs[0])
	link.new(noise3.outputs[0], ramp3.inputs[0])
	link.new(mapping.outputs[0], vor.inputs[0])
	link.new(mapping.outputs[0], noise1.inputs[0])
	link.new(mapping.outputs[0], noise2.inputs[0])
	link.new(mapping.outputs[0], noise3.inputs[0])
	link.new(coord.outputs[3], mapping.inputs[0])
	
	# set displacement and add material
	mat.cycles.displacement_method = "DISPLACEMENT"
	obj.data.materials.append(mat)


# Properties
class SnowSettings(PropertyGroup):
	coverage : bpy.props.IntProperty(
		name = "Coverage",
		description = "Percentage of the object to be covered with snow",
		default = 100,
		min = 0,
		max = 100,
		subtype = 'PERCENTAGE'
		)

	height : bpy.props.FloatProperty(
		name = "Height",
		description = "Height of the snow",
		default = 0.3,
		step = 1,
		precision = 2,
		min = 0.1,
		max = 1
		)

	vertices : bpy.props.BoolProperty(
		name = "Selected Faces",
		description = "Add snow only on selected faces",
		default = False
		)


#############################################################################################
classes = (
	REAL_PT_snow,
	SNOW_OT_Create,
	SnowSettings
	)

register, unregister = bpy.utils.register_classes_factory(classes)

# Register
def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Scene.snow = bpy.props.PointerProperty(type=SnowSettings)


# Unregister
def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)
	del bpy.types.Scene.snow


if __name__ == "__main__":
	register()
