# Utility functions to parse .props.txt files output by uModel into Python dict/json.

from typing import Tuple, Dict
import json, re
RE_LIST = re.compile(r".*\[[0-9]*\]")

def props_txt_to_dict(filepath: str) -> Dict:
	"""Convert .props.txt files output by uModel to a Python dictionary."""

	# Read file into lines
	data = open(filepath).read()
	data = cleanup_data(data)
	parsed_dict = parse(data)

	dicts_to_lists(parsed_dict)

	return parsed_dict

def props_txt_to_json(filepath: str) -> str:
	parsed_dict = props_txt_to_dict(filepath)
	return json.dumps(parsed_dict, indent=4)

def value_to_python(value: str):
	try:
		return eval(value)
	except Exception:
		return value

def cleanup_data(data: str):
	lines = []
	for line in data.split("\n"):
		lines.append(
			re.sub(r"\s*", "", line).replace("false", "False").replace("true", "True")
		)

	return "\n".join(lines).replace("=\n", "=")

def process_line(data: Dict, line: str):
	"""Add an entry to the data dictionary, based on a string.
	
	line must be a string with an equal sign and no brackets unless it starts and ends with matched ones.
	Processing a line just means turning it into a key/value pair.
	"""

	if "=" not in line:
		return
	key, value = line.split("=", 1)

	if value.startswith("{") and value.endswith("}"):
		if len(value) == 2:
			data[key] = []
			return
		value = value[1:-1]
		if "=" not in value:
			value = eval(f"[{value}]")

	if "," in value:
		sub_data = {}
		parts = value.split(",")
		for part in parts:
			k, v = part.split("=")
			try:
				v = eval(v)
			except Exception:
				pass
			sub_data[k] = v
		value = sub_data

	if "=" in value:
		k, v = value.split("=")
		value = {k:v} 

	try:
		value = eval(value)
	except Exception:
		pass

	data[key] = value

def parse(data: str, is_top_level=True) -> Tuple[Dict, int]:
	"""A recursive attempt:
	Function takes a string and returns a dictionary and an int.
	The int is how many lines the single call of the function has scanned, out of the lines that were passed to it.
	Closing brackets } are always at the end of the line.
	We use this returned int to skip those lines higher up in the stack, so that we only have to scan once.
	"""
	processed = {}
	lines = data.split("\n")
	index_offset = 0	# Increase this by 1 for each line processed by a deeper recursion level.
	for i in range(len(lines)):
		adjusted_i = i + index_offset
		if adjusted_i >= len(lines):
			break
		line = lines[adjusted_i]
		if "{" in line:
			if "}" in line:
				process_line(processed, line)
			else:
				name, rest = line.split("={", 1)
				# A new block begins here, so recurse.
				processed[name], num_lines = parse("\n".join([rest] + lines[adjusted_i+1:]), is_top_level=False)
				# Add the number of lines that were processed by the recursion.
				index_offset += num_lines
		elif "}" in line:
			# } is always assumed to be the last character in the line.
			process_line(processed, line[:-1])
			if not is_top_level:
				# Indicates end of a block, so we go up in the stack. (We return)
				return processed, adjusted_i
			else:
				# The block has ended, but we are already at the top level, so let's keep looping.
				continue
		else:
			# No brackets in the line, just process_line it.
			process_line(processed, line)

	return processed

def dicts_to_lists(data: Dict) -> Dict:
	"""
	Iterate through only the top level of the dictionary.
	If an entry's name matches the RE_LIST regex:
	- Remove the regex from the name
	- Add the contents of each entry in the dict to a list which should become the new value.
	"""
	for key, value in list(data.items()):
		match = re.match(RE_LIST, key)
		if match:
			new_key = key.split("[")[0]
			if value:
				if type(value)==dict:
					new_value = list(value.values())
				else:
					new_value = value
			else:
				new_value = None
			data[new_key] = new_value
			value = new_value
			del data[key]
		if type(value) == dict:
			dicts_to_lists(value)