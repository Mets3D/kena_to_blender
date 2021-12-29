from typing import List
from bpy.types import Object
import bpy, os, sys
from datetime import datetime

RIG_FILES = "D:/3D/Kena/Extracted/Extracted_Rigs/Game/Mochi/Characters/"

def is_psk(filename):
	return filename.endswith(".psk") or filename.endswith(".pskx")

def get_object_name_list():
	return [o.name for o in bpy.data.objects]

def get_new_objects(old_name_list: List[str]) -> List[Object]:
	return [o for o in bpy.data.objects if o.name not in old_name_list]

def enable_print(bool):
	"""For suppressing prints from fbx importer and remove_doubles()."""
	if not bool:
		sys.stdout = open(os.devnull, 'w')
	else:
		sys.stdout = sys.__stdout__

def import_psk_files(psk_files: List[str]) -> List[Object]:
	objects = []
	for full_path in psk_files:
		print(full_path)
		ob_list = get_object_name_list()
		enable_print(False)
		bpy.ops.import_scene.psk(filepath=full_path)
		enable_print(True)
		new_obs = get_new_objects(ob_list)
		for o in new_obs:
			o.name = o.name.replace(".mo", "").replace(".ao", "_Skeleton").replace("SK_", "")
			o.data.name = o.name

		now = datetime.now().strftime("%H:%M:%S")
		print(f"{now} Imported: " + str([o.name for o in new_obs]))
		objects.extend(new_obs)
	return objects

def batch_import_psk(context, abs_path_to_extracted_files: str):
	"""
	We extract the rigs from the game using umodel_kena.exe into .psk files. (.psk over .gltf because the gltf skeletons aren't compatible with the game's animations.)
		(umodel_kena_extract_morphs.exe works for everyone except Kena, her skeleton gets butchered.)
		Forum link: https://www.gildor.org/smf/index.php/topic,7922.0.html
		Direct link: https://drive.google.com/file/d/1rGoBufCGKWe3_aPp1XcxvOBM_GLbrv1B/view
	We import these with the .psk importer addon.
		Repo: https://github.com/Befzz/blender3d_import_psk_psa
	Then we use this function to batch import those .psk/pskx files.
	"""
	for subdir, dirs, files in os.walk(abs_path_to_extracted_files):
		psk_files = [subdir + os.sep + f for f in files if is_psk(f)]
		if not psk_files:
			continue

		objects = import_psk_files(psk_files)

def batch_import_psk_WITH_MORPHS(context, abs_path_to_extracted_files: str):
	"""
	We extract the morphs from the game using umodel_kena_morphs_export.exe into .psk files.
		Forum link: https://www.gildor.org/smf/index.php/topic,7922.0.html
		Direct link: https://drive.google.com/file/d/1rGoBufCGKWe3_aPp1XcxvOBM_GLbrv1B/view
	We import these with the .psk importer addon.
		Repo: https://github.com/Befzz/blender3d_import_psk_psa
	Then we use this function to batch import those .psk/pskx files, 
	and merge the morphs into shape keys on a single object.

	"""
	for subdir, dirs, files in os.walk(abs_path_to_extracted_files):
		psk_files = [subdir + os.sep + f for f in files if is_psk(f)]
		if not psk_files:
			continue

		any_morphs = False
		for filename in psk_files:
			if "Morph" in filename:
				any_morphs = True
				break
		if not any_morphs:
			continue

		objects = import_psk_files(psk_files)
		combine_morphs(context, objects)

def combine_morphs(context, objects: List[Object]):
	"""
	objects is expected to be a list of imported armatures and meshes.
	Only one of the meshes doesn't have "Morph" in the name, that will be the target.
	All objects except this one and its parent (the armature) will be deleted.
	"""
	bpy.ops.object.select_all(action='DESELECT')
	for o in objects[:]:
		if o.type!='MESH':
			continue
		o.select_set(True)
		if "Morph" not in o.name:
			context.view_layer.objects.active = o
			objects.remove(o)
			objects.remove(o.parent)
		else:
			parts = o.name.split("_")
			for i, part in enumerate(parts):
				if "Morph" in part:
					# Discard parts of the name up to and including "Morph"
					parts = parts[i+1:]
					break
			o.name = "_".join(parts)

	bpy.ops.object.join_shapes()
	for o in objects[:]:
		bpy.data.objects.remove(o)

	bpy.ops.outliner.orphans_purge(do_recursive=True)

batch_import_psk(bpy.context, RIG_FILES)