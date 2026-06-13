import os
import shutil
import subprocess
import logging
from multiprocessing import Pool
from pdf2image import convert_from_path
from google import genai

# ==========================================
# 1. Logging Setup
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("processing_trace.log"), logging.StreamHandler()]
)

def log(msg, filename):
    logging.info(f"[{filename}] {msg}")

# ==========================================
# 2. Configuration
# ==========================================
API_KEY = "AIzaSyACloyikx6S1JqZfk3daRG9XTGwTMSWn7E"
MODEL_NAME = 'gemini-2.5-flash-lite'
MAX_CONCURRENT_FILES = 3
INPUT_DIR = "." 
OUTPUT_DIR = "./processed_pdfs"
WORK_DIR = "./workspace"

# REPAIRED TEMPLATE: 
# Braces used for LaTeX syntax (e.g., {article}) are doubled {{ }} to escape them.
# The single {} at the end is the ONLY injection point for .format()
LATEX_TEMPLATE = r"""\documentclass[11pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage{{amsmath, amssymb, amsfonts}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}
\usepackage[normalem]{{ulem}} 
\usepackage{{cancel}}        
\usepackage{{enumitem}}      
\usepackage{{geometry}}      
\geometry{{margin=1in}}
\begin{{document}}
{}
\end{{document}}
"""

def clean_output(text):
    text = text.replace(r"\begin{document}", "").replace(r"\end{document}", "")
    text = text.replace(r"\documentclass", "").replace("```latex", "").replace("```", "")
    return text.strip()

def init_worker(api_key):
    global client
    client = genai.Client(api_key=api_key)

def process_single_pdf(pdf_filename):
    if pdf_filename.startswith("processed_"):
        return

    pdf_base = os.path.splitext(pdf_filename)[0]
    workspace = os.path.join(WORK_DIR, pdf_base)
    figures_dir = os.path.join(workspace, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    log("Initializing workspace.", pdf_filename)
    
    try:
        pages = convert_from_path(pdf_filename, dpi=300)
    except Exception as e:
        log(f"FAILED during extraction: {e}", pdf_filename)
        return

    latex_content = ""
    
    for i, page_img in enumerate(pages):
        img_name = f"page_{i+1}.png"
        img_path = os.path.join(figures_dir, img_name)
        page_img.save(img_path, "PNG")
        
        log(f"Transcribing page {i+1}/{len(pages)}.", pdf_filename)
        
        prompt = (
            "Transcribe this handwritten page into LaTeX. "
            "Use \\sout{...} for strikethroughs, \\cancel{...} for math cancellations. "
            "Return ONLY the LaTeX body content. Do not include boilerplate."
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[page_img, prompt]
        )
        
        # Double {{ }} used to escape these braces within the f-string
        latex_content += f"""\\subsection*{{Page {i+1}}}
\\includegraphics[width=0.6\\textwidth]{{figures/{img_name}}}
\\begin{{quote}}{clean_output(response.text)}\\end{{quote}}\\newpage\n"""

    tex_path = os.path.join(workspace, "manuscript.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        # Uses .format() which now works because template braces are doubled
        f.write(LATEX_TEMPLATE.format(latex_content))

    log("Compiling with XeLaTeX.", pdf_filename)
    try:
        # Pass 1
        subprocess.run(["xelatex", "-interaction=nonstopmode", "manuscript.tex"], 
                       cwd=workspace, stdout=subprocess.DEVNULL)
        # Pass 2
        result = subprocess.run(["xelatex", "-interaction=nonstopmode", "manuscript.tex"], 
                                cwd=workspace, capture_output=True, text=True)
        
        if result.returncode == 0:
            shutil.move(os.path.join(workspace, "manuscript.pdf"), 
                        os.path.join(OUTPUT_DIR, f"processed_{pdf_filename}"))
            log("SUCCESS.", pdf_filename)
        else:
            log(f"COMPILATION FAILED: {result.stderr[-300:]}", pdf_filename)
    except Exception as e:
        log(f"SYSTEM ERROR: {e}", pdf_filename)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(WORK_DIR, exist_ok=True)
    
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf") 
             and not f.startswith("processed_")]
    
    if not files:
        print("No new PDF files found.")
        return

    print(f"Processing {len(files)} files...")
    with Pool(processes=MAX_CONCURRENT_FILES, initializer=init_worker, initargs=(API_KEY,)) as pool:
        pool.map(process_single_pdf, files)

if __name__ == "__main__":
    main()