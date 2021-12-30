# uModel to Blender IO Tools
# Copyright (C) 2021 Mets3D
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

bl_info = {
	"name": "uModel IO Tools",
	"author": "Mets3D",
	"version": (1, 0),
	"blender": (3, 0, 0),
	"location": "File->Import->Witcher 3 FBX",
	"description": "My tools to help import stuff from uModel (UE4)",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "Object"
}

import bpy, importlib
from bpy.props import StringProperty
from . import import_umodel_material
from . import props_txt_to_json

class uModelIOAddonPrefs(bpy.types.AddonPreferences):
	# this must match the addon name, use '__package__'
	# when defining this in a submodule of a python package.
	bl_idname = __package__

	extract_path: StringProperty(
		name="Extract Path",
		subtype='DIR_PATH',
		default='D:\\Path_to_your_extract_folder\\',
		description="Path to where you extracted the game files using umodel.exe. Will be searching for .tga textures here"
	)

	def draw(self, context):
		layout = self.layout
		layout.label(text="uModel Importer settings:")
		layout.prop(self, "extract_path")

modules = [
	import_umodel_material
    ,props_txt_to_json
]

from bpy.utils import register_class, unregister_class
def register():
	for m in modules:
		importlib.reload(m)
		if hasattr(m, 'registry'):
			for c in m.registry:
				register_class(c)
		if hasattr(m, 'register'):
			m.register()

	bpy.utils.register_class(uModelIOAddonPrefs)

def unregister():
	for m in reversed(modules):
		if hasattr(m, 'unregister'):
			m.unregister()
		if hasattr(m, 'registry'):
			for c in m.registry:
				unregister_class(c)

	bpy.utils.unregister_class(uModelIOAddonPrefs)