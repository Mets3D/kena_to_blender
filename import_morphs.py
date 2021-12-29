# We extract the morphs from the game using umodel_kena_morphs_export.exe into .psk files.
	# Forum link: https://www.gildor.org/smf/index.php/topic,7922.0.html
	# Direct link: https://drive.google.com/file/d/1rGoBufCGKWe3_aPp1XcxvOBM_GLbrv1B/view
# We import these with the .psk importer addon.
	# Repo: https://github.com/Befzz/blender3d_import_psk_psa
# Then we use the script below to batch import those .psk/pskx files, 
# and merge the morphs into shape keys on a single object.

from typing import List
from bpy.types import Object
import bpy, os, sys

PATH_TO_MORPHS = os.path.abspath("D:/3D/Kena/Extracted/Extracted_Morphs/Game/Mochi/Characters/HeroRot/Skeletal/")

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

def batch_import_morph_psk(context):
	for subdir, dirs, files in os.walk(PATH_TO_MORPHS):
		psk_files = [f for f in files if is_psk(f)]
		if not psk_files:
			continue

		psk_files = psk_files[:3]

		objects = []
		for filename in psk_files:
			full_path = subdir + os.sep + filename
			print(full_path)
			ob_list = get_object_name_list()
			enable_print(False)
			bpy.ops.import_scene.psk(filepath=full_path)
			enable_print(True)
			new_obs = get_new_objects(ob_list)
			for o in new_obs:
				o.name = o.name.replace(".mo", "").replace(".ao", "_Skeleton").replace("SK_", "")
				o.data.name = o.name
			print("Imported: " + str([o.name for o in new_obs]))
			objects.extend(new_obs)
		
		combine_morphs(objects)

def combine_morphs(objects: List[Object]):
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

batch_import_morph_psk(bpy.context)