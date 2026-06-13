conda create -n turing_archive python=3.10 -y
conda activate turing_archive
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu132
pip install "transformers[torch]"


source .venv/bin/activate
