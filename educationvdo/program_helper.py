from argparse import ArgumentParser, _ArgumentGroup, _SubParsersAction
from typing import Optional


def find_argument_group(program : ArgumentParser, group_name : str) -> Optional[_ArgumentGroup]:
	for group in program._action_groups:
		if group.title == group_name:
			return group
	return None


def validate_args(program : ArgumentParser) -> bool:
	if validate_actions(program):
		for action in program._actions:
			if isinstance(action, _SubParsersAction):
				for _, sub_program in action._name_parser_map.items():
					if not validate_args(sub_program):
						return False
		return True
	return False


import sys


def validate_actions(program : ArgumentParser) -> bool:
	valid = True
	for action in program._actions:
		if action.default and action.choices:
			if isinstance(action.default, list):
				invalid = [default for default in action.default if default not in action.choices]
				if invalid:
					print(f"[ERROR] Invalid default for '{action.dest}': {invalid} not in {action.choices}", file=sys.stderr)
					valid = False
			elif action.default not in action.choices:
				print(f"[ERROR] Invalid default for '{action.dest}': {action.default!r} not in {action.choices}", file=sys.stderr)
				valid = False
	return valid
