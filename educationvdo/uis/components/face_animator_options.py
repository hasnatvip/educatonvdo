from typing import List, Optional, Tuple

import gradio

from educationvdo import state_manager, translator
from educationvdo.common_helper import calculate_float_step
from educationvdo.processors.core import load_processor_module
from educationvdo.processors.modules.face_animator import choices as face_animator_choices
from educationvdo.processors.modules.face_animator.types import FaceAnimatorModel
from educationvdo.uis.core import get_ui_component, register_ui_component

FACE_ANIMATOR_MODEL_DROPDOWN : Optional[gradio.Dropdown] = None
FACE_ANIMATOR_MOTION_SCALE_SLIDER : Optional[gradio.Slider] = None
FACE_ANIMATOR_HEAD_POSE_RATIO_SLIDER : Optional[gradio.Slider] = None
FACE_ANIMATOR_EXPRESSION_RATIO_SLIDER : Optional[gradio.Slider] = None
FACE_ANIMATOR_EYE_OPEN_RATIO_SLIDER : Optional[gradio.Slider] = None
FACE_ANIMATOR_LIP_OPEN_RATIO_SLIDER : Optional[gradio.Slider] = None
FACE_ANIMATOR_RELATIVE_CHECKBOX : Optional[gradio.Checkbox] = None


def render() -> None:
	global FACE_ANIMATOR_MODEL_DROPDOWN
	global FACE_ANIMATOR_MOTION_SCALE_SLIDER
	global FACE_ANIMATOR_HEAD_POSE_RATIO_SLIDER
	global FACE_ANIMATOR_EXPRESSION_RATIO_SLIDER
	global FACE_ANIMATOR_EYE_OPEN_RATIO_SLIDER
	global FACE_ANIMATOR_LIP_OPEN_RATIO_SLIDER
	global FACE_ANIMATOR_RELATIVE_CHECKBOX

	has_face_animator = 'face_animator' in state_manager.get_item('processors')
	FACE_ANIMATOR_MODEL_DROPDOWN = gradio.Dropdown(
		label = translator.get('uis.model_dropdown', 'educationvdo.processors.modules.face_animator'),
		choices = face_animator_choices.face_animator_models,
		value = state_manager.get_item('face_animator_model'),
		visible = has_face_animator
	)
	FACE_ANIMATOR_MOTION_SCALE_SLIDER = gradio.Slider(
		label = translator.get('uis.motion_scale_slider', 'educationvdo.processors.modules.face_animator'),
		value = state_manager.get_item('face_animator_motion_scale'),
		step = calculate_float_step(face_animator_choices.face_animator_motion_scale_range),
		minimum = face_animator_choices.face_animator_motion_scale_range[0],
		maximum = face_animator_choices.face_animator_motion_scale_range[-1],
		visible = has_face_animator
	)
	FACE_ANIMATOR_HEAD_POSE_RATIO_SLIDER = gradio.Slider(
		label = translator.get('uis.head_pose_ratio_slider', 'educationvdo.processors.modules.face_animator'),
		value = state_manager.get_item('face_animator_head_pose_ratio'),
		step = calculate_float_step(face_animator_choices.face_animator_head_pose_ratio_range),
		minimum = face_animator_choices.face_animator_head_pose_ratio_range[0],
		maximum = face_animator_choices.face_animator_head_pose_ratio_range[-1],
		visible = has_face_animator
	)
	FACE_ANIMATOR_EXPRESSION_RATIO_SLIDER = gradio.Slider(
		label = translator.get('uis.expression_ratio_slider', 'educationvdo.processors.modules.face_animator'),
		value = state_manager.get_item('face_animator_expression_ratio'),
		step = calculate_float_step(face_animator_choices.face_animator_expression_ratio_range),
		minimum = face_animator_choices.face_animator_expression_ratio_range[0],
		maximum = face_animator_choices.face_animator_expression_ratio_range[-1],
		visible = has_face_animator
	)
	FACE_ANIMATOR_EYE_OPEN_RATIO_SLIDER = gradio.Slider(
		label = translator.get('uis.eye_open_ratio_slider', 'educationvdo.processors.modules.face_animator'),
		value = state_manager.get_item('face_animator_eye_open_ratio'),
		step = calculate_float_step(face_animator_choices.face_animator_eye_open_ratio_range),
		minimum = face_animator_choices.face_animator_eye_open_ratio_range[0],
		maximum = face_animator_choices.face_animator_eye_open_ratio_range[-1],
		visible = has_face_animator
	)
	FACE_ANIMATOR_LIP_OPEN_RATIO_SLIDER = gradio.Slider(
		label = translator.get('uis.lip_open_ratio_slider', 'educationvdo.processors.modules.face_animator'),
		value = state_manager.get_item('face_animator_lip_open_ratio'),
		step = calculate_float_step(face_animator_choices.face_animator_lip_open_ratio_range),
		minimum = face_animator_choices.face_animator_lip_open_ratio_range[0],
		maximum = face_animator_choices.face_animator_lip_open_ratio_range[-1],
		visible = has_face_animator
	)
	FACE_ANIMATOR_RELATIVE_CHECKBOX = gradio.Checkbox(
		label = translator.get('uis.relative_checkbox', 'educationvdo.processors.modules.face_animator'),
		value = state_manager.get_item('face_animator_relative'),
		visible = has_face_animator
	)
	register_ui_component('face_animator_model_dropdown', FACE_ANIMATOR_MODEL_DROPDOWN)


def listen() -> None:
	FACE_ANIMATOR_MODEL_DROPDOWN.change(update_face_animator_model, inputs = FACE_ANIMATOR_MODEL_DROPDOWN, outputs = FACE_ANIMATOR_MODEL_DROPDOWN)
	FACE_ANIMATOR_MOTION_SCALE_SLIDER.release(update_face_animator_motion_scale, inputs = FACE_ANIMATOR_MOTION_SCALE_SLIDER)
	FACE_ANIMATOR_HEAD_POSE_RATIO_SLIDER.release(update_face_animator_head_pose_ratio, inputs = FACE_ANIMATOR_HEAD_POSE_RATIO_SLIDER)
	FACE_ANIMATOR_EXPRESSION_RATIO_SLIDER.release(update_face_animator_expression_ratio, inputs = FACE_ANIMATOR_EXPRESSION_RATIO_SLIDER)
	FACE_ANIMATOR_EYE_OPEN_RATIO_SLIDER.release(update_face_animator_eye_open_ratio, inputs = FACE_ANIMATOR_EYE_OPEN_RATIO_SLIDER)
	FACE_ANIMATOR_LIP_OPEN_RATIO_SLIDER.release(update_face_animator_lip_open_ratio, inputs = FACE_ANIMATOR_LIP_OPEN_RATIO_SLIDER)
	FACE_ANIMATOR_RELATIVE_CHECKBOX.change(update_face_animator_relative, inputs = FACE_ANIMATOR_RELATIVE_CHECKBOX)

	processors_checkbox_group = get_ui_component('processors_checkbox_group')
	if processors_checkbox_group:
		processors_checkbox_group.change(remote_update, inputs = processors_checkbox_group, outputs = [ FACE_ANIMATOR_MODEL_DROPDOWN, FACE_ANIMATOR_MOTION_SCALE_SLIDER, FACE_ANIMATOR_HEAD_POSE_RATIO_SLIDER, FACE_ANIMATOR_EXPRESSION_RATIO_SLIDER, FACE_ANIMATOR_EYE_OPEN_RATIO_SLIDER, FACE_ANIMATOR_LIP_OPEN_RATIO_SLIDER, FACE_ANIMATOR_RELATIVE_CHECKBOX ])


def remote_update(processors : List[str]) -> Tuple[gradio.Dropdown, gradio.Slider, gradio.Slider, gradio.Slider, gradio.Slider, gradio.Slider, gradio.Checkbox]:
	has_face_animator = 'face_animator' in processors
	return gradio.Dropdown(visible = has_face_animator), gradio.Slider(visible = has_face_animator), gradio.Slider(visible = has_face_animator), gradio.Slider(visible = has_face_animator), gradio.Slider(visible = has_face_animator), gradio.Slider(visible = has_face_animator), gradio.Checkbox(visible = has_face_animator)


def update_face_animator_model(face_animator_model : FaceAnimatorModel) -> gradio.Dropdown:
	face_animator_module = load_processor_module('face_animator')
	face_animator_module.clear_inference_pool()
	state_manager.set_item('face_animator_model', face_animator_model)

	if face_animator_module.pre_check():
		return gradio.Dropdown(value = state_manager.get_item('face_animator_model'))
	return gradio.Dropdown()


def update_face_animator_motion_scale(face_animator_motion_scale : float) -> None:
	state_manager.set_item('face_animator_motion_scale', face_animator_motion_scale)


def update_face_animator_head_pose_ratio(face_animator_head_pose_ratio : float) -> None:
	state_manager.set_item('face_animator_head_pose_ratio', face_animator_head_pose_ratio)


def update_face_animator_expression_ratio(face_animator_expression_ratio : float) -> None:
	state_manager.set_item('face_animator_expression_ratio', face_animator_expression_ratio)


def update_face_animator_eye_open_ratio(face_animator_eye_open_ratio : float) -> None:
	state_manager.set_item('face_animator_eye_open_ratio', face_animator_eye_open_ratio)


def update_face_animator_lip_open_ratio(face_animator_lip_open_ratio : float) -> None:
	state_manager.set_item('face_animator_lip_open_ratio', face_animator_lip_open_ratio)


def update_face_animator_relative(face_animator_relative : bool) -> None:
	state_manager.set_item('face_animator_relative', face_animator_relative)
