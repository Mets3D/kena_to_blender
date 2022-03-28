import bpy, os, shutil
from datetime import datetime

def is_psk(filename):
	return filename.endswith(".psk") or filename.endswith(".pskx")

def get_extract_path(context) -> str:
	addon_prefs = context.preferences.addons[__package__].preferences
	extract_path = addon_prefs.extract_path
	assert extract_path != 'D:\\Path_to_your_extract_folder\\', "Set your extract folder path in the addon prefs!"
	return extract_path

def delete_anim_uasset_files():
    bad_folders = []
    bad_files = []

    for subdir, dirs, files in os.walk("D:/3D/Kena/Extracted/Extracted_uasset/"):
        if "Animation" in subdir:
            bad.append(subdir)
        for f in files:
            if f.startswith("A_") or "Anim" in f:
                bad_files.append(subdir+os.sep+f)

    for b in bad_folders:
        try:
            shutil.rmtree(b)
            print("Nuked " + b)
        except Exception as e:
            pass

    for f in bad_files:
        os.remove(f)
        print("Deleted file: ", f)

def import_animations(folder: str):
	counter = 0

	for subdir, dirs, files in os.walk(folder):
		for file in files:
			if not file.endswith(".gltf"):
				continue
			if file.replace("out.gltf", "") in bpy.data.actions:
				continue
			print(file)
			bpy.ops.import_scene.gltf(filepath=subdir+os.sep+file)
			counter += 1
			for o in bpy.context.selected_objects[:]:
				bpy.data.objects.remove(o)

			action = bpy.data.actions.get('DefAnim_Armature.001') or bpy.data.actions.get('DefAnim_Armature.002') or bpy.data.actions.get('DefAnim_Armature.003') or bpy.data.actions.get('DefAnim_Armature.004')
			action.name = file.replace("out.gltf", "")
			action.use_fake_user = True
			bpy.ops.outliner.orphans_purge(do_recursive=True)
			if counter > 0:
				return

# import_animations("D:\\3D\\Kena\\Tools\\ACLAnimViewer_Kena\\Export\\SK_Kenaout")

def set_active_textures():
	for m in bpy.data.materials:
		for n in m.node_tree.nodes:
			if n.type=='GROUP':
				diffuse = n.inputs.get('Diffuse')
				if len(diffuse.links) > 0:
					from_node = diffuse.links[0].from_node
					m.node_tree.nodes.active = from_node
				else:
					print("No diffuse: ", m.name)

def compress_images():
	# Convert images to .jpg
	# Except .jpg doesn't have alpha channel, so if an image's Alpha is ever used, don't convert it.
	C = bpy.context
	C.scene.view_settings.view_transform = 'Standard'
	C.scene.view_settings.look = 'None'
	C.scene.view_settings.exposure = 0.0
	C.scene.view_settings.gamma = 1.0
	C.scene.render.image_settings.file_format = 'JPEG'

	images_with_alpha = []

	for o in bpy.data.objects:
		for ms in o.material_slots:
			if not ms.material.node_tree:
				# TODO: Who dis??
				continue
			for n in ms.material.node_tree.nodes:
				if n.type != 'TEX_IMAGE' or not n.image:
					continue
				if len(n.outputs[1].links) > 0:
					images_with_alpha.append(n.image.name)


	for i in bpy.data.images:
		if i.name == 'Transparent':
			continue
		if i.filepath.endswith(".jpg"):
			continue
		abs_path = bpy.path.abspath(i.filepath)
		new_rel_path = i.filepath.replace("//textures_ue", "//textures_compressed")
		new_abs_path = bpy.path.abspath(new_rel_path)
		jpg_abs_path = new_abs_path.replace(".tga", ".jpg")
		jpg_rel_path = new_rel_path.replace(".tga", ".jpg")
		if os.path.isfile(jpg_abs_path):
			if i.name in images_with_alpha:
				print("THIS SHOULD BE TGA", i.filepath)
			else:
				i.filepath = jpg_rel_path
				print("Already compressed, skipped: ", i.filepath)

		if i.name in images_with_alpha:
			if "textures_compressed" in i.filepath:
				continue
			# Just copy the file without compressing it.
			os.makedirs(os.path.dirname(new_abs_path), exist_ok=True)
			shutil.copy(abs_path, new_abs_path)
			i.filepath = new_rel_path
			print("Copied", new_abs_path)
		else:
			# Save as .jpg in the new location.
			i.save_render(filepath=jpg_abs_path)
			i.filepath = jpg_rel_path
			print("Compressed", jpg_abs_path)

def find_image_users(image_name):
	for o in bpy.data.objects:
		for ms in o.material_slots:
			m = ms.material
			if not m: continue
			if not m.node_tree or not m.node_tree.nodes: continue
			for n in m.node_tree.nodes:
				if not n.type == 'TEX_IMAGE' or not n.image:
					continue
				if n.image.name == image_name:
					print(o.name)
	
# find_image_users("")

def hookup_alphas():
	# doesn't work, over-eager, no way to make sure image actually has alpha.
	import bpy

	for m in bpy.data.materials:
		if not m.node_tree or not m.node_tree.nodes:
			continue
		ng = None
		for n in m.node_tree.nodes:
			if n.type == 'GROUP':
				ng = n
				break
		
		for n in m.node_tree.nodes:
			if n.type == 'TEX_IMAGE' and n.image and len(n.outputs[0].links) > 0:
				if n.outputs[0].links[0].to_socket.name == 'Diffuse' and len(ng.inputs['Alpha'].links) == 0 and n.image.depth == 32:
					m.node_tree.links.new(n.outputs[1], ng.inputs['Alpha'])
					print(m.name, n.image.name)

def copy_used_images(search_path, replace_path):
	for i in bpy.data.images:
		abspath = bpy.path.abspath(i.filepath)
		i.filepath = i.filepath.replace(search_path, replace_path)
		new_abspath = bpy.path.abspath(i.filepath)
		os.makedirs(os.path.dirname(new_abspath), exist_ok=True)
		shutil.copyfile(abspath, new_abspath)
		print(new_abspath)

class RenderCyclesThumbnail(bpy.types.Operator):
	bl_idname = 'view3d.render_cycles_thumbnail'
	bl_label = "Render Cycles Thumbnail"

	@classmethod
	def poll(cls, context):
		ob = context.object
		return ob and ob.type == 'MESH' and context.area.ui_type == 'VIEW_3D'

	def execute(self, context):
		ob = context.object
		
		filepath = "//..\\Thumbnails\\" + ob.name + ".png"
		abspath = bpy.path.abspath(filepath)

		if os.path.isfile(abspath):
			print("Overwriting: ", abspath)
			# TODO: Overwrite y/n?

		context.scene.render.filepath = filepath
		bpy.ops.render.render(use_viewport=True, write_still=True)
		context.scene.collection.objects.unlink(ob)
		bpy.ops.ed.lib_id_load_custom_preview({"id": ob}, filepath=abspath)

		return {'FINISHED'}

class Render_All_Cycles_Thumbnails(bpy.types.Operator):
	bl_idname = "view3d.render_all_cycles_thumbnails"
	bl_label = "Render All Cycles Thumbnails"

	def execute(self, context):
		ob_count = len(bpy.data.objects)
		for i, o in enumerate(bpy.data.objects):
			if o.type != 'MESH': continue
			filepath = "//..\\Thumbnails\\" + o.name + ".png"
			abspath = bpy.path.abspath(filepath)
			if os.path.isfile(abspath):
				continue
			now = datetime.now()
			print(f"{now.hour}:{now.minute}:{now.second} {o.name} {i}/{ob_count}")
			context.scene.collection.objects.link(o)
			o.hide_viewport = False
			o.select_set(True)
			context.view_layer.objects.active = o
			bpy.ops.view3d.view_selected()
			context.scene.render.filepath = filepath
			bpy.ops.render.render(use_viewport=True, write_still=True)
			o.hide_viewport = True
			context.scene.collection.objects.unlink(o)
			bpy.ops.ed.lib_id_load_custom_preview({"id": o}, filepath=abspath)
		return {'FINISHED'}

bpy.utils.register_class(Render_All_Cycles_Thumbnails)
bpy.utils.register_class(RenderCyclesThumbnail)