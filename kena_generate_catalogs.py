from typing import List, Dict

from bpy.types import Object, Collection, Operator
from bpy.props import StringProperty
import bpy, os
from uuid import uuid4
from .utils import get_extract_path, is_psk
from .batch_import_psk import import_kena_psk

ASSET_HEADER = """
# This is an Asset Catalog Definition file for Blender.
#
# Empty lines and lines starting with `#` will be ignored.
# The first non-ignored line should be the version indicator.
# Other lines are of the format "UUID:catalog/path/for/assets:simple catalog name"

VERSION 1

"""
ASSET_FILENAME = "blender_assets.cats.txt"

def generate_catalogs(context):
	"""Execute this funciton to generate the asset catalog .txt file based on
	the extracted game's folder hierarchy. (only for folders that contain .fbx)"""
	cats = folder_structure_to_catalogs(get_extract_path(context))
	asset_filepath = os.path.join(os.path.dirname(bpy.data.filepath), ASSET_FILENAME)
	asset_catalogue = ASSET_HEADER + "\n".join(cats)

	f = open(asset_filepath, 'w')
	f.write(asset_catalogue)
	f.close()

def folder_structure_to_catalogs(root_dir: str) -> List[str]:
	"""Generate the string of a catalog file, where each sub-folder of a directory is a catalog."""
	root_dir = os.path.abspath(root_dir)
	catalogs = {}	# simple-catalog-name : cat_def
	for subdir, dirs, files in os.walk(root_dir):
		if not has_psk_in_any_subfolder(subdir):
			continue

		catalog_path = subdir.replace(root_dir, "")[1:]
		name_chain = folder_path_to_catalog_name_chain(catalog_path)

		cat_def = name_chain_to_catalog_def(name_chain)
		if not cat_def:
			continue

		# Avoid duplicates.
		simple_name = cat_def.split(":")[2]
		if simple_name not in catalogs:
			catalogs[simple_name] = cat_def

	return list(catalogs.values())

def has_psk_in_any_subfolder(folder) -> bool:
	for subdir, dirs, files in os.walk(folder):
		for f in files:
			if is_psk(f):
				return True
	return False

def name_chain_to_catalog_def(name_chain: List[str]) -> str:
	if not name_chain:
		return
	cat_def = f"{str(uuid4())}:{'/'.join(name_chain)}:{'-'.join(name_chain)}"
	return cat_def

def folder_path_to_catalog_name_chain(folder_path: str):
	folders = folder_path.split(os.sep)
	return [f.replace("_", " ").title() for f in folders]

def read_catalogs() -> List[str]:
	"""Read and return the catalog definitions from the catalog .txt file."""
	asset_filepath = os.path.join(os.path.dirname(bpy.data.filepath), ASSET_FILENAME)
	contents = open(asset_filepath).read()
	cats = contents.split("\n")[8:]
	cats = [cat for cat in cats if cat] # Don't include empty lines.
	return cats

def get_catalog_of_folder(name_chain: List[str], cat_defs: List[str], subfolder: str):
	for cat_def in cat_defs:
		if "/".join(name_chain) == cat_def.split(":")[1]:
			return cat_def

def import_folders(context, name_chains: List[List[str]]=[]):
	"""Import a specific set of folders, or everything.
	Also create assets.
	w3_generate_catalogs.generate_catalogs() should be called first, to generate the asset catalog file.

	This function has no operator, it's to be called directly, eg., from a text editor.
	Have a console open, since importing everything could take many hours, or even a day.
	Memory requirement is not as bad as you'd think, but the import process will save the file pretty frequently.
	"""
	cat_defs = read_catalogs()
	extract_path = get_extract_path(context)

	finished = import_up_to_filesize(context, extract_path, cat_defs, name_chains)
	bpy.ops.wm.save_mainfile()
	print("Saved Blend file. Size: " + str(os.path.getsize(bpy.data.filepath)))

def import_up_to_filesize(context, extract_path, cat_defs, name_chains=[]):
	"""Import files from the extract path."""
	mem_bytes = 0
	cat_to_coll = map_catalogs_to_collections(context, cat_defs, extract_path)

	file_count = 0

	for subdir, dirs, files in os.walk(extract_path):
		# Find catalog definition for this subfolder...
		catalog_path = subdir.replace(extract_path, "")
		name_chain = folder_path_to_catalog_name_chain(catalog_path)
		if not name_chain:
			continue
		if not is_good_name_chain(name_chain, name_chains):
			continue
		cat_def = get_catalog_of_folder(name_chain, cat_defs, subdir.replace(extract_path, ""))
		if not cat_def:
			continue

		# Find collection of catalog...
		coll = cat_to_coll[cat_def]

		# Import the stuff.
		for filename in files:
			if not is_psk(filename):
				continue
			filepath = os.path.join(subdir, filename)
			objs = import_kena_psk(context, filepath)
			file_count += 1
			path_from_uncook = filepath.replace(extract_path, "")
			mem_bytes += os.path.getsize(filepath)

			bpy.ops.object.select_all(action='DESELECT')
			for o in objs:
				set_up_asset(o, coll, cat_def.split(":")[0], path_from_uncook)
				o.hide_viewport=True

def is_good_name_chain(name_chain: List[str], good_chains: List[List[str]]) -> bool:
	for good_chain in good_chains:
		match = True
		for name1, name2 in zip(good_chain, name_chain):
			if name1 != name2:
				match = False
		if match:
			return True
	return False

def ensure_coll_hierarchy(coll, coll_names: List[str]) -> Collection:
	"""Find a collection by a hierarchy, where the names don't have to be a perfect match."""

	if len(coll_names) == 0:
		# This is the only exit out of the recursion.
		return coll

	for child in coll.children:
		if coll_names[0] in child.name:
			return ensure_coll_hierarchy(child, coll_names[1:])

	# If the rest of the collections don't exist, let's create them.
	new_coll = bpy.data.collections.new(name=coll_names[0])
	coll.children.link(new_coll)
	return ensure_coll_hierarchy(new_coll, coll_names[1:])

def map_catalogs_to_collections(context
		,cat_defs: List[str]
		,uncook_path: str
	) -> Dict[str, Collection]:
	"""Create a mapping from catalogs to existing collections."""
	cat_to_coll = {}
	for cat_def in cat_defs:
		if not cat_def:
			continue
		coll_names = get_name_hierarchy_of_cat(cat_def)
		coll = ensure_coll_hierarchy(context.scene.collection, coll_names)
		cat_to_coll[cat_def] = coll

	return cat_to_coll

def get_name_hierarchy_of_cat(catalog_def: str) -> List[str]:
	spl = catalog_def.split(":")
	return spl[1].split("/")

def set_up_asset(o: Object, coll: Collection, cat_id: str, description: str):
	for c in o.users_collection:
		c.objects.unlink(o)
	coll.objects.link(o)
	if o.type == 'MESH':
		o.select_set(True)
		asset_data = generate_asset(o)
		asset_data.catalog_id = cat_id
		if len(o.modifiers) > 0:
			asset_data.tags.new('Animated')
		else:
			asset_data.tags.new('Static')
		asset_data.description = description
		asset_data.author = "Ember Labs"
		for ms in o.material_slots:
			if not ms.material:
				continue
			m = ms.material
			asset_data.tags.new(m.name)
			if not m.node_tree:
				continue
			for n in reversed(m.node_tree.nodes):
				if n.type == 'GROUP':
					if asset_data.tags.find(n.label) == -1:
						asset_data.tags.new(n.label)
					break

def generate_asset(o):
	if o.asset_data:
		return o.asset_data
	o.asset_mark()
	o.asset_generate_preview()
	return o.asset_data

class OBJECT_OT_reload_kena_asset(Operator):
	"""Re-import Kena asset"""
	bl_idname = "object.reload_kena_asset"
	bl_label = "Reload Kena Asset"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	ob_name: StringProperty()
	filepath: StringProperty()

	def execute(self, context):
		# Find and delete the object
		if context.object:
			bpy.ops.object.mode_set(mode='OBJECT')
		bpy.ops.object.select_all(action='DESELECT')

		ob = bpy.data.objects.get(self.ob_name)

		cat_id = ob.asset_data.catalog_id
		coll = ob.users_collection[0]
		description = ob.asset_data.description

		if not ob:
			return {'CANCELLED'}
		if ob.parent and len(ob.parent.children) == 1:
			bpy.data.objects.remove(ob.parent)
		bpy.data.objects.remove(ob)

		full_path = os.path.join(get_extract_path(context), self.filepath)
		import_kena_psk(context, full_path, do_clean_mesh=True)

		new_ob = bpy.data.objects.get(self.ob_name)
		set_up_asset(new_ob, coll, cat_id, description)
		context.view_layer.objects.active = new_ob

		return {'FINISHED'}

def context_menu_draw_kena(self, context):
	"""Add a button to the asset browser context menu"""
	layout = self.layout
	asset_data = context.asset_file_handle.asset_data
	ob_name = asset_data.id_data.name
	if asset_data.author == 'Ember Labs':
		op = layout.operator('object.reload_kena_asset', icon='FILE_REFRESH')
		op.ob_name = ob_name
		op.filepath = asset_data.description

registry = [
	OBJECT_OT_reload_kena_asset
]

def register():
	bpy.types.ASSETBROWSER_MT_context_menu.append(context_menu_draw_kena)

def unregister():
	bpy.types.ASSETBROWSER_MT_context_menu.remove(context_menu_draw_kena)
