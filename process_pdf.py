import fitz  # PyMuPDF
import base64
import io
import os
from openai import OpenAI
from PIL import Image

# 1. Setup
client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
PDF_PATH = '/home/rmodi/turing/turing_archive/amt-d-9.pdf'
FIGURES_DIR = "figures"
os.makedirs(FIGURES_DIR, exist_ok=True)

def process_manuscript(pdf_path):
    doc = fitz.open(pdf_path)
    all_pages_latex = []

    for page_num in range(len(doc)):
        print(f"Processing page {page_num + 1}/{len(doc)}...")
        page = doc.load_page(page_num)
        
        # 2. Extract unique figures only
        # Use a dict to store unique XREFs and avoid duplicate extractions
        images = list(dict.fromkeys(page.get_images(full=True)))
        fig_paths = []
        
        for i, img_info in enumerate(images):
            xref = img_info[0]
            pix = fitz.Pixmap(doc, xref)
            
            # Save to 'figures/' folder
            fig_name = f"page_{page_num}_fig_{i}.png"
            fig_path = os.path.join(FIGURES_DIR, fig_name)
            pix.save(fig_path)
            fig_paths.append(fig_name)
            print(f"Extracted: {fig_path}")

        # 3. Contextual image for VLM
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        # 4. Refined Prompt (Forces correct file paths)
        prompt = (
            "You are an expert transcriber. Transcribe the manuscript text and insert "
            "these extracted figures at the correct locations using LaTeX. "
            f"Available figures: {fig_paths}. "
            "Use: \\begin{figure}[h] \\centering \\includegraphics[width=0.8\\textwidth]{figures/FILENAME} \\caption{...} \\end{figure}. "
            "IMPORTANT: Only use the filenames listed in the 'Available figures' list above. "
        )

        response = client.chat.completions.create(
            model="Qwen/Qwen3-VL-32B-Instruct",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}]
        )
        
        all_pages_latex.append(response.choices[0].message.content)
        print(f"Processed page {page_num + 1}")
        # if page_num >= 4:  # For testing, limit to first 5 pages
        #     break
    # 5. Save master document with LaTeX Boilerplate
    with open("master_document.tex", "w",encoding="utf-8") as f:
        f.write(r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{graphicx}
\usepackage{amsmath}

\begin{document}
""")
        f.write("\n\n".join(all_pages_latex))
        f.write("\n\n\\end{document}")

    print("Done! master_document.tex is ready.")

if __name__ == "__main__":
    process_manuscript(PDF_PATH)