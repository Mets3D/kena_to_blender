import bpy
from bpy.types import Operator, Object
from bpy.props import BoolProperty
from math import pi
from mathutils import Vector
import bmesh
from typing import List

def cleanup_mesh(context
		,obj: Object
		,*
		,remove_doubles = False
		,quadrangulate = False
		,weight_normals = True
		,seams_from_islands = True
		,clear_unused_UVs = True
		,rename_single_UV = True
	):

	if len(obj.data.vertices) == 0:
		return

	# Mode management
	org_active = context.object
	org_mode = 'OBJECT'
	org_selected = context.selected_objects[:]
	if org_active:
		org_mode = org_active.mode
		bpy.ops.object.mode_set(mode='OBJECT')

	bpy.ops.object.select_all(action='DESELECT')
	context.view_layer.objects.active = obj
	bpy.ops.object.mode_set(mode='EDIT')
	bpy.ops.mesh.select_all(action='SELECT')

	# Setting auto-smooth to 180 is necessary so that splitnormals_clear() doesn't mark sharp edges
	obj.data.use_auto_smooth = True
	obj.data.auto_smooth_angle = pi
	bpy.ops.mesh.customdata_custom_splitnormals_clear()

	if remove_doubles:
		bpy.ops.mesh.remove_doubles(threshold=0.00001)
		bpy.ops.mesh.mark_sharp(clear=True)

	if quadrangulate:
		bpy.ops.mesh.tris_convert_to_quads(uvs=True, materials=True)

	bpy.ops.object.mode_set(mode='OBJECT')
	context.view_layer.objects.active = obj
	bpy.ops.object.mode_set(mode='EDIT')

	### Removing useless UVMaps
	mesh = obj.data
	if clear_unused_UVs:
		bm = bmesh.from_edit_mesh(mesh)

		for uv_idx in reversed(range(0, len(mesh.uv_layers))):			# For each UV layer
			delet_this = True
			mesh.uv_layers.active_index = uv_idx
			bm.faces.ensure_lookup_table()
			for face in bm.faces:
				for loop in face.loops: 	# No idea what "loops" are.
					loop_on_active = loop[bm.loops.layers.uv.active]
					if loop_on_active.uv != Vector((0.0, 1.0)):	# If the X or Y of the the loop's UVs first vert is NOT 0
						delet_this = False
						break
				if not delet_this:
					break
			if delet_this:
				obj.data.uv_layers.remove(obj.data.uv_layers[uv_idx])

		bmesh.update_edit_mesh(mesh, loop_triangles=True)

	# Renaming single UV maps
	if len(mesh.uv_layers) == 1 and rename_single_UV:
		mesh.uv_layers[0].name = 'UVMap'

	# Seams from islands
	if seams_from_islands and len(mesh.uv_layers) > 0:
		context.scene.tool_settings.use_uv_select_sync = True
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)

	# Mark Sharp
	bpy.ops.mesh.select_all(action='DESELECT')
	bpy.ops.mesh.select_mode(type='EDGE')
	bpy.ops.mesh.edges_select_sharp(sharpness=(pi/2)-0.01)
	bpy.ops.mesh.mark_sharp()
	bpy.ops.mesh.select_all(action='DESELECT')

	bpy.ops.object.mode_set(mode='OBJECT')
	
	# Weight normals only works with remove doubles, otherwise throws ZeroDivisionError.
	# It also has to come AFTER Mark Sharp for correct results.
	if weight_normals and remove_doubles:
		m = obj.modifiers.new(name='WN', type='WEIGHTED_NORMAL')
		m.keep_sharp = True
		bpy.ops.object.modifier_apply(modifier='WN')

	# Mode management
	for o in org_selected:
		o.select_set(True)

	if org_active:
		context.view_layer.objects.active = org_active

	bpy.ops.object.mode_set(mode=org_mode)

class OBJECT_OT_clean_up_game_mesh(Operator):
	"""Clean up meshes imported from games"""
	bl_idname = "object.mesh_cleanup"
	bl_label = "Clean Up Mesh"
	bl_options = {'REGISTER', 'UNDO'}

	remove_doubles: BoolProperty(
		name="Remove Doubles",
		description="Enable remove doubles",
		default=False
	)

	quadrangulate: BoolProperty(
		name="Tris to Quads",
		description="Enable Tris to Quads (UV Seams enabledd)",
		default=False
	)

	weight_normals: BoolProperty(
		name="Weight Normals",
		description="Enable weighted normals",
		default=False
	)

	seams_from_islands: BoolProperty(
		name="Seams from Islands",
		description="Create UV seams based on UV islands",
		default=False
	)

	clear_unused_UVs: BoolProperty(
		name="Delete Unused UV Maps",
		description="If all UV verts' X coordinate is 0, the UV map will be deleted.",
		default=True
	)

	rename_single_UV: BoolProperty(
		name="Rename Singular UV Maps",
		description="If an object is only left with one UV map, rename it to the default name, 'UVMap'.",
		default=True
	)

	def execute(self, context):
		for o in context.selected_objects:
			cleanup_mesh(context, o,
				remove_doubles = self.remove_doubles,
				quadrangulate = self.quadrangulate,
				weight_normals = self.weight_normals,
				seams_from_islands = self.seams_from_islands,
				clear_unused_UVs = self.clear_unused_UVs,
				rename_single_UV = self.rename_single_UV)
		return {'FINISHED'}

def delete_mesh_with_bad_materials(context, obj: Object, bad_mats: List[str]):
	# Object should be selected and active.

	# Find indicies of bad materials.
	bad_mat_idxs = []
	for i, ms in enumerate(obj.material_slots):
		if ms.material and ms.material.name in bad_mats:
			bad_mat_idxs.append(i)
	if not bad_mat_idxs:
		return

	# Delete the geometry assigned to the bad materials.
	bpy.ops.object.select_all(action='DESELECT')
	context.view_layer.objects.active = obj
	obj.select_set(True)
	bpy.ops.object.mode_set(mode='EDIT')
	bpy.ops.mesh.select_all(action='DESELECT')
	for i in bad_mat_idxs:
		obj.active_material_index = i
		bpy.ops.object.material_slot_select()
		bpy.ops.mesh.delete(type='VERT')
	bpy.ops.object.mode_set(mode='OBJECT')

	# Remove the material slot.
	for i in reversed(bad_mat_idxs):
		obj.active_material_index = i
		bpy.ops.object.material_slot_remove()

registry = [
	OBJECT_OT_clean_up_game_mesh
]
