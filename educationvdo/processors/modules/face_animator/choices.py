from typing import List, Sequence, get_args

from educationvdo.common_helper import create_float_range
from educationvdo.processors.modules.face_animator.types import FaceAnimatorModel

face_animator_models : List[FaceAnimatorModel] = list(get_args(FaceAnimatorModel))

face_animator_motion_scale_range : Sequence[float] = create_float_range(0.0, 2.0, 0.05)
face_animator_head_pose_ratio_range : Sequence[float] = create_float_range(0.0, 2.0, 0.05)
face_animator_expression_ratio_range : Sequence[float] = create_float_range(0.0, 2.0, 0.05)
face_animator_eye_open_ratio_range : Sequence[float] = create_float_range(0.0, 2.0, 0.05)
face_animator_lip_open_ratio_range : Sequence[float] = create_float_range(0.0, 2.0, 0.05)
