import os
import shutil
import subprocess
import logging
import re
from multiprocessing import Pool
from pdf2image import convert_from_path
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential,wait_random_exponential

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
TRANSCRIPTION_MODEL = 'gemini-2.5-flash'  # Fast and cheap for page images
REFINEMENT_MODEL = 'gemini-2.5-pro'            # Deep reasoning for structural math cleanup
MAX_CONCURRENT_FILES = 6
INPUT_DIR = "." 
OUTPUT_DIR = "./processed_pdfs"  
WORK_DIR = "./workspace"

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
    if not text:
        return ""
    # 1. Remove markdown code blocks
    text = re.sub(r"```latex", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text, flags=re.IGNORECASE)
    
    # 2. Aggressively strip preamble commands
    text = re.sub(r"\\documentclass.*", "", text)
    text = re.sub(r"\\usepackage\{.*?\}", "", text)
    text = re.sub(r"\\begin\{document\}", "", text)
    text = re.sub(r"\\end\{document\}", "", text)
    
    # 3. Strip structural quote commands if they cause nesting issues
    text = text.replace(r"\begin{quote}", "").replace(r"\end{quote}", "")
    
    return text.strip()

def init_worker(api_key):
    global client
    client = genai.Client(api_key=api_key)

@retry(
    stop=stop_after_attempt(7), 
    wait=wait_random_exponential(multiplier=2, min=15, max=65),
    before_sleep=lambda retry_state: logging.warning(
        f"Rate limit hit (429). Retrying in {retry_state.next_action.sleep:.2f} seconds... (Attempt {retry_state.attempt_number}/7)"
    )
)
def call_gemini_with_retry(contents, prompt, is_image=True):
    if is_image:
        return client.models.generate_content(
            model=TRANSCRIPTION_MODEL,
            contents=[contents, prompt]
        )
    else:
        # Standardize text requests and route them to the stronger PRO model
        combined_payload = f"{prompt}\n\nINPUT TEXT TO REFINE:\n{contents}"
        return client.models.generate_content(
            model=REFINEMENT_MODEL,
            contents=combined_payload
        )

def process_single_pdf(pdf_filename):
    if pdf_filename.startswith("processed_"):
        return

    pdf_base = os.path.splitext(pdf_filename)[0]
    workspace = os.path.join(WORK_DIR, pdf_base)
    figures_dir = os.path.join(workspace, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    log("Initializing workspace.", pdf_filename)
    
    try:
        pages = convert_from_path(pdf_filename, dpi=150) 
    except Exception as e:
        log(f"FAILED during extraction: {e}", pdf_filename)
        return

    raw_latex_body = ""
    
    # PASS 1: Sequential Page Transcriptions (Using Flash-Lite)
    for i, page_img in enumerate(pages):
        img_name = f"page_{i+1}.png"
        img_path = os.path.join(figures_dir, img_name)
        page_img.save(img_path, "PNG")
        
        log(f"Transcribing page {i+1}/{len(pages)} (Pass 1 - Flash).", pdf_filename)
        
        prompt = (
            "Transcribe this handwritten math page into LaTeX. "
            "Output ONLY the LaTeX body content. "
            "DO NOT include: \\usepackage, \\documentclass, \\begin{document}, or \\end{document}. "
            "Ensure all math is properly closed with '$' or environment tags. "
        )
        
        try:
            response = call_gemini_with_retry(page_img, prompt, is_image=True)
            cleaned_page = clean_output(response.text)
            
            raw_latex_body += f"""\\subsection*{{Page {i+1}}}
\\includegraphics[width=0.6\\textwidth]{{figures/{img_name}}}
\\par {cleaned_page} \\newpage\n"""
        except Exception as e:
            log(f"FAILED page {i+1} during Pass 1: {e}", pdf_filename)
            raw_latex_body += f"\\subsection*{{Page {i+1}}} \\par \\textit{{Transcription failed.}} \\newpage\n"

    # PASS 2: Global Document Refinement (Using Pro - No Compilation)
    log("Refining full document syntax (Pass 2 - Gemini Pro).", pdf_filename)
    refinement_prompt = (
        "You are an expert LaTeX proofreader. Review the provided input document containing multi-page transcription math. "
        "Fix common compilation bugs globally: ensure all math inline or display environments match, "
        "ensure all braces are closed correctly, convert unmatched or dangling \\left/\\right markers into generic formatting "
        "like standard parenthesis if necessary, and escape naked '&' markers outside of tables or matrices. "
        "DO NOT delete the actual mathematical text or sentences under any circumstance. "
        "Preserve the structural page breaks (\\newpage) and image macros intact. "
        "Output ONLY the corrected body markup text without any markdown or code wrappers."
    )
    
    try:
        refinement_response = call_gemini_with_retry(raw_latex_body, refinement_prompt, is_image=False)
        final_latex_body = clean_output(refinement_response.text)
    except Exception as e:
        log(f"Refinement Pass 2 failed. Falling back to Pass 1 content. Error: {e}", pdf_filename)
        final_latex_body = raw_latex_body

    # Assemble into standard file structure
    tex_path = os.path.join(workspace, "manuscript.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(LATEX_TEMPLATE.format(final_latex_body))

    log("Saving output files to destination without compiling.", pdf_filename)
    try:
        final_dest_dir = os.path.join(OUTPUT_DIR, pdf_base)
        if os.path.exists(final_dest_dir):
            shutil.rmtree(final_dest_dir)
        
        shutil.copytree(workspace, final_dest_dir)
        log(f"SUCCESS. Content directory saved at {final_dest_dir}", pdf_filename)
    except Exception as e:
        log(f"SYSTEM COPY ERROR: {e}", pdf_filename)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(WORK_DIR, exist_ok=True)
    
    #files = ['amt-c-11-to20-5.pdf']
    #detect all files 
    # files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.pdf') and not f.startswith("processed_")]
    files = ['amt-b-16-30-17.pdf','amt-b-31-57-3.pdf']
    print(f"Processing {len(files)} files with Dual-Pass Reflection (Hybrid Flash-Lite / Pro)...")
    
    pool = Pool(processes=MAX_CONCURRENT_FILES, initializer=init_worker, initargs=(API_KEY,))
    try:
        pool.map(process_single_pdf, files)
    finally:
        pool.close()
        pool.join()
        
    print("All file processing steps have successfully completed.")

if __name__ == "__main__":
    main()
