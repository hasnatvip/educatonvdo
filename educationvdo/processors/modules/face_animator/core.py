from argparse import ArgumentParser
from functools import lru_cache
from types import ModuleType
from typing import List, Optional, Tuple

import cv2
import numpy

import educationvdo.jobs.job_manager
import educationvdo.jobs.job_store
from educationvdo import config, content_analyser, face_classifier, face_detector, face_landmarker, face_masker, face_recognizer, inference_manager, logger, state_manager, translator, video_manager, voice_extractor
from educationvdo.common_helper import create_float_metavar, get_first, get_middle
from educationvdo.download import conditional_download_hashes, conditional_download_sources, resolve_download_url
from educationvdo.face_creator import get_many_faces, scale_face
from educationvdo.face_helper import create_bounding_box, paste_back, scale_face_landmark_5, warp_face_by_face_landmark_5
from educationvdo.face_masker import create_box_mask, create_occlusion_mask
from educationvdo.face_selector import select_faces
from educationvdo.filesystem import in_directory, is_image, is_video, resolve_relative_path, same_file_extension
from educationvdo.processors.live_portrait import create_rotation, limit_expression
from educationvdo.processors.modules.face_animator import choices as face_animator_choices
from educationvdo.processors.modules.face_animator.types import FaceAnimatorInputs
from educationvdo.processors.types import LivePortraitExpression, LivePortraitFeatureVolume, LivePortraitMotionPoints, LivePortraitPitch, LivePortraitRoll, LivePortraitRotation, LivePortraitScale, LivePortraitTranslation, LivePortraitYaw, ProcessorOutputs
from educationvdo.program_helper import find_argument_group
from educationvdo.thread_helper import conditional_thread_semaphore, thread_semaphore
from educationvdo.types import ApplyStateItem, Args, DownloadScope, Face, FaceLandmark68, InferencePool, ModelOptions, ModelSet, ProcessMode, VisionFrame
from educationvdo.vision import read_static_image, read_static_video_frame

DRIVING_BASELINE : Optional[Tuple[LivePortraitPitch, LivePortraitYaw, LivePortraitRoll, LivePortraitExpression]] = None


@lru_cache()
def create_static_model_set(download_scope : DownloadScope) -> ModelSet:
	return\
	{
		'live_portrait':
		{
			'__metadata__':
			{
				'vendor': 'KwaiVGI',
				'license': 'MIT',
				'year': 2024
			},
			'hashes':
			{
				'feature_extractor':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_feature_extractor.hash'),
					'path': resolve_relative_path('../.assets/models/live_portrait_feature_extractor.hash')
				},
				'motion_extractor':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_motion_extractor.hash'),
					'path': resolve_relative_path('../.assets/models/live_portrait_motion_extractor.hash')
				},
				'eye_retargeter':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_eye_retargeter.hash'),
					'path': resolve_relative_path('../.assets/models/live_portrait_eye_retargeter.hash')
				},
				'lip_retargeter':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_lip_retargeter.hash'),
					'path': resolve_relative_path('../.assets/models/live_portrait_lip_retargeter.hash')
				},
				'stitcher':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_stitcher.hash'),
					'path': resolve_relative_path('../.assets/models/live_portrait_stitcher.hash')
				},
				'generator':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_generator.hash'),
					'path': resolve_relative_path('../.assets/models/live_portrait_generator.hash')
				}
			},
			'sources':
			{
				'feature_extractor':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_feature_extractor.onnx'),
					'path': resolve_relative_path('../.assets/models/live_portrait_feature_extractor.onnx')
				},
				'motion_extractor':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_motion_extractor.onnx'),
					'path': resolve_relative_path('../.assets/models/live_portrait_motion_extractor.onnx')
				},
				'eye_retargeter':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_eye_retargeter.onnx'),
					'path': resolve_relative_path('../.assets/models/live_portrait_eye_retargeter.onnx')
				},
				'lip_retargeter':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_lip_retargeter.onnx'),
					'path': resolve_relative_path('../.assets/models/live_portrait_lip_retargeter.onnx')
				},
				'stitcher':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_stitcher.onnx'),
					'path': resolve_relative_path('../.assets/models/live_portrait_stitcher.onnx')
				},
				'generator':
				{
					'url': resolve_download_url('models-3.0.0', 'live_portrait_generator.onnx'),
					'path': resolve_relative_path('../.assets/models/live_portrait_generator.onnx')
				}
			},
			'template': 'ffhq_512',
			'size': (512, 512)
		}
	}


def get_inference_pool() -> InferencePool:
	model_names = [ state_manager.get_item('face_animator_model') ]
	model_source_set = get_model_options().get('sources')

	return inference_manager.get_inference_pool(__name__, model_names, model_source_set)


def clear_inference_pool() -> None:
	model_names = [ state_manager.get_item('face_animator_model') ]
	inference_manager.clear_inference_pool(__name__, model_names)


def get_model_options() -> ModelOptions:
	model_name = state_manager.get_item('face_animator_model')
	return create_static_model_set('full').get(model_name)


def register_args(program : ArgumentParser) -> None:
	group_processors = find_argument_group(program, 'processors')
	if group_processors:
		group_processors.add_argument('--face-animator-model', help = translator.get('help.model', __package__), default = config.get_str_value('processors', 'face_animator_model', 'live_portrait'), choices = face_animator_choices.face_animator_models)
		group_processors.add_argument('--face-animator-motion-scale', help = translator.get('help.motion_scale', __package__), type = float, default = config.get_float_value('processors', 'face_animator_motion_scale', '1.0'), choices = face_animator_choices.face_animator_motion_scale_range, metavar = create_float_metavar(face_animator_choices.face_animator_motion_scale_range))
		group_processors.add_argument('--face-animator-head-pose-ratio', help = translator.get('help.head_pose_ratio', __package__), type = float, default = config.get_float_value('processors', 'face_animator_head_pose_ratio', '1.0'), choices = face_animator_choices.face_animator_head_pose_ratio_range, metavar = create_float_metavar(face_animator_choices.face_animator_head_pose_ratio_range))
		group_processors.add_argument('--face-animator-expression-ratio', help = translator.get('help.expression_ratio', __package__), type = float, default = config.get_float_value('processors', 'face_animator_expression_ratio', '1.0'), choices = face_animator_choices.face_animator_expression_ratio_range, metavar = create_float_metavar(face_animator_choices.face_animator_expression_ratio_range))
		group_processors.add_argument('--face-animator-eye-open-ratio', help = translator.get('help.eye_open_ratio', __package__), type = float, default = config.get_float_value('processors', 'face_animator_eye_open_ratio', '1.0'), choices = face_animator_choices.face_animator_eye_open_ratio_range, metavar = create_float_metavar(face_animator_choices.face_animator_eye_open_ratio_range))
		group_processors.add_argument('--face-animator-lip-open-ratio', help = translator.get('help.lip_open_ratio', __package__), type = float, default = config.get_float_value('processors', 'face_animator_lip_open_ratio', '1.0'), choices = face_animator_choices.face_animator_lip_open_ratio_range, metavar = create_float_metavar(face_animator_choices.face_animator_lip_open_ratio_range))
		group_processors.add_argument('--face-animator-relative', help = translator.get('help.relative', __package__), default = config.get_bool_value('processors', 'face_animator_relative', 'True'), action = 'store_true')
		educationvdo.jobs.job_store.register_step_keys([ 'face_animator_model', 'face_animator_motion_scale', 'face_animator_head_pose_ratio', 'face_animator_expression_ratio', 'face_animator_eye_open_ratio', 'face_animator_lip_open_ratio', 'face_animator_relative' ])


def apply_args(args : Args, apply_state_item : ApplyStateItem) -> None:
	apply_state_item('face_animator_model', args.get('face_animator_model'))
	apply_state_item('face_animator_motion_scale', args.get('face_animator_motion_scale'))
	apply_state_item('face_animator_head_pose_ratio', args.get('face_animator_head_pose_ratio'))
	apply_state_item('face_animator_expression_ratio', args.get('face_animator_expression_ratio'))
	apply_state_item('face_animator_eye_open_ratio', args.get('face_animator_eye_open_ratio'))
	apply_state_item('face_animator_lip_open_ratio', args.get('face_animator_lip_open_ratio'))
	apply_state_item('face_animator_relative', args.get('face_animator_relative'))


def get_common_modules() -> List[ModuleType]:
	return [ content_analyser, face_classifier, face_detector, face_landmarker, face_masker, face_recognizer, voice_extractor ]


def pre_check() -> bool:
	model_hash_set = get_model_options().get('hashes')
	model_source_set = get_model_options().get('sources')

	for common_module in get_common_modules():
		if not common_module.pre_check():
			return False

	return conditional_download_hashes(model_hash_set) and conditional_download_sources(model_source_set)


def pre_process(mode : ProcessMode) -> bool:
	if mode == 'stream':
		logger.error(translator.get('stream_not_supported') + translator.get('exclamation_mark'), __name__)
		return False
	if mode in [ 'output', 'preview' ] and not is_image(state_manager.get_item('target_path')) and not is_video(state_manager.get_item('target_path')):
		logger.error(translator.get('choose_image_or_video_target') + translator.get('exclamation_mark'), __name__)
		return False
	if mode == 'output' and not in_directory(state_manager.get_item('output_path')):
		logger.error(translator.get('specify_image_or_video_output') + translator.get('exclamation_mark'), __name__)
		return False
	return True


def post_process() -> None:
	global DRIVING_BASELINE
	DRIVING_BASELINE = None
	read_static_image.cache_clear()
	read_static_video_frame.cache_clear()
	video_manager.clear_video_pool()

	if state_manager.get_item('video_memory_strategy') in [ 'strict', 'moderate' ]:
		clear_inference_pool()

	if state_manager.get_item('video_memory_strategy') == 'strict':
		for common_module in get_common_modules():
			common_module.clear_inference_pool()


def forward_extract_feature(crop_vision_frame : VisionFrame) -> LivePortraitFeatureVolume:
	feature_extractor = get_inference_pool().get('feature_extractor')

	with conditional_thread_semaphore():
		feature_volume = feature_extractor.run(None,
		{
			'input': crop_vision_frame
		})[0]

	return feature_volume


def forward_extract_motion(crop_vision_frame : VisionFrame) -> Tuple[LivePortraitPitch, LivePortraitYaw, LivePortraitRoll, LivePortraitScale, LivePortraitTranslation, LivePortraitExpression, LivePortraitMotionPoints]:
	motion_extractor = get_inference_pool().get('motion_extractor')

	with conditional_thread_semaphore():
		pitch, yaw, roll, scale, translation, expression, motion_points = motion_extractor.run(None,
		{
			'input': crop_vision_frame
		})

	return pitch, yaw, roll, scale, translation, expression, motion_points


def forward_retarget_eye(eye_motion_points : LivePortraitMotionPoints) -> LivePortraitMotionPoints:
	eye_retargeter = get_inference_pool().get('eye_retargeter')

	with conditional_thread_semaphore():
		eye_motion_points = eye_retargeter.run(None,
		{
			'input': eye_motion_points
		})[0]

	return eye_motion_points


def forward_retarget_lip(lip_motion_points : LivePortraitMotionPoints) -> LivePortraitMotionPoints:
	lip_retargeter = get_inference_pool().get('lip_retargeter')

	with conditional_thread_semaphore():
		lip_motion_points = lip_retargeter.run(None,
		{
			'input': lip_motion_points
		})[0]

	return lip_motion_points


def forward_stitch_motion_points(source_motion_points : LivePortraitMotionPoints, target_motion_points : LivePortraitMotionPoints) -> LivePortraitMotionPoints:
	stitcher = get_inference_pool().get('stitcher')

	with thread_semaphore():
		motion_points = stitcher.run(None,
		{
			'source': source_motion_points,
			'target': target_motion_points
		})[0]

	return motion_points


def forward_generate_frame(feature_volume : LivePortraitFeatureVolume, source_motion_points : LivePortraitMotionPoints, target_motion_points : LivePortraitMotionPoints) -> VisionFrame:
	generator = get_inference_pool().get('generator')

	with thread_semaphore():
		crop_vision_frame = generator.run(None,
		{
			'feature_volume': feature_volume,
			'source': source_motion_points,
			'target': target_motion_points
		})[0][0]

	return crop_vision_frame


def prepare_crop_frame(crop_vision_frame : VisionFrame) -> VisionFrame:
	model_size = get_model_options().get('size')
	prepare_size = (model_size[0] // 2, model_size[1] // 2)
	crop_vision_frame = cv2.resize(crop_vision_frame, prepare_size, interpolation = cv2.INTER_AREA)
	crop_vision_frame = crop_vision_frame[:, :, ::-1] / 255.0
	crop_vision_frame = numpy.expand_dims(crop_vision_frame.transpose(2, 0, 1), axis = 0).astype(numpy.float32)
	return numpy.ascontiguousarray(crop_vision_frame)


def normalize_crop_frame(crop_vision_frame : VisionFrame) -> VisionFrame:
	crop_vision_frame = crop_vision_frame.transpose(1, 2, 0).clip(0, 1)
	crop_vision_frame = (crop_vision_frame * 255.0)
	crop_vision_frame = crop_vision_frame.astype(numpy.uint8)[:, :, ::-1]
	return crop_vision_frame


def animate_face(target_face : Face, driving_face : Optional[Face], driving_vision_frame : Optional[VisionFrame], temp_vision_frame : VisionFrame) -> VisionFrame:
	global DRIVING_BASELINE
	model_template = get_model_options().get('template')
	model_size = get_model_options().get('size')

	target_landmark_5 = scale_face_landmark_5(target_face.landmark_set.get('5/68'), 1.5)
	target_crop, affine_matrix = warp_face_by_face_landmark_5(temp_vision_frame, target_landmark_5, model_template, model_size)
	box_mask = create_box_mask(target_crop, state_manager.get_item('face_mask_blur'), (0, 0, 0, 0))

	target_crop_prepared = prepare_crop_frame(target_crop)
	feature_volume = forward_extract_feature(target_crop_prepared)
	pitch_t, yaw_t, roll_t, scale_t, trans_t, expr_t, motion_points_t = forward_extract_motion(target_crop_prepared)

	head_pose_ratio = float(state_manager.get_item('face_animator_head_pose_ratio') or 1.0)
	expression_ratio = float(state_manager.get_item('face_animator_expression_ratio') or 1.0)
	motion_scale = float(state_manager.get_item('face_animator_motion_scale') or 1.0)
	relative = bool(state_manager.get_item('face_animator_relative'))

	if driving_face is not None and driving_vision_frame is not None:
		driving_landmark_5 = scale_face_landmark_5(driving_face.landmark_set.get('5/68'), 1.5)
		driving_crop, _ = warp_face_by_face_landmark_5(driving_vision_frame, driving_landmark_5, model_template, model_size)
		driving_crop_prepared = prepare_crop_frame(driving_crop)
		pitch_d, yaw_d, roll_d, scale_d, trans_d, expr_d, motion_points_d = forward_extract_motion(driving_crop_prepared)

		if relative:
			if DRIVING_BASELINE is None:
				DRIVING_BASELINE = (pitch_d, yaw_d, roll_d, expr_d)

			b_pitch, b_yaw, b_roll, b_expr = DRIVING_BASELINE
			delta_pitch = (pitch_d - b_pitch) * head_pose_ratio * motion_scale
			delta_yaw = (yaw_d - b_yaw) * head_pose_ratio * motion_scale
			delta_roll = (roll_d - b_roll) * head_pose_ratio * motion_scale
			delta_expr = (expr_d - b_expr) * expression_ratio * motion_scale

			anim_pitch = pitch_t + delta_pitch
			anim_yaw = yaw_t + delta_yaw
			anim_roll = roll_t + delta_roll
			anim_expr = limit_expression(expr_t + delta_expr)
		else:
			anim_pitch = pitch_d * head_pose_ratio * motion_scale
			anim_yaw = yaw_d * head_pose_ratio * motion_scale
			anim_roll = roll_d * head_pose_ratio * motion_scale
			anim_expr = limit_expression(expr_d * expression_ratio * motion_scale)

		rotation_driven = create_rotation(anim_pitch, anim_yaw, anim_roll)
		motion_points_source = scale_t * (motion_points_t @ rotation_driven.T + anim_expr) + trans_t
	else:
		rotation_t = create_rotation(pitch_t, yaw_t, roll_t)
		motion_points_source = scale_t * (motion_points_t @ rotation_t.T + expr_t) + trans_t

	rotation_target = create_rotation(pitch_t, yaw_t, roll_t)
	motion_points_target = scale_t * (motion_points_t @ rotation_target.T + expr_t) + trans_t

	motion_points_stitched = forward_stitch_motion_points(motion_points_source, motion_points_target)
	crop_vision_frame = forward_generate_frame(feature_volume, motion_points_stitched, motion_points_target)
	crop_vision_frame = normalize_crop_frame(crop_vision_frame)

	crop_masks = [ box_mask ]
	if 'occlusion' in state_manager.get_item('face_mask_types'):
		crop_masks.append(create_occlusion_mask(target_crop))
	crop_mask = numpy.minimum.reduce(crop_masks).clip(0, 1)

	paste_vision_frame = paste_back(temp_vision_frame, crop_vision_frame, crop_mask, affine_matrix)
	return paste_vision_frame


def process_frame(inputs : FaceAnimatorInputs) -> ProcessorOutputs:
	reference_vision_frame = inputs.get('reference_vision_frame')
	source_vision_frames = inputs.get('source_vision_frames')
	target_vision_frames = inputs.get('target_vision_frames')
	temp_vision_frame = inputs.get('temp_vision_frame')
	temp_vision_mask = inputs.get('temp_vision_mask')

	target_vision_frame = get_middle(target_vision_frames)
	target_faces = select_faces(reference_vision_frame, source_vision_frames, target_vision_frames)

	driving_face = None
	driving_vision_frame = None

	if source_vision_frames:
		driving_vision_frame = get_first(source_vision_frames)
		if driving_vision_frame is not None:
			driving_faces = get_many_faces([ driving_vision_frame ])
			if driving_faces:
				driving_face = get_first(driving_faces)

	if target_faces:
		for target_face in target_faces:
			target_face = scale_face(target_face, target_vision_frame, temp_vision_frame)
			temp_vision_frame = animate_face(target_face, driving_face, driving_vision_frame, temp_vision_frame)

	return temp_vision_frame, temp_vision_mask
