from typing import Optional

import gradio

import educationvdo.choices
from educationvdo import state_manager, translator
from educationvdo.types import WorkflowStrategy

WORKFLOW_STRATEGY_DROPDOWN : Optional[gradio.Dropdown] = None


def render() -> None:
	global WORKFLOW_STRATEGY_DROPDOWN

	WORKFLOW_STRATEGY_DROPDOWN = gradio.Dropdown(
		label = translator.get('uis.workflow_strategy_dropdown'),
		choices = educationvdo.choices.workflow_strategies,
		value = state_manager.get_item('workflow_strategy')
	)


def listen() -> None:
	WORKFLOW_STRATEGY_DROPDOWN.change(update_workflow_strategy, inputs = WORKFLOW_STRATEGY_DROPDOWN)


def update_workflow_strategy(workflow_strategy : WorkflowStrategy) -> None:
	state_manager.set_item('workflow_strategy', workflow_strategy)
