import bpy, os, shutil

def is_psk(filename):
	return filename.endswith(".psk") or filename.endswith(".pskx")

def get_extract_path(context) -> str:
	addon_prefs = context.preferences.addons[__package__].preferences
	extract_path = addon_prefs.extract_path
	assert extract_path != 'D:\\Path_to_your_extract_folder\\', "Set your extract folder path in the addon prefs!"
	return extract_path

def delete_anim_uasset_files():
    import os, shutil

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