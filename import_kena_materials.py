from typing import List, Dict, Tuple
from bpy.types import Object, Material
import bpy, os, sys
from .props_txt_to_json import props_txt_to_json

EXTRACTED_FILES = "D:/3D/Kena/Extracted/Extracted_Rigs/"

def build_material_map(path_to_files: str) -> Dict[str, str]:
	"""
	The meshes imported by the .psk importer have materials named according to the
	material files (.props.txt) that were extracted by umodel.
	To match the material to the correct file quicker, we build a mapping from
	material name to filepath in one go.
	"""

	mat_map = {}

	for subdir, dirs, files in os.walk(abs_path_to_extracted_files):
		mat_files = [subdir + os.sep + f for f in files if f.endswith('.props.txt')]
		for mat_file in mat_files:
			mat_map[mat_file.replace(".props.txt", "")] = subdir + os.sep + mat_file

	return mat_files

def set_up_materials(obj: Object, mat_map: Dict[str, str]):
	"""Set up all materials of the object."""

	for ms in obj.material_slots:
		mat = ms.material
		if not mat:
			continue
		mat_file = mat_map.get(mat.name)
		if not mat_file:
			continue

		set_up_material

def set_up_material(obj: Object, mat: Material, mat_info):
	"""Set up a single material."""
	pass

props_txt_to_json(EXTRACTED_FILES + "Game/Mochi/Characters/Kena/Materials/Standard/MI_KenaHair.props.txt")