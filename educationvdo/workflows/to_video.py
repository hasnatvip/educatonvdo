from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Deque

import cv2
import numpy
from tqdm import tqdm

from educationvdo import content_analyser, ffmpeg, ffprobe, logger, process_manager, state_manager, translator, video_manager
from educationvdo.common_helper import get_first, get_middle
from educationvdo.filesystem import filter_audio_paths, filter_video_paths, is_image, is_video
from educationvdo.processors.core import get_processors_modules
from educationvdo.temp_helper import move_temp_file, resolve_temp_frame_set
from educationvdo.time_helper import calculate_end_time
from educationvdo.types import ErrorCode, Fps, Resolution, VisionFrame
from educationvdo.vision import detect_image_resolution, detect_video_fps, detect_video_resolution, pack_resolution, predict_video_frame_total, read_static_image, read_static_video_frame, restrict_image_resolution, restrict_trim_frame, restrict_video_fps, restrict_video_resolution, scale_resolution, write_image
from educationvdo.workflows.core import conditional_get_target_vision_frames, is_process_stopping, process_temp_frame


def resolve_temp_video_resolution(target_path : str) -> Resolution:
	if is_video(target_path):
		output_video_resolution = scale_resolution(detect_video_resolution(target_path), state_manager.get_item('output_video_scale'))
		return restrict_video_resolution(target_path, output_video_resolution)
	output_video_resolution = scale_resolution(detect_image_resolution(target_path), state_manager.get_item('output_video_scale'))
	return restrict_image_resolution(target_path, output_video_resolution)


def resolve_output_video_resolution(target_path : str) -> Resolution:
	if is_video(target_path):
		return scale_resolution(detect_video_resolution(target_path), state_manager.get_item('output_video_scale'))
	return scale_resolution(detect_image_resolution(target_path), state_manager.get_item('output_video_scale'))


def resolve_temp_video_fps(target_path : str) -> Fps:
	if is_video(target_path):
		return restrict_video_fps(target_path, state_manager.get_item('output_video_fps'))
	source_video_paths = filter_video_paths(state_manager.get_item('source_paths'))
	if source_video_paths:
		return detect_video_fps(source_video_paths[0]) or state_manager.get_item('output_video_fps')
	return state_manager.get_item('output_video_fps')


def resolve_video_frame_total(target_path : str, temp_video_fps : Fps, trim_frame_start : int, trim_frame_end : int) -> int:
	if is_video(target_path):
		return predict_video_frame_total(target_path, temp_video_fps, trim_frame_start, trim_frame_end)
	source_video_paths = filter_video_paths(state_manager.get_item('source_paths'))
	source_audio_paths = filter_audio_paths(state_manager.get_item('source_paths'))
	if trim_frame_end is not None:
		return max(1, trim_frame_end - trim_frame_start)
	if source_video_paths:
		v_start, v_end = restrict_trim_frame(source_video_paths[0], state_manager.get_item('trim_frame_start'), state_manager.get_item('trim_frame_end'))
		return predict_video_frame_total(source_video_paths[0], temp_video_fps, v_start, v_end)
	if source_audio_paths:
		audio_metadata = ffprobe.extract_static_audio_metadata(source_audio_paths[0])
		audio_duration = audio_metadata.get('duration') if audio_metadata else 5.0
		return max(1, round(audio_duration * temp_video_fps))
	return 150


def analyse_video() -> ErrorCode:
	target_path = state_manager.get_item('target_path')
	if is_video(target_path):
		trim_frame_start, trim_frame_end = restrict_trim_frame(target_path, state_manager.get_item('trim_frame_start'), state_manager.get_item('trim_frame_end'))
		if content_analyser.analyse_video(target_path, trim_frame_start, trim_frame_end):
			return 3
	elif is_image(target_path):
		if content_analyser.analyse_image(target_path):
			return 3
	return 0


def extract_frames() -> ErrorCode:
	target_path = state_manager.get_item('target_path')
	trim_frame_start, trim_frame_end = restrict_trim_frame(target_path, state_manager.get_item('trim_frame_start'), state_manager.get_item('trim_frame_end')) if is_video(target_path) else (state_manager.get_item('trim_frame_start') or 0, state_manager.get_item('trim_frame_end'))
	temp_video_resolution = resolve_temp_video_resolution(target_path)
	temp_video_fps = resolve_temp_video_fps(target_path)

	logger.info(translator.get('extracting_frames').format(resolution=pack_resolution(temp_video_resolution), fps=temp_video_fps), __name__)

	if is_video(target_path):
		success = ffmpeg.extract_frames(target_path, temp_video_resolution, temp_video_fps, trim_frame_start, trim_frame_end)
	else:
		spawn_frame_total = resolve_video_frame_total(target_path, temp_video_fps, trim_frame_start, trim_frame_end)
		success = ffmpeg.spawn_frames(target_path, temp_video_resolution, temp_video_fps, spawn_frame_total)

	if success:
		logger.debug(translator.get('extracting_frames_succeeded'), __name__)
	else:
		if is_process_stopping():
			return 4
		logger.error(translator.get('extracting_frames_failed'), __name__)
		return 1
	return 0


def process_disk_frame(temp_frame_path : str, frame_number : int) -> bool:
	target_vision_frames = conditional_get_target_vision_frames(frame_number)
	temp_vision_frame = read_static_image(temp_frame_path, 'rgba')
	temp_vision_frame = process_temp_frame(target_vision_frames, temp_vision_frame, frame_number)
	return write_image(temp_frame_path, temp_vision_frame)


def process_disk_frames() -> ErrorCode:
	temp_frame_set = resolve_temp_frame_set(state_manager.get_item('target_path'))

	if temp_frame_set:
		with tqdm(total = len(temp_frame_set), desc = translator.get('processing'), unit = 'frame', ascii = ' =', disable = state_manager.get_item('log_level') in [ 'warn', 'error' ]) as progress:
			progress.set_postfix(execution_providers = state_manager.get_item('execution_providers'))

			if is_video(state_manager.get_item('target_path')):
				read_static_video_frame(state_manager.get_item('target_path'), state_manager.get_item('reference_frame_number'))
			else:
				read_static_image(state_manager.get_item('target_path'))

			with ThreadPoolExecutor(max_workers = state_manager.get_item('execution_thread_count')) as executor:
				futures : Deque[Future[bool]] = deque()

				for frame_number, temp_frame_path in temp_frame_set.items():
					future = executor.submit(process_disk_frame, temp_frame_path, frame_number)
					futures.append(future)

				while futures:
					future = futures.popleft()

					if is_process_stopping():

						for pending_future in futures:
							pending_future.cancel()

						futures.clear()

					else:
						future.result()
						progress.update()

		for processor_module in get_processors_modules(state_manager.get_item('processors')):
			processor_module.post_process()

		if is_process_stopping():
			return 4
	else:
		logger.error(translator.get('temp_frames_not_found'), __name__)
		return 1
	return 0


def process_memory_frame(frame_number : int, temp_video_resolution : Resolution, output_video_resolution : Resolution) -> VisionFrame:
	target_vision_frames = conditional_get_target_vision_frames(frame_number)
	target_vision_frame = get_middle(target_vision_frames)
	temp_vision_frame = target_vision_frame.copy()

	if not (target_vision_frame.shape[1], target_vision_frame.shape[0]) == temp_video_resolution:
		temp_vision_frame = cv2.resize(target_vision_frame, temp_video_resolution)

	temp_vision_frame = process_temp_frame(target_vision_frames, temp_vision_frame, frame_number)

	if not (temp_vision_frame.shape[1], temp_vision_frame.shape[0]) == output_video_resolution:
		temp_vision_frame = cv2.resize(temp_vision_frame, output_video_resolution)

	if state_manager.get_item('temp_pixel_format') == 'bgra':
		temp_vision_frame = cv2.cvtColor(temp_vision_frame, cv2.COLOR_BGR2BGRA)

	if state_manager.get_item('temp_pixel_format') == 'bgr24':
		temp_vision_frame = temp_vision_frame[:, :, :3]

	return numpy.ascontiguousarray(temp_vision_frame)


def process_memory_frames() -> ErrorCode:
	target_path = state_manager.get_item('target_path')
	trim_frame_start, trim_frame_end = restrict_trim_frame(target_path, state_manager.get_item('trim_frame_start'), state_manager.get_item('trim_frame_end')) if is_video(target_path) else (state_manager.get_item('trim_frame_start') or 0, state_manager.get_item('trim_frame_end'))
	output_video_resolution = resolve_output_video_resolution(target_path)
	temp_video_resolution = resolve_temp_video_resolution(target_path)
	temp_video_fps = resolve_temp_video_fps(target_path)
	temp_frame_total = resolve_video_frame_total(target_path, temp_video_fps, trim_frame_start, trim_frame_end)
	temp_frame_range = range(trim_frame_start, trim_frame_start + temp_frame_total)

	if temp_frame_range:
		video_writer = video_manager.get_writer(target_path, temp_video_fps, output_video_resolution, output_video_resolution, state_manager.get_item('output_video_fps'))

		with tqdm(total = len(temp_frame_range), desc = translator.get('processing'), unit = 'frame', ascii = ' =', disable = state_manager.get_item('log_level') in [ 'warn', 'error' ]) as progress:
			progress.set_postfix(execution_providers = state_manager.get_item('execution_providers'))

			if is_video(target_path):
				read_static_video_frame(target_path, state_manager.get_item('reference_frame_number'))
			else:
				read_static_image(target_path)

			with ThreadPoolExecutor(max_workers = state_manager.get_item('execution_thread_count')) as executor:
				futures : Deque[Future[VisionFrame]] = deque()

				for frame_number in temp_frame_range:
					future = executor.submit(process_memory_frame, frame_number, temp_video_resolution, output_video_resolution)
					futures.append(future)

				while futures:
					future = futures.popleft()

					if is_process_stopping():

						for pending_future in futures:
							pending_future.cancel()

						futures.clear()

					else:
						video_manager.write_video_frame(video_writer, future.result())
						progress.update()

		if not video_manager.close_video_writer(video_writer):
			process_manager.stop()

		for processor_module in get_processors_modules(state_manager.get_item('processors')):
			processor_module.post_process()

		if is_process_stopping():
			return 4
	else:
		logger.error(translator.get('temp_frames_not_found'), __name__)
		return 1
	return 0


def merge_frames() -> ErrorCode:
	target_path = state_manager.get_item('target_path')
	trim_frame_start, trim_frame_end = restrict_trim_frame(target_path, state_manager.get_item('trim_frame_start'), state_manager.get_item('trim_frame_end')) if is_video(target_path) else (0, 0)
	output_video_resolution = resolve_output_video_resolution(target_path)
	temp_video_fps = resolve_temp_video_fps(target_path)

	logger.info(translator.get('merging_video').format(resolution = pack_resolution(output_video_resolution), fps = state_manager.get_item('output_video_fps')), __name__)
	if ffmpeg.merge_video(target_path, temp_video_fps, output_video_resolution, state_manager.get_item('output_video_fps'), trim_frame_start, trim_frame_end):
		logger.debug(translator.get('merging_video_succeeded'), __name__)
	else:
		if is_process_stopping():
			return 4
		logger.error(translator.get('merging_video_failed'), __name__)
		return 1
	return 0


def restore_audio() -> ErrorCode:
	target_path = state_manager.get_item('target_path')
	trim_frame_start, trim_frame_end = restrict_trim_frame(target_path, state_manager.get_item('trim_frame_start'), state_manager.get_item('trim_frame_end')) if is_video(target_path) else (0, 0)

	if state_manager.get_item('output_audio_volume') == 0:
		logger.info(translator.get('skipping_audio'), __name__)
		move_temp_file(target_path, state_manager.get_item('output_path'))
	else:
		source_audio_path = get_first(filter_audio_paths(state_manager.get_item('source_paths')))
		if source_audio_path:
			if ffmpeg.replace_audio(target_path, source_audio_path, state_manager.get_item('output_path')):
				video_manager.clear_video_pool()
				logger.debug(translator.get('replacing_audio_succeeded'), __name__)
			else:
				video_manager.clear_video_pool()
				if is_process_stopping():
					return 4
				logger.warn(translator.get('replacing_audio_skipped'), __name__)
				move_temp_file(target_path, state_manager.get_item('output_path'))
		elif is_image(target_path):
			source_video_paths = filter_video_paths(state_manager.get_item('source_paths'))
			driving_video_path = get_first(source_video_paths)
			if driving_video_path and ffmpeg.replace_audio(target_path, driving_video_path, state_manager.get_item('output_path')):
				video_manager.clear_video_pool()
				logger.debug(translator.get('replacing_audio_succeeded'), __name__)
			else:
				video_manager.clear_video_pool()
				move_temp_file(target_path, state_manager.get_item('output_path'))
		else:
			if ffmpeg.restore_audio(target_path, state_manager.get_item('output_path'), trim_frame_start, trim_frame_end):
				video_manager.clear_video_pool()
				logger.debug(translator.get('restoring_audio_succeeded'), __name__)
			else:
				video_manager.clear_video_pool()
				if is_process_stopping():
					return 4
				logger.warn(translator.get('restoring_audio_skipped'), __name__)
				move_temp_file(target_path, state_manager.get_item('output_path'))
	return 0


def finalize_video(start_time : float) -> ErrorCode:
	if is_video(state_manager.get_item('output_path')):
		logger.info(translator.get('processing_video_succeeded').format(seconds = calculate_end_time(start_time)), __name__)
	else:
		logger.error(translator.get('processing_video_failed'), __name__)
		return 1
	return 0
