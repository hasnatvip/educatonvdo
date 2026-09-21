
from functools import lru_cache

from educationvdo.types import Fps, VisionFrame


def pre_check() -> bool:
	"""
	Compatibility function.

	NSFW/content analysis is disabled.
	"""
	return True


def get_inference_pool():
	"""
	NSFW inference is disabled.

	Returns None instead of creating an inference pool.
	"""
	return None


def clear_inference_pool() -> None:
	"""
	NSFW inference is disabled.
	"""
	return None


def collect_model_downloads():
	"""
	NSFW model downloads are disabled.
	"""
	return {}, {}


def create_static_model_set(download_scope):
	"""
	NSFW models are disabled.

	Returning an empty dictionary prevents the NSFW models
	from being downloaded by the force-download mechanism.
	"""
	return {}


def analyse_stream(
	vision_frame: VisionFrame,
	video_fps: Fps
) -> bool:
	"""
	NSFW checking disabled.

	Returns False so the frame is never flagged as NSFW.
	"""
	return False


def analyse_frame(
	vision_frame: VisionFrame
) -> bool:
	"""
	NSFW checking disabled.

	Returns False so the frame is never flagged as NSFW.
	"""
	return False


@lru_cache()
def analyse_image(
	image_path: str
) -> bool:
	"""
	NSFW checking disabled.

	Returns False so the image is never flagged as NSFW.
	"""
	return False


@lru_cache()
def analyse_video(
	video_path: str,
	trim_frame_start: int,
	trim_frame_end: int
) -> bool:
	"""
	NSFW checking disabled.

	Returns False so the video is never flagged as NSFW.
	"""
	return False
