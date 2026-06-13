source .venv/bin/activate
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
vllm serve Qwen/Qwen3-VL-32B-Instruct \
    --tensor-parallel-size 2 \
    --gpu-memory-utilization 0.90 \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --trust-remote-code \
    --port 8000