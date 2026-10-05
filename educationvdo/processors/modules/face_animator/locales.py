from educationvdo.types import Locales

LOCALES : Locales =\
{
	'en':
	{
		'help':
		{
			'model': 'choose the model responsible for animating the face',
			'motion_scale': 'specify the overall motion scale',
			'head_pose_ratio': 'specify the head pose rotation ratio',
			'expression_ratio': 'specify the expression strength ratio',
			'eye_open_ratio': 'specify the eye open ratio',
			'lip_open_ratio': 'specify the lip open ratio',
			'relative': 'use relative motion driving instead of absolute'
		},
		'uis':
		{
			'model_dropdown': 'FACE ANIMATOR MODEL',
			'motion_scale_slider': 'FACE ANIMATOR MOTION SCALE',
			'head_pose_ratio_slider': 'FACE ANIMATOR HEAD POSE RATIO',
			'expression_ratio_slider': 'FACE ANIMATOR EXPRESSION RATIO',
			'eye_open_ratio_slider': 'FACE ANIMATOR EYE OPEN RATIO',
			'lip_open_ratio_slider': 'FACE ANIMATOR LIP OPEN RATIO',
			'relative_checkbox': 'FACE ANIMATOR RELATIVE DRIVING'
		}
	}
}
