import ctypes
import glob
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from functools import lru_cache
from typing import List, Optional, Tuple


def preload_cuda_libraries() -> None:
	if sys.platform.startswith('linux'):
		search_paths = []

		for path in sys.path:
			if os.path.isdir(path) and ('site-packages' in path or 'dist-packages' in path):
				nvidia_dir = os.path.join(path, 'nvidia')
				if os.path.isdir(nvidia_dir):
					for sub in os.listdir(nvidia_dir):
						lib_dir = os.path.join(nvidia_dir, sub, 'lib')
						if os.path.isdir(lib_dir):
							search_paths.append(lib_dir)

		for cuda_dir in [ '/usr/local/cuda/lib64', '/usr/local/cuda-12/lib64', '/usr/local/cuda-12.0/lib64', '/usr/local/cuda-12.1/lib64', '/usr/local/cuda-12.2/lib64', '/usr/local/cuda-12.3/lib64', '/usr/local/cuda-12.4/lib64', '/usr/local/cuda-12.5/lib64', '/usr/local/cuda-12.6/lib64', '/usr/local/cuda-12.8/lib64' ]:
			if os.path.isdir(cuda_dir):
				search_paths.append(cuda_dir)

		if search_paths:
			existing_ld = os.environ.get('LD_LIBRARY_PATH', '')
			new_paths = [ p for p in search_paths if p not in existing_ld.split(':') ]
			if new_paths:
				os.environ['LD_LIBRARY_PATH'] = ':'.join(new_paths + ([ existing_ld ] if existing_ld else []))

			priority_prefixes =\
			[
				'libcuda.so',
				'libculibos.so',
				'libcurand.so',
				'libcufft.so',
				'libcublasLt.so',
				'libcublas.so',
				'libcudnn_ops.so',
				'libcudnn_cnn.so',
				'libcudnn_adv.so',
				'libcudnn_graph.so',
				'libcudnn_engines_runtime_compiled.so',
				'libcudnn_engines_precompiled.so',
				'libcudnn_heuristic.so',
				'libcudnn.so'
			]
			for prefix in priority_prefixes:
				for directory in search_paths:
					for file_path in sorted(glob.glob(os.path.join(directory, prefix + '*'))):
						try:
							ctypes.CDLL(file_path, mode = ctypes.RTLD_GLOBAL)
						except Exception:
							pass

			for directory in search_paths:
				for file_path in sorted(glob.glob(os.path.join(directory, 'libcudnn*.so*'))):
					try:
						ctypes.CDLL(file_path, mode = ctypes.RTLD_GLOBAL)
					except Exception:
						pass


preload_cuda_libraries()

import onnxruntime

if hasattr(onnxruntime, 'preload_dlls'):
	try:
		onnxruntime.preload_dlls()
	except Exception:
		pass

import educationvdo.choices
from educationvdo.filesystem import create_directory, is_directory
from educationvdo.types import ExecutionDevice, ExecutionProvider, InferenceOptionSet, InferenceProvider, ValueAndUnit

onnxruntime.set_default_logger_severity(3)


def has_execution_provider(execution_provider : ExecutionProvider) -> bool:
	return execution_provider in get_available_execution_providers()


@lru_cache()
def get_onnxruntime_version() -> Tuple[int, int, int]:
	version_split = onnxruntime.get_version_string().split('.')
	major_version = int(version_split[0])
	minor_version = int(version_split[1])
	patch_version = int(version_split[2].split('+')[0])

	return major_version, minor_version, patch_version


def get_available_execution_providers() -> List[ExecutionProvider]:
	inference_session_providers = onnxruntime.get_available_providers()
	available_execution_providers : List[ExecutionProvider] = []

	for execution_provider, execution_provider_value in educationvdo.choices.execution_provider_set.items():
		if execution_provider_value in inference_session_providers:
			index = educationvdo.choices.execution_providers.index(execution_provider)
			available_execution_providers.insert(index, execution_provider)

	return available_execution_providers


def create_inference_providers(execution_device_id : int, execution_providers : List[ExecutionProvider]) -> List[InferenceProvider]:
	inference_providers : List[InferenceProvider] = []
	cache_path = resolve_cache_path()

	for execution_provider in execution_providers:
		if execution_provider == 'cuda':
			inference_providers.append((educationvdo.choices.execution_provider_set.get(execution_provider),
			{
				'device_id': execution_device_id,
				'cudnn_conv_algo_search': resolve_cudnn_conv_algo_search()
			}))

		if execution_provider == 'tensorrt':
			inference_option_set : InferenceOptionSet =\
			{
				'device_id': execution_device_id
			}
			if is_directory(cache_path) or create_directory(cache_path):
				inference_option_set.update(
				{
					'trt_engine_cache_enable': True,
					'trt_engine_cache_path': cache_path,
					'trt_timing_cache_enable': True,
					'trt_timing_cache_path': cache_path,
					'trt_builder_optimization_level': 4
				})
			inference_providers.append((educationvdo.choices.execution_provider_set.get(execution_provider), inference_option_set))

		if execution_provider in [ 'directml', 'rocm' ]:
			inference_providers.append((educationvdo.choices.execution_provider_set.get(execution_provider),
			{
				'device_id': execution_device_id
			}))

		if execution_provider == 'migraphx':
			inference_option_set =\
			{
				'device_id': execution_device_id
			}
			if is_directory(cache_path) or create_directory(cache_path):
				inference_option_set.update(
				{
					'migraphx_model_cache_dir': cache_path
				})
			inference_providers.append((educationvdo.choices.execution_provider_set.get(execution_provider), inference_option_set))

		if execution_provider == 'coreml':
			inference_option_set =\
			{
				'SpecializationStrategy': 'FastPrediction'
			}
			if is_directory(cache_path) or create_directory(cache_path):
				inference_option_set.update(
				{
					'ModelCacheDirectory': cache_path
				})
			inference_providers.append((educationvdo.choices.execution_provider_set.get(execution_provider), inference_option_set))

		if execution_provider == 'openvino':
			inference_providers.append((educationvdo.choices.execution_provider_set.get(execution_provider),
			{
				'device_type': resolve_openvino_device_type(execution_device_id),
				'precision': 'FP32'
			}))

		if execution_provider == 'qnn':
			inference_providers.append((educationvdo.choices.execution_provider_set.get(execution_provider),
			{
				'device_id': execution_device_id,
				'backend_type': 'htp'
			}))

	if 'cpu' in execution_providers:
		inference_providers.append(educationvdo.choices.execution_provider_set.get('cpu'))

	return inference_providers


def resolve_cache_path() -> str:
	return os.path.join('.caches', onnxruntime.get_version_string())


def resolve_cudnn_conv_algo_search() -> str:
	if 'EDUCATIONVDO_CUDNN_CONV_ALGO_SEARCH' in os.environ:
		return os.environ['EDUCATIONVDO_CUDNN_CONV_ALGO_SEARCH']

	execution_devices = detect_static_execution_devices()
	product_names = (
		'GeForce GTX 1630', 'GeForce GTX 1650', 'GeForce GTX 1660',
		'Tesla T4', 'T4', 'Tesla',
		'GeForce RTX 2060', 'GeForce RTX 2070', 'GeForce RTX 2080',
		'TITAN RTX', 'Quadro T'
	)

	for execution_device in execution_devices:
		product_name = execution_device.get('product', {}).get('name', '')
		if any(name in product_name for name in product_names):
			return 'DEFAULT'

	return 'DEFAULT'


def resolve_openvino_device_type(execution_device_id : int) -> str:
	if execution_device_id == 0:
		return 'GPU'
	return 'GPU.' + str(execution_device_id)


def run_nvidia_smi() -> subprocess.Popen[bytes]:
	commands = [ shutil.which('nvidia-smi'), '--query', '--xml-format' ]
	return subprocess.Popen(commands, stdout = subprocess.PIPE)


@lru_cache()
def detect_static_execution_devices() -> List[ExecutionDevice]:
	return detect_execution_devices()


def detect_execution_devices() -> List[ExecutionDevice]:
	execution_devices : List[ExecutionDevice] = []

	try:
		output, _ = run_nvidia_smi().communicate()
		root_element = ElementTree.fromstring(output)
	except Exception:
		root_element = ElementTree.Element('xml')

	for gpu_element in root_element.findall('gpu'):
		execution_devices.append(
		{
			'driver_version': root_element.findtext('driver_version'),
			'framework':
			{
				'name': 'CUDA',
				'version': root_element.findtext('cuda_version')
			},
			'product':
			{
				'vendor': 'NVIDIA',
				'name': gpu_element.findtext('product_name').replace('NVIDIA', '').strip()
			},
			'video_memory':
			{
				'total': create_value_and_unit(gpu_element.findtext('fb_memory_usage/total')),
				'free': create_value_and_unit(gpu_element.findtext('fb_memory_usage/free'))
			},
			'temperature':
			{
				'gpu': create_value_and_unit(gpu_element.findtext('temperature/gpu_temp')),
				'memory': create_value_and_unit(gpu_element.findtext('temperature/memory_temp'))
			},
			'utilization':
			{
				'gpu': create_value_and_unit(gpu_element.findtext('utilization/gpu_util')),
				'memory': create_value_and_unit(gpu_element.findtext('utilization/memory_util'))
			}
		})

	return execution_devices


def create_value_and_unit(text : str) -> Optional[ValueAndUnit]:
	if ' ' in text:
		value, unit = text.split()

		return\
		{
			'value': int(value),
			'unit': str(unit)
		}
	return None
