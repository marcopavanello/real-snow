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
		
		if (context.selected_objects):
			# start progress bar
			lenght = len(context.selected_objects)
			context.window_manager.progress_begin(0, 10)
			timer=0
			for o in context.selected_objects:
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
				fo = [ele.index for ele in bm.faces if Vector((0, 0, -1.0)).angle(ele.normal, 4.0) < (math.pi/2.0+0.5)]
				bpy.ops.mesh.select_all(action='DESELECT')
				bm.free()
				# select upper faces
				for i in fo:
					mesh = bmesh.from_edit_mesh(new_o.data)
					for fm in mesh.faces:
						if (fm.index == i):
							fm.select = True
				# delete unneccessary faces
				if fo:
					faces_select = [f for f in mesh.faces if f.select]
					bmesh.ops.delete(mesh, geom=faces_select, context='FACES_KEEP_BOUNDARY')
					mesh.free()
				bpy.ops.object.mode_set(mode = 'OBJECT')
				# add metaball
				ball = bpy.data.metaballs.new("Snow")
				ballobj = bpy.data.objects.new("Snow", ball)
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
				# update progress bar
				timer=timer+((100/lenght)/1000)
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
	path = os.path.join(os.path.dirname(__file__), "Snow.blend")
	if "Snow" in bpy.data.materials:
		bpy.data.materials["Snow"].name = "Snow.001"
	with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
		data_to.materials = ["Snow"]
	mat = bpy.data.materials["Snow"]
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
