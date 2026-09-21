from typing import Optional

import gradio

import educationvdo.choices
from educationvdo import state_manager, translator
from educationvdo.types import VideoMemoryStrategy

VIDEO_MEMORY_STRATEGY_DROPDOWN : Optional[gradio.Dropdown] = None


def render() -> None:
	global VIDEO_MEMORY_STRATEGY_DROPDOWN

	VIDEO_MEMORY_STRATEGY_DROPDOWN = gradio.Dropdown(
		label = translator.get('uis.video_memory_strategy_dropdown'),
		choices = educationvdo.choices.video_memory_strategies,
		value = state_manager.get_item('video_memory_strategy')
	)


def listen() -> None:
	VIDEO_MEMORY_STRATEGY_DROPDOWN.change(update_video_memory_strategy, inputs = VIDEO_MEMORY_STRATEGY_DROPDOWN)


def update_video_memory_strategy(video_memory_strategy : VideoMemoryStrategy) -> None:
	state_manager.set_item('video_memory_strategy', video_memory_strategy)
