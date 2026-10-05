from typing import List, Literal, TypedDict

from educationvdo.types import Mask, VisionFrame

FaceAnimatorInputs = TypedDict('FaceAnimatorInputs',
{
	'reference_vision_frame' : VisionFrame,
	'source_vision_frames' : List[VisionFrame],
	'target_vision_frames' : List[VisionFrame],
	'temp_vision_frame' : VisionFrame,
	'temp_vision_mask' : Mask
})

FaceAnimatorModel = Literal['live_portrait']
