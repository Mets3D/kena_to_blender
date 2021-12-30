from typing import List, Dict, Tuple
from bpy.types import Object, Material, Node, Image
import bpy, os, sys, shutil
from .props_txt_to_json import props_txt_to_dict

import json

EQUIVALENT_PARAMS = {
	'BaseColor' : 'Diffuse'
	,'Albedo' : 'Diffuse'
	,'Normals' : 'Normal'
	,'Emissive' : 'Emission'
	,'AO_R' : 'AO_R_M'
	,'MREA' : 'AO_R_M'
}

TEX_BLACKLIST = [
	'kena_cloth_sprint_EMISSIVE'
	,'kena_props_sprint_EMISSIVE'
]

SHADER_MAPPING = {
	'M_EyeRefractive' : 'Kena_Eye'
}

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

		print("SETTING UP", mat.name)

		mat_info = props_txt_to_dict(mat_file)
		# print("AND THEN THIS IS WHAT'S RETURNED", json.dumps(mat_info, indent=4))

		set_up_material(obj, mat, mat_info)

def set_up_material(obj: Object, mat: Material, mat_info: Dict):
	"""Set up a single material."""

	tex_params, vector_params, scalar_params = parse_mat_params(mat_info)
	mat.use_nodes = True
	nodes = mat.node_tree.nodes
	links = mat.node_tree.links

	nodes.clear()

	# Create main node group node
	node_ng = nodes.new(type='ShaderNodeGroup')
	shader = 'Kena'
	if 'Parent' in mat_info:
		master_mat = mat_info['Parent'].split("'")[1].split(".")[1]
		if master_mat in SHADER_MAPPING:
			shader = SHADER_MAPPING[master_mat]
	node_ng.node_tree = bpy.data.node_groups[shader]

	node_ng.location = (500, 200)
	node_ng.width = 350

	node_output = nodes.new(type='ShaderNodeOutputMaterial')
	node_output.location = (900, 200)
	links.new(node_ng.outputs[0], node_output.inputs[0])

	param_nodes = []
	y_loc = 1000
	for par_name, par_value in tex_params.items():
		node = create_node_texture(mat, par_name, par_value, node_ng)
		param_nodes.append(node)
		node.location = (-450, y_loc)
		y_loc -= 320
	for par_name, par_value in vector_params.items():
		node = create_node_vector(mat, par_name, par_value, node_ng)
		param_nodes.append(node)
		node.location = (-450, y_loc)
		y_loc -= 220
	for par_name, par_value in scalar_params.items():
		node = create_node_float(mat, par_name, par_value, node_ng)
		param_nodes.append(node)
		node.location = (-450, y_loc)
		y_loc -= 170

	for par_node in param_nodes:
		# Linking the node to the nodegroup
		par_name = par_node.name
		if par_name in EQUIVALENT_PARAMS:
			input_pin = node_ng.inputs.get(EQUIVALENT_PARAMS[par_name])
		else:
			input_pin = node_ng.inputs.get(par_name)

		if not input_pin:
			continue
			
		if par_node.type == 'TEX_IMAGE' and par_node.image.name in TEX_BLACKLIST:
			continue

		if len(input_pin.links) > 0:
			print("WARNING: NODE WAS ALREADY CONNECTED!")

		links.new(par_node.outputs[0], input_pin)

		if par_node.type == 'TEX_IMAGE' and input_pin.name not in ['Diffuse']:
			par_node.image.colorspace_settings.name = 'Non-Color'
		
		if input_pin.name == 'Diffuse':
			nodes.active = par_node

def create_node_float(mat, par_name, par_value, node_ng):
	nodes = mat.node_tree.nodes

	node = nodes.new(type='ShaderNodeValue')
	node.name = node.label = par_name
	node.outputs[0].default_value = float(par_value)

	return node

def create_node_vector(mat, par_name, par_value, node_ng):
	nodes = mat.node_tree.nodes

	def assign_uv_scale_values(mat, target_node):
		if not target_node:
			return
		if len(target_node.inputs[0].links) > 0:
			mapping_node = target_node.inputs[0].links[0].from_node
			if mapping_node.type == 'MAPPING':
				# Set X and Y scale values to the DetailTile value.
				mapping_node.inputs[3].default_value[0] = par_value[0]
				mapping_node.inputs[3].default_value[1] = par_value[1]
			else:
				print(f"Expected a mapping node for {par_name}, got {mapping_node.type} instead!")
				return
			mapping_node.label = mapping_node.name = par_name
		else:
			print(f"Warning: Node {target_node.name} in material {mat.name} was expected to have a Mapping node plugged into it!")

	node = nodes.new(type='ShaderNodeCombineXYZ')
	node.name = node.label = par_name
	node.inputs[0].default_value = par_value[0]
	node.inputs[1].default_value = par_value[1]
	node.inputs[2].default_value = par_value[2]

	return node

def create_node_texture(
		mat: Material
		,par_name: str
		,par_value: str
		,node_ng: Node
	):
	nodes = mat.node_tree.nodes

	node = nodes.new(type="ShaderNodeTexImage")
	node.name = node.label = par_name
	node.width = 300

	tex_path = get_extract_path(bpy.context) + os.sep + par_value
	node.image = load_texture(mat, tex_path)
	if not node.image:
		node.label = "MISSING:" + par_value

	return node

def load_texture(
		mat: Material
		,tex_path: str
	) -> Image:
	img_filename = os.path.basename(tex_path)	# Filename with extension.

	# Check if an image with this filepath is already loaded.
	img = None
	for i in bpy.data.images:
		if bpy.path.basename(i.filepath) == img_filename:
			img = i
			break
	# Check if the file exists
	if not img and not os.path.isfile(tex_path):
		print("Image not found: " + tex_path + " (Usually unimportant)")
		return
	elif not img:	# The image exists in the filesystem but not in Blender.
		# Load the image.
		# Because we pack and unpack the images immediately on import, the check_existing flag
		# doesn't actually help us here...
		img = bpy.data.images.load(tex_path, check_existing=True)

	localize_image(img)

	# Correct the image name.
	filepath = img.filepath.replace(os.sep, "/")	# important to make separators consistent...
	filename = filepath.split("/")[-1]
	file_parts = filename.split(".")
	img.name = file_parts[0]

	return img

def localize_image(img: Image):
	if img.filepath.startswith("//textures"):
		# Image is already local.
		return

	assert bpy.data.is_saved, "Blend file must be saved first. (There should be an earlier assert for this!)"

	if len(img.packed_files) > 0:
		return

	if os.path.isfile(os.path.abspath(img.filepath)) and img.filepath.endswith(".tga"):
		# The image exists at its filepath, cool.
		pass
	else:
		print("Image not found: " + img.filepath)
		return

	# Change the image filepath to be next to the blend file to a folder called
	# textures_ue, to differentiate it from the Blender-managed "textures" folder.
	img_abspath = os.path.abspath(img.filepath)
	extract_path = os.path.abspath(get_extract_path(bpy.context))
	blendfile_folder_path = os.path.dirname(bpy.data.filepath)
	textures_abspath = os.path.join(blendfile_folder_path, "textures_ue")
	new_abspath = img_abspath.replace(extract_path, textures_abspath)
	new_rel_path = "//textures_ue" + img.filepath.replace(extract_path, "")

	# Copy the image from the uncook folder next to the .blend file, 
	os.makedirs(os.path.dirname(new_abspath), exist_ok=True)
	shutil.copyfile(img.filepath, new_abspath)
	img.filepath = new_rel_path

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