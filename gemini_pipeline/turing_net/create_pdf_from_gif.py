import os
import sys
from PIL import Image

# FORCED ENCODER REGISTRATION
# Explicitly imports core plugins to register the 'JPEG' codecs inside the 
# global PIL Image system before the file compilation block executes.
try:
    from PIL import JpegImagePlugin, PdfImagePlugin
except ImportError:
    print("[!] Warning: Could not explicitly import Pillow sub-plugins.")
    print("    Ensure your Pillow installation is up to date: pip install --upgrade pillow")

def compile_images_to_pdf_with_progress():
    # Configuration boundaries
    TARGET_EXTENSION = ".gif"
    OUTPUT_DIR_NAME = "processed_dir"
    
    current_dir = os.getcwd()
    processed_dir = os.path.join(current_dir, OUTPUT_DIR_NAME)
    os.makedirs(processed_dir, exist_ok=True)
    
    print("=====================================================================")
    print("         LOCAL ARCHIVAL PAYLOAD COMPILATION PIPELINE                 ")
    print("=====================================================================")
    print(f"Scanning target directory space: {current_dir}\n")
    
    compiled_folders_count = 0
    
    # Step 1: Iterate through items in the execution root alphabetically
    for folder_name in sorted(os.listdir(current_dir)):
        folder_path = os.path.join(current_dir, folder_name)
        
        # Isolate true target directories, skipping files and output spaces
        if not os.path.isdir(folder_path) or folder_name == OUTPUT_DIR_NAME or folder_name.startswith('.'):
            continue
            
        # Step 2: Gather and filter image files
        image_files = [
            f for f in os.listdir(folder_path) 
            if f.lower().endswith(TARGET_EXTENSION)
        ]
        
        if not image_files:
            continue
            
        # Strict alphanumeric sorting to keep '000.gif', '001.gif', etc. in order
        image_files.sort()
        total_pages = len(image_files)
        
        print(f"\nProcessing Folder: ./{folder_name}/ ({total_pages} pages detected)")
        
        # Step 3: Open, convert to RGB, and track progress page by page
        pil_images = []
        for current_idx, img_file in enumerate(image_files, 1):
            img_path = os.path.join(folder_path, img_file)
            try:
                img = Image.open(img_path)
                
                # GIFs use an indexed/palette mode. PDF layers require a raw RGB matrix layout.
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                pil_images.append(img)
                
                # Active inline terminal update for page extraction visibility
                sys.stdout.write(f"\r    -> Converting pages: [{current_idx}/{total_pages}] | Processing: {img_file}")
                sys.stdout.flush()
                
            except Exception as e:
                print(f"\n    [!] Error opening asset {img_file}: {e}")
        
        # Clear the terminal progress line cleanly before compiling
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        
        # Step 4: Compress and write the image array into a single unified PDF layout
        if pil_images:
            output_pdf_path = os.path.join(processed_dir, f"{folder_name}.pdf")
            print(f"    -> Compressing and compiling matrix into final layout...")
            
            try:
                # Use Pillow's native multi-page sequence compiler
                first_image = pil_images[0]
                first_image.save(
                    output_pdf_path,
                    save_all=True,
                    append_images=pil_images[1:]
                )
                
                compiled_folders_count += 1
                print(f"    [+] Saved Unified Manuscript -> ./{OUTPUT_DIR_NAME}/{folder_name}.pdf")
                
            except Exception as e:
                print(f"    [!] Critical failure writing PDF file: {e}")
                
            finally:
                # MANDATORY MEMORY CLEANUP: Flush active file descriptors out of RAM
                for img in pil_images:
                    img.close()

    print("\n=====================================================================")
    print("   COMPILATION SEQUENCE COMPLETED SUCCESSFULLY")
    print(f"   Total Transformed Manuscripts: {compiled_folders_count} volumes compiled.")
    print(f"   Output Root:                   ./{OUTPUT_DIR_NAME}/")
    print("=====================================================================")

if __name__ == "__main__":
    compile_images_to_pdf_with_progress()