import fitz  # PyMuPDF
import base64
import io
import os
import re
import sys
from openai import OpenAI
from PIL import Image

# Force UTF-8 stdout to avoid UnicodeEncodeError on em dashes etc.
sys.stdout.reconfigure(encoding='utf-8')

# 1. Setup
client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
PDF_PATH = '/home/rmodi/turing/turing_archive/amt-d-9.pdf'
FIGURES_DIR = "figures"
os.makedirs(FIGURES_DIR, exist_ok=True)

UNICODE_SUPERSCRIPTS = {
    '\u2070': '0', '\u00b9': '1', '\u00b2': '2', '\u00b3': '3',
    '\u2074': '4', '\u2075': '5', '\u2076': '6', '\u2077': '7',
    '\u2078': '8', '\u2079': '9',
}
UNICODE_SUBSCRIPTS = {
    '\u2080': '0', '\u2081': '1', '\u2082': '2', '\u2083': '3',
    '\u2084': '4', '\u2085': '5', '\u2086': '6', '\u2087': '7',
    '\u2088': '8', '\u2089': '9',
}

# Common Unicode characters that have safe LaTeX equivalents
UNICODE_REPLACEMENTS = {
    '\u2014': '---',       # em dash
    '\u2013': '--',        # en dash
    '\u2018': '`',         # left single quote
    '\u2019': "'",         # right single quote
    '\u201c': '``',        # left double quote
    '\u201d': "''",        # right double quote
    '\u2026': '\\ldots{}', # ellipsis
    '\u00a0': '~',         # non-breaking space
    '\u00b7': '\\cdot{}',  # middle dot
    '\u2212': '-',         # minus sign
    '\u00d7': '\\times{}', # multiplication sign
    '\u00f7': '\\div{}',   # division sign
    '\u2264': '\\leq{}',   # less than or equal
    '\u2265': '\\geq{}',   # greater than or equal
    '\u2260': '\\neq{}',   # not equal
    '\u221e': '\\infty{}', # infinity
    '\u03b1': '\\alpha{}', # greek alpha
    '\u03b2': '\\beta{}',  # greek beta
    '\u03b3': '\\gamma{}', # greek gamma
    '\u03b4': '\\delta{}', # greek delta
    '\u03b5': '\\epsilon{}', # greek epsilon
    '\u03bb': '\\lambda{}',# greek lambda
    '\u03bc': '\\mu{}',    # greek mu
    '\u03c0': '\\pi{}',    # greek pi
    '\u03c3': '\\sigma{}', # greek sigma
    '\u03c6': '\\phi{}',   # greek phi
    '\u03c9': '\\omega{}', # greek omega
}


def sanitize_latex(text):
    # 1. Fix [h] float specifier
    text = text.replace(r'\begin{figure}[h]', r'\begin{figure}[htbp]')

    # 2. Convert Unicode superscripts to LaTeX math
    for char, digit in UNICODE_SUPERSCRIPTS.items():
        text = text.replace(char, f'$^{{{digit}}}$')

    # 3. Convert Unicode subscripts to LaTeX math
    for char, digit in UNICODE_SUBSCRIPTS.items():
        text = text.replace(char, f'$_{{{digit}}}$')

    # 4. Replace known Unicode characters with LaTeX equivalents
    for char, replacement in UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)

    # 5. Replace any remaining non-ASCII characters with '?'
    result = []
    for char in text:
        if ord(char) > 127:
            result.append('?')
        else:
            result.append(char)
    return ''.join(result)


def process_manuscript(pdf_path):
    doc = fitz.open(pdf_path)
    all_pages_latex = []

    for page_num in range(len(doc)):
        print(f"\nProcessing page {page_num + 1}/{len(doc)}...")
        page = doc.load_page(page_num)

        # 2. Extract unique raster figures, skip tiny decorative images
        fig_paths = []
        raw_images = list(dict.fromkeys(page.get_images(full=True)))

        for i, img_info in enumerate(raw_images):
            xref = img_info[0]
            pix = fitz.Pixmap(doc, xref)

            # Skip tiny images (icons, bullets, decorations)
            if pix.width < 100 or pix.height < 100:
                print(f"  Skipping small image (xref={xref}, {pix.width}x{pix.height})")
                continue

            fig_name = f"page_{page_num}_fig_{i}.png"
            fig_path = os.path.join(FIGURES_DIR, fig_name)
            pix.save(fig_path)
            fig_paths.append(fig_name)
            print(f"  Extracted figure: {fig_path}")

        # 3. Fallback: if no raster images found, save full page render
        #    so vector drawings / charts are still captionable
        if not fig_paths:
            fallback_pix = page.get_pixmap(dpi=150)
            fig_name = f"page_{page_num}_fullpage.png"
            fig_path = os.path.join(FIGURES_DIR, fig_name)
            fallback_pix.save(fig_path)
            fig_paths.append(fig_name)
            print(f"  No raster images found - saved full-page fallback: {fig_path}")

        # 4. Render page as image for the VLM
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        # 5. Prompt: full text + figures with real captions, body-only LaTeX
        prompt = (
            "You are an expert LaTeX transcriber. Transcribe the manuscript page shown "
            "in the image into LaTeX. Output ONLY the body content — do NOT include "
            r"\documentclass, \usepackage, \begin{document}, or \end{document}. "
            "Transcribe ALL text on the page completely and verbatim — every heading, "
            "paragraph, footnote, and caption visible in the image must appear in the output. "
            "Do not summarise, skip, or truncate any text, even if a figure is present. "
            "Use proper LaTeX math mode for ALL mathematical expressions, symbols, subscripts, "
            "and superscripts — never use raw Unicode characters for math. "
            "Insert figures at the correct locations using the following filenames exactly: "
            f"{fig_paths}. "
            r"Use this exact format for each figure: "
            r"\begin{figure}[htbp] \centering "
            r"\includegraphics[width=0.8\textwidth]{figures/FILENAME} "
            r"\caption{Descriptive caption inferred from the figure content and surrounding text.} "
            r"\label{fig:FILENAME} "
            r"\end{figure} "
            "IMPORTANT RULES - follow every one: "
            "1. Only use filenames from the list above - never invent new filenames. "
            "2. If the page contains a diagram, chart, table, illustration, or any visual "
            "element, you MUST include it as a figure with a meaningful caption. Never skip it. "
            "3. If the page is plain text with no visual content, do not insert any figure environment. "
            "4. Every caption MUST be descriptive and specific to what is shown - "
            "never write '...' or generic placeholder text like 'Caption here'. "
            "5. The figure environment must be placed at the position in the text where "
            "the figure appears on the page - not dumped at the end. "
            "6. Do not wrap the output in markdown code fences or backticks. "
            "7. Always use LaTeX math mode ($...$ or $$...$$) for equations, never raw Unicode math symbols."
        )

        response = client.chat.completions.create(
            model="Qwen/Qwen3-VL-32B-Instruct",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}]
        )

        content = response.choices[0].message.content

        # 6. Strip any document-level wrappers the model emits anyway
        skip_patterns = (
            r"\documentclass",
            r"\usepackage",
            r"\begin{document}",
            r"\end{document}",
            "```",
        )
        filtered_lines = [
            line for line in content.splitlines()
            if not any(line.strip().startswith(p) for p in skip_patterns)
        ]
        content = "\n".join(filtered_lines)

        # 7. Sanitize Unicode and fix float specifiers
        content = sanitize_latex(content)

        all_pages_latex.append(content)
        print(f"  Done - page {page_num + 1} transcribed.")

    # 8. Write final .tex with boilerplate exactly once
    output_path = "master_document.tex"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{float}
\usepackage{textcomp}

\begin{document}

""")
        f.write("\n\n% -------- Page break --------\n\n".join(all_pages_latex))
        f.write("\n\n\\end{document}\n")

    print(f"\nDone! {output_path} is ready.")


if __name__ == "__main__":
    process_manuscript(PDF_PATH)