import os

from educationvdo import content_analyser, ffmpeg, logger, process_manager, state_manager, translator
from educationvdo.filesystem import is_image
from educationvdo.processors.core import get_processors_modules
from educationvdo.temp_helper import get_temp_file_path
from educationvdo.time_helper import calculate_end_time
from educationvdo.types import ErrorCode
from educationvdo.vision import detect_image_resolution, pack_resolution, read_static_image, restrict_image_resolution, scale_resolution, write_image
from educationvdo.workflows.core import conditional_get_target_vision_frames, is_process_stopping, process_temp_frame


def analyse_image() -> ErrorCode:
	if content_analyser.analyse_image(state_manager.get_item('target_path')):
		return 3
	return 0


def prepare_image() -> ErrorCode:
	output_image_resolution = scale_resolution(detect_image_resolution(state_manager.get_item('target_path')), state_manager.get_item('output_image_scale'))
	temp_image_resolution = restrict_image_resolution(state_manager.get_item('target_path'), output_image_resolution)

	logger.info(translator.get('copying_image').format(resolution = pack_resolution(temp_image_resolution)), __name__)
	if ffmpeg.copy_image(state_manager.get_item('target_path'), temp_image_resolution):
		logger.debug(translator.get('copying_image_succeeded'), __name__)
	else:
		logger.error(translator.get('copying_image_failed'), __name__)
		process_manager.end()
		return 1
	return 0


def process_image() -> ErrorCode:
	temp_image_path = get_temp_file_path(state_manager.get_item('target_path'))
	target_vision_frames = conditional_get_target_vision_frames(0)
	temp_vision_frame = read_static_image(temp_image_path, 'rgba')
	temp_vision_frame = process_temp_frame(target_vision_frames, temp_vision_frame, 0)
	write_image(temp_image_path, temp_vision_frame)

	for processor_module in get_processors_modules(state_manager.get_item('processors')):
		processor_module.post_process()

	if is_process_stopping():
		return 4
	return 0


def finalize_image(start_time : float) -> ErrorCode:
	output_image_resolution = scale_resolution(detect_image_resolution(state_manager.get_item('target_path')), state_manager.get_item('output_image_scale'))

	logger.info(translator.get('finalizing_image').format(resolution = pack_resolution(output_image_resolution)), __name__)
	if ffmpeg.finalize_image(state_manager.get_item('target_path'), state_manager.get_item('output_path'), output_image_resolution):
		logger.debug(translator.get('finalizing_image_succeeded'), __name__)
	else:
		logger.warn(translator.get('finalizing_image_skipped'), __name__)

	output_path = state_manager.get_item('output_path')
	if is_image(output_path):
		seconds = calculate_end_time(start_time)
		logger.info(translator.get('processing_image_succeeded').format(seconds = seconds), __name__)
		logger.info(f'Output image saved to: {output_path}', __name__)
		file_size_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0

		print('\n' + '━' * 60, flush = True)
		print(f'🎉 IMAGE PROCESSING SUCCEEDED IN {seconds}s!', flush = True)
		print(f'📁 Saved image: {output_path} ({file_size_mb:.2f} MB)', flush = True)
		print(f'📥 How to Download in Google Colab:', flush = True)
		print(f'   1. Run Colab download command in a new cell:', flush = True)
		print(f'      from google.colab import files; files.download("{output_path}")', flush = True)
		print(f'   2. Or find it in the Colab file browser (left sidebar)', flush = True)
		print('━' * 60 + '\n', flush = True)
	else:
		logger.error(translator.get('processing_image_failed'), __name__)
		return 1
	return 0
