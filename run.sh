#!/bin/bash
source educationvdo-env/bin/activate
python educationvdo.py run --execution-providers coreml cpu --execution-thread-count 8 --video-memory-strategy tolerant
