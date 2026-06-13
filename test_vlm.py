# code to test qwen 3 vl across two gpus 
# few layers on gpu 0 and the rest on gpu 1 

import torch

from transformers import Qwen3VLForConditionalGeneration,AutoProcessor

model_id = "Qwen/Qwen3-VL-32B-Instruct"
model = Qwen3VLForConditionalGeneration.from_pretrained(
    model_id,
    torch_dtype="auto",
    device_map="auto",
    attn_implementation="sdpa" # or "flash_attention_2" if you have it installed
)


# 3. Load the processor
processor = AutoProcessor.from_pretrained(model_id)

# 4. Verify the split (Optional)
# This will print which layers were placed on which GPU (cuda:0, cuda:1)
print(model.hf_device_map)
