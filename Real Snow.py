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
from bpy.props import *
from random import randint
from bpy.types import Panel, Operator, PropertyGroup
from mathutils import Vector


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
			for o in context.selected_objects:
				bpy.ops.object.select_all(action='DESELECT')
				o.select_set(True)
				context.view_layer.objects.active = o
				bpy.ops.object.duplicate()
				obj1 = context.active_object
				bpy.ops.object.duplicate()
				obj2 = context.active_object
				bpy.ops.object.select_all(action='DESELECT')
				obj1.select_set(True)
				bpy.ops.object.mode_set(mode = 'EDIT')
				me = obj2.data
				bm_orig = bmesh.from_edit_mesh(me)
				bm = bm_orig.copy()
				bm.transform(o.matrix_world)
				bm.normal_update()
				fo = [ele.index for ele in bm.faces if Vector((0, 0, -1.0)).angle(ele.normal, 4.0) < (math.pi/2.0+0.5)]
				bpy.ops.mesh.select_all(action='DESELECT')
				obj_e = bpy.context.edit_object
				
				for i in fo:
					mesh = bmesh.from_edit_mesh(obj_e.data)
					for fm in mesh.faces:
						if (fm.index == i):
							fm.select = True
					bmesh.update_edit_mesh(obj_e.data, True)
				
				bme = bmesh.from_edit_mesh(obj_e.data)
				faces_select = [f for f in bme.faces if f.select]
				bmesh.ops.delete(bme, geom=faces_select, context='FACES_KEEP_BOUNDARY')
				bmesh.update_edit_mesh(obj_e.data, True)
				bpy.ops.object.mode_set(mode = 'OBJECT')
				ball = bpy.data.metaballs.new("Snow Ball")
				ballobj = bpy.data.objects.new("Snow Ball Object", ball)
				bpy.context.scene.collection.objects.link(ballobj)
				ball.resolution = height
				ball.threshold = 1.3
				element = ball.elements.new()
				element.radius = 1.5
				element.stiffness = 0.75
				ballobj.scale = [0.09, 0.09, 0.09]
				context.view_layer.objects.active = obj2
				a = area(obj2)
				number = a*100*(height**-1.5)*(coverage/100)
				print(number)
				bpy.ops.object.particle_system_add()
				particles = obj2.particle_systems[0]
				particles.name = 'Snow'
				psettings = particles.settings
				psettings.type = 'HAIR'
				psettings.name = 'Snow'
				psettings.render_type = 'OBJECT'
				psettings.instance_object = ballobj
				psettings.particle_size = height
				psettings.count = number
				# generate random number for seed
				random_seed = randint(0, 1000)
				particles.seed = random_seed
				bpy.ops.object.select_all(action='DESELECT')
				context.view_layer.objects.active = ballobj
				ballobj.select_set(True)
				bpy.ops.object.convert(target='MESH')
				snow = bpy.context.active_object
				snow.scale = [0.09, 0.09, 0.09]
				snow.select_set(True)
				bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
				bpy.ops.object.select_all(action='DESELECT')
				obj2.select_set(True)
				bpy.ops.object.particle_system_remove()
				bpy.ops.object.delete()
				bpy.ops.object.select_all(action='DESELECT')
				obj1.select_set(True)
				bpy.ops.object.delete()
				bpy.ops.object.select_all(action='DESELECT')
				snow.select_set(True)
				# add modifier
				snow.modifiers.new("Decimate", 'DECIMATE')
				snow.modifiers["Decimate"].ratio = 0.5

		return {'FINISHED'}


def area(obj):
	bm = bmesh.new()
	bm.from_mesh(obj.data)
	bm.transform(obj.matrix_world)
	area = sum(f.calc_area() for f in bm.faces)
	bm.free
	return area


# Properties
class SnowSettings(PropertyGroup):
	coverage : bpy.props.IntProperty(
		name = "Coverage",
		description = "Percentage of the object to be covered with snow",
		default = 50,
		min = 0,
		max = 100,
		subtype = 'PERCENTAGE'
		)

	height : bpy.props.FloatProperty(
		name = "Height",
		description = "Height of the snow",
		default = 0.3,
		min = 0,
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
