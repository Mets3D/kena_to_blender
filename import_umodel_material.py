from typing import List, Dict, Tuple
from bpy.types import Object, Material
import bpy, os, sys
from .props_txt_to_json import props_txt_to_dict

def build_material_map(path_to_files: str) -> Dict[str, str]:
	"""
	The meshes imported by the .psk importer have materials named according to the
	material files (.props.txt) that were extracted by umodel.
	To match the material to the correct file quicker, we build a mapping from
	material name to filepath in one go.
	"""

	# NOTE: This currently catches .props.txt files that are for meshes, not materials, 
	# but it shouldn't cause any problems because there shouldn't be a name overlap...

	mat_map = {}

	for subdir, dirs, files in os.walk(path_to_files):
		mat_files = [f for f in files if f.endswith('.props.txt')]
		for mat_file in mat_files:
			mat_map[mat_file.replace(".props.txt", "")] = subdir + os.sep + mat_file

	return mat_map

def set_up_materials(obj: Object, mat_map: Dict[str, str]):
	"""Set up all materials of the object."""

	for ms in obj.material_slots:
		mat = ms.material
		if not mat:
			continue
		mat_file = mat_map.get(mat.name)
		if not mat_file:
			continue

		mat_info = props_txt_to_dict(mat_file)

		set_up_material(obj, mat, mat_info)
		break

def set_up_material(obj: Object, mat: Material, mat_info: Dict):
	"""Set up a single material."""

	tex_params, vector_params, scalar_params = parse_mat_params(mat_info)

def do_master_params(mat_info):
	tex_pars = mat_info.get('CollectedTextureParameters')
	vec_pars = mat_info.get('CollectedVectorParameters')
	scal_pars = mat_info.get('CollectedScalarParameters')

	processed_tex = {}
	processed_vec = {}
	processed_scal = {}

	if tex_pars:
		for tex_param in tex_pars:
			name = tex_param.get("Name")
			value = tex_param.get("Texture")
			if not value:
				processed_tex[name] = None
				continue
			value = value.split("'")[1].split(".")[0] + ".tga"
			processed_tex[name] = value

	if vec_pars:
		for vec_param in vec_pars:
			name = vec_param.get("Name")
			value = vec_param.get("Value")
			value = [value['R'], value['G'], value['B'], value['A']]
			processed_vec[name] = value

	if scal_pars:
		for scalar_param in scal_pars:
			name = scalar_param.get("Name")
			value = scalar_param.get("Value")
			processed_scal[name] = value

	return processed_tex, processed_vec, processed_scal
	
def do_instance_params(mat_info):
	tex_pars = mat_info.get('TextureParameterValues')
	vec_pars = mat_info.get('VectorParameterValues')
	scal_pars = mat_info.get('ScalarParameterValues')

	processed_tex = {}
	processed_vec = {}
	processed_scal = {}

	if tex_pars:
		for tex_param in tex_pars:
			name = tex_param.get("ParameterInfo").get("Name")
			value = tex_param.get("ParameterValue")
			if not value:
				processed_tex[name] = None
				continue
			value = value.split("'")[1].split(".")[0] + ".tga"
			processed_tex[name] = value

	if vec_pars:
		for vec_param in vec_pars:
			name = vec_param.get("ParameterInfo").get("Name")
			value = vec_param.get("ParameterValue")
			value = [value['R'], value['G'], value['B'], value['A']]
			processed_vec[name] = value

	if scal_pars:
		for scalar_param in scal_pars:
			name = scalar_param.get("ParameterInfo").get("Name")
			value = scalar_param.get("ParameterValue")
			processed_scal[name] = value

	return processed_tex, processed_vec, processed_scal

def parse_mat_params(mat_info: Dict) -> Tuple[Dict, Dict, Dict]:
	tex_params = {}
	vector_params = {}
	scalar_params = {}

	if 'Parent' in mat_info:
		parent_filepath = mat_info['Parent'].split("'")[1].split(".")[0]
		parent_filepath = get_extract_path(bpy.context) + os.sep + parent_filepath + ".props.txt"

		# Parse Master Material. 
		# These contain the list of parameters and their default values, which Material Instances are able to overwrite,
		# So we first load the master material's data into a dictionary, which can later be overwritten by the info in the MaterialInstance.

		master_mat_info = props_txt_to_dict(parent_filepath)
		tex_params, vector_params, scalar_params = do_master_params(mat_info = master_mat_info)

	# Material Instance parameters
	mi_tex_params, mi_vec_params, mi_scal_params = do_instance_params(mat_info = mat_info)

	tex_params.update(mi_tex_params)
	vector_params.update(mi_vec_params)
	scalar_params.update(mi_scal_params)

	return tex_params, vector_params, scalar_params

def get_extract_path(context) -> str:
	addon_prefs = context.preferences.addons[__package__].preferences
	extract_path = addon_prefs.extract_path
	assert extract_path != 'D:\\Path_to_your_extract_folder\\', "Set your extract folder path in the addon prefs!"
	return extract_path

class OBJECT_OT_SetUpMaterials(bpy.types.Operator):
	"""Load UE4 materials on an object"""
	bl_idname = "object.load_umodel_materials"
	bl_label = "Load uModel Materials"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		extract_path = get_extract_path(context)
		
		mat_map = build_material_map(extract_path)
		for key, value in mat_map.items():
			full_path = os.path.join(extract_path, value)
			mat_map[key] = full_path

		for o in context.selected_objects:
			set_up_materials(o, mat_map)

		return {'FINISHED'}
	
registry = [
	OBJECT_OT_SetUpMaterials
]