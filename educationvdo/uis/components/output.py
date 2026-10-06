import os
import tempfile
from pathlib import Path
from typing import Optional

import gradio

from educationvdo import state_manager, translator
from educationvdo.uis.core import register_ui_component

OUTPUT_PATH_TEXTBOX : Optional[gradio.Textbox] = None
OUTPUT_IMAGE : Optional[gradio.Image] = None
OUTPUT_VIDEO : Optional[gradio.Video] = None


def render() -> None:
	global OUTPUT_PATH_TEXTBOX
	global OUTPUT_IMAGE
	global OUTPUT_VIDEO

	if not state_manager.get_item('output_path'):
		if os.path.exists('/content'):
			colab_outputs = os.path.abspath('/content/outputs')
			os.makedirs(colab_outputs, exist_ok = True)
			state_manager.set_item('output_path', colab_outputs)
		else:
			documents_directory = Path.home().joinpath('Documents')

			if documents_directory.exists():
				state_manager.set_item('output_path', str(documents_directory))
			else:
				outputs_directory = Path.cwd().joinpath('outputs')
				outputs_directory.mkdir(parents = True, exist_ok = True)
				state_manager.set_item('output_path', str(outputs_directory))
	elif isinstance(state_manager.get_item('output_path'), (str, Path)) and not os.path.splitext(str(state_manager.get_item('output_path')))[1]:
		os.makedirs(str(state_manager.get_item('output_path')), exist_ok = True)
	OUTPUT_PATH_TEXTBOX = gradio.Textbox(
		label = translator.get('uis.output_path_textbox'),
		value = state_manager.get_item('output_path'),
		max_lines = 1
	)
	OUTPUT_IMAGE = gradio.Image(
		label = translator.get('uis.output_image_or_video'),
		visible = False
	)
	OUTPUT_VIDEO = gradio.Video(
		label = translator.get('uis.output_image_or_video')
	)


def listen() -> None:
	OUTPUT_PATH_TEXTBOX.change(update_output_path, inputs = OUTPUT_PATH_TEXTBOX)
	register_ui_component('output_image', OUTPUT_IMAGE)
	register_ui_component('output_video', OUTPUT_VIDEO)


def update_output_path(output_path : str) -> None:
	state_manager.set_item('output_path', output_path)
