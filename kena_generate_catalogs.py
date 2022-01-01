from typing import List

import bpy, os
from uuid import uuid4
from .utils import get_extract_path, is_psk

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

		folders = catalog_path.split(os.sep)

		name_chain = [f.replace("_", " ").title() for f in folders]
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