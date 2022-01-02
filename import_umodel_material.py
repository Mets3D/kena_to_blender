from typing import List, Dict, Tuple
from bpy.types import Object, Material, Node, Image
import bpy, os, sys, shutil
from .props_txt_to_json import props_txt_to_dict
from .utils import get_extract_path

RES_FILE = "kena_materials.blend"
RES_DIR = os.path.dirname(os.path.realpath(__file__))
RES_PATH = os.path.join(RES_DIR, RES_FILE)

EQUIVALENT_PARAMS = {
	'BaseColor' : 'Diffuse'
	,'Albedo' : 'Diffuse'
	,'Tex_Color' : 'Diffuse'
	,'TileDiffuse' : 'Diffuse'
	,'Normals' : 'Normal'
	,'TileNormal' : 'Normal'
	,'Tex_Normal' : 'Normal'
	,'Emissive' : 'Emission'
	,'GlowMap' : 'Emission'
	,'AO_R' : 'AO_R_M'
	,'MREA' : 'AO_R_M'
	,'Tex_Comp' : 'AO_R_M'
	,'Comp_M_R_Ao' : 'M_R_AO'
	,'Unique_Hair_Value' : 'Depth'
}

TEX_BLACKLIST = [
	'kena_cloth_sprint_EMISSIVE'
	,'kena_props_sprint_EMISSIVE'
	,'kena_cloth_EMISSIVE'
	,'Noise_cloudsmed'
]

SHADER_MAPPING = {
	'M_EyeRefractive' : 'Kena_Eye'
	,'M_HairSheet' : 'Kena_Hair'
	,'M_Skin' : 'Kena_Skin'
}

def ensure_node_group(ng_name):
	"""Check if a nodegroup exists, and if not, link it from the addon's resource file."""

	if ng_name not in bpy.data.node_groups:
		with bpy.data.libraries.load(RES_PATH, link=True) as (data_from, data_to):
			for ng in data_from.node_groups:
				if ng == ng_name:
					data_to.node_groups.append(ng)

	ng = bpy.data.node_groups[ng_name]
	ng.use_fake_user = False

	return ng

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

def set_up_materials(context, obj: Object, mat_map: Dict[str, str]):
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

def set_up_material(obj: Object, mat: Material, mat_info: Dict):
	"""Set up a single material."""

	# print("\n\n",mat.name)
	tex_params, vector_params, scalar_params = parse_mat_params(mat.name, mat_info)
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
		node_ng.name = node_ng.label = master_mat
	node_ng.node_tree = ensure_node_group(shader)

	node_ng.location = (500, 200)
	node_ng.width = 350

	node_output = nodes.new(type='ShaderNodeOutputMaterial')
	node_output.location = (900, 200)
	links.new(node_ng.outputs[0], node_output.inputs[0])

	param_nodes = []
	y_loc = 1000
	for par_name, par_value in tex_params.items():
		node = create_node_texture(mat, par_name, par_value, node_ng)
		if not node: continue
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
			# If something is already connected to this socket, don't overwrite it.
			# Textures are processed first, and they should have priority.
			continue

		links.new(par_node.outputs[0], input_pin)

		if par_node.type == 'TEX_IMAGE' and input_pin.name not in ['Diffuse', 'Alpha', 'IrisColor']:
			par_node.image.colorspace_settings.name = 'Non-Color'
		
		if input_pin.name == 'Diffuse':
			nodes.active = par_node
	
	if shader == 'Kena_Hair':
		mat.blend_method = 'HASHED'
	else:
		mat.blend_method = 'CLIP'
	if 'EyeShadow' in mat.name:
		mat.blend_method = 'BLEND'

def create_node_float(mat, par_name, par_value, node_ng):
	nodes = mat.node_tree.nodes

	node = nodes.new(type='ShaderNodeValue')
	node.name = node.label = par_name
	node.outputs[0].default_value = float(par_value)

	return node

def create_node_vector(mat, par_name, par_value, node_ng):
	nodes = mat.node_tree.nodes
	if not par_name:
		par_name = "Unknown"

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
	if not par_value:
		return

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

	# Sometimes master materials have a ReferencedTextures block within their CachedExpressionData block
	# without having any CollectedTextureParameters.
	# In this case the type of each texture is also not indicated, leaving us to guess by filename...
	cached_exp_data = mat_info.get('CachedExpressionData')
	if cached_exp_data:
		tex_list = cached_exp_data.get('ReferencedTextures')
		if tex_list:
			for tex_path in tex_list:
				value = tex_path.split("'")[1].split(".")[0] + ".tga"

				name = ""
				# Guess the texture type name
				if value.endswith("_D.tga"):
					name = 'Diffuse'
				elif value.endswith("_H_R_AO.tga"):
					name = 'H_R_AO'
				elif value.endswith("_M_R_AO.tga"):
					name = 'M_R_AO'
				elif value.endswith("_AO_R_M.tga"):
					name = 'AO_R_M'
				elif value.endswith("_N.tga"):
					name = 'Normal'
				elif value.endswith("_E.tga"):
					name = 'Emission'

				if name=="" or name in processed_tex:
					name = 'Unknown'

				if name not in processed_tex:
					processed_tex[name] = value

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

def parse_mat_params(mat_name: str, mat_info: Dict) -> Tuple[Dict, Dict, Dict]:
	tex_params = {}
	vector_params = {}
	scalar_params = {}

	if 'Parent' in mat_info:
		# Recursively load material info from parents first.
		parent_rel_path = mat_info['Parent'].split("'")[1].split(".")[0]
		parent_name = parent_rel_path.split("/")[-1]
		parent_abs_path = get_extract_path(bpy.context) + os.sep + parent_rel_path + ".props.txt"

		parent_mat_info = props_txt_to_dict(parent_abs_path)
		tex_params, vector_params, scalar_params = parse_mat_params(parent_name, parent_mat_info)

	# Determine whether this material should be parsed as a MasterMaterial or MaterialInstance based on name prefix.
	is_instance = mat_name.startswith("MI_")
	if is_instance:
		# Process material info as MaterialInstance
		local_tex_params, local_vector_params, local_scalar_params = do_instance_params(mat_info = mat_info)
	else:
		# Process material info as MasterMaterial
		local_tex_params, local_vector_params, local_scalar_params = do_master_params(mat_info = mat_info)
	
	tex_params.update(local_tex_params)
	vector_params.update(local_vector_params)
	scalar_params.update(local_scalar_params)

	return tex_params, vector_params, scalar_params

def load_materials_on_selected_objects(context):
	extract_path = get_extract_path(context)
	
	mat_map = build_material_map(extract_path)
	for key, value in mat_map.items():
		full_path = os.path.join(extract_path, value)
		mat_map[key] = full_path

	for o in context.selected_objects:
		set_up_materials(context, o, mat_map)

class OBJECT_OT_SetUpMaterials(bpy.types.Operator):
	"""Load UE4 materials on an object"""
	bl_idname = "object.load_umodel_materials"
	bl_label = "Load uModel Materials"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		load_materials_on_selected_objects(context)

		return {'FINISHED'}
	
registry = [
	OBJECT_OT_SetUpMaterials
]