import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# =====================================================================
# Configuration & Direct URL Extraction
# =====================================================================
print("=====================================================================")
print("         UNIVERSAL ALAN TURING ARCHIVE PIPELINE DOWNLOADER          ")
print("=====================================================================")

sample_url = 'https://www.alanturing.net/turing_archive/archive/t/t01/TR01-005.gif'

# This pattern captures the base URL path, the exact local folder name, 
# and the exact filename prefix used in the link, completely ignoring casing or letter changes.
pattern = r"(https://.*/archive/[^/]+/([^/]+)/+)([^/-]+)-\d+\.(\w+)"
match = re.search(pattern, sample_url)

if not match:
    print("\n[!] Error: Could not parse the URL structure.")
    import sys
    sys.exit(1)

base_folder_url = match.group(1)   # e.g., "https://www.alanturing.net/turing_archive/archive/t/t01/"
dir_name = match.group(2)          # Local folder layout target (e.g., "t01")
extracted_prefix = match.group(3)  # Exact prefix extracted from sample (e.g., "TR01")
file_ext = match.group(4)          # Extension (e.g., "gif")

# --- MUTATION MATRIX GENERATION ---
# Instead of guessing based on the folder name, we generate mutations 
# directly on the prefix that you verified works in your sample link!
prefixes_to_try = set([extracted_prefix])

# Handle letter casing variants (TR01, tr01)
prefixes_to_try.add(extracted_prefix.upper())
prefixes_to_try.add(extracted_prefix.lower())

# Handle potential 0 vs O character swaps on the prefix
for p in list(prefixes_to_try):
    prefixes_to_try.add(p.replace("0", "O"))
    prefixes_to_try.add(p.replace("O", "0"))
    prefixes_to_try.add(p.replace("0", "o"))
    prefixes_to_try.add(p.replace("o", "0"))

# If the folder name happens to look like a missing leading zero scenario (like B13 vs B013),
# we add the folder name itself into the sweep pool as a safety mechanism.
prefixes_to_try.add(dir_name)
prefixes_to_try.add(dir_name.upper())

prefixes_to_try = sorted(list(prefixes_to_try))
# ----------------------------------

START_PAGE = 0
END_PAGE = 500
MAX_THREADS = 16 

# Establish local directory matching your input format
OUTPUT_DIR = os.path.abspath(os.path.join(".", dir_name))
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print("\n[+] Extraction Strategy Operational:")
print(f"    -> Local Destination Folder: ./{dir_name}/")
print(f"    -> Verified Target Prefix:   {extracted_prefix}")
print(f"    -> Mutation Testing Matrix:  {prefixes_to_try}")
print(f"    -> Payload Asset Target:     .{file_ext}\n")

# =====================================================================
# Core Download Routine
# =====================================================================
def download_page(page_num):
    page_str = f"{page_num:03d}"
    local_filename = f"{page_str}.{file_ext}"
    local_path = os.path.join(OUTPUT_DIR, local_filename)
    
    for prefix in prefixes_to_try:
        target_url = f"{base_folder_url}{prefix}-{page_str}.{file_ext}"
        
        try:
            head_response = requests.head(target_url, headers=HEADERS, timeout=5)
            if head_response.status_code == 200:
                get_response = requests.get(target_url, headers=HEADERS, stream=True, timeout=15)
                if get_response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        for chunk in get_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    return page_num, True, f"Saved via [{prefix}] -> ./{dir_name}/{local_filename}"
                    
        except requests.exceptions.RequestException:
            continue
            
    return page_num, False, "Missing pattern alignment"

def main():
    print("Spawning parallel workers to scan sequence indices...")
    success_count = 0
    total_scanned = 0
    
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_page = {
            executor.submit(download_page, i): i for i in range(START_PAGE, END_PAGE + 1)
        }
        
        for future in as_completed(future_to_page):
            page_num, success, message = future.result()
            total_scanned += 1
            
            if success:
                success_count += 1
                print(f"[+] [Index {page_num:03d}]: {message}")

    print("\n=====================================================================")
    print("   PROCESSING COMPLETION SUMMARY")
    print(f"   Total Targets Evaluated:          {total_scanned}")
    print(f"   Total Documents Pulled onto Disk: {success_count} files in ./{dir_name}/")
    print("=====================================================================")

if __name__ == "__main__":
    main()
# import os
# import re
# import requests
# from concurrent.futures import ThreadPoolExecutor, as_completed

# # =====================================================================
# # Configuration & Advanced Prefix Generator
# # =====================================================================
# print("=====================================================================")
# print("         ULTIMATE RESILIENT ALAN TURING ARCHIVE DOWNLOADER          ")
# print("=====================================================================")

# sample_url = 'https://www.alanturing.net/turing_archive/archive/t/t01/TR01-005.gif'#input("Paste a sample URL from the target document folder:\n-> ").strip()

# # Parse baseline server positioning
# pattern = r"(https://.*/archive/[^/]+/([^/]+)/+)([^/-]+)-\d+\.(\w+)"
# match = re.search(pattern, sample_url)

# if not match:
#     print("\n[!] Error: Could not parse the URL structure.")
#     import sys
#     sys.exit(1)

# base_folder_url = match.group(1)   # e.g., "https://www.alanturing.net/turing_archive/archive/b/B013//"
# dir_name = match.group(2)          # Folder name on server (e.g., "B013")
# file_ext = match.group(4)          # File extension (e.g., "gif")

# # --- MUTATION MATRIX GENERATION ---
# # Start with any characters extracted from the folder name
# raw_clean = dir_name.upper().strip()

# # Generate variations by isolating the letter and the numeric blocks
# # This handles stripping or adding zero padding (e.g., B013 -> B13 or B5 -> B05)
# letter_part = "".join([c for c in raw_clean if c.isalpha()])
# number_part = "".join([c for c in raw_clean if c.isdigit()])

# base_variants = [raw_clean]
# if number_part:
#     int_val = int(number_part)
#     # Generate variations with different zero-padding depths
#     base_variants.append(f"{letter_part}{int_val}")        # e.g., B13
#     base_variants.append(f"{letter_part}{int_val:02d}")    # e.g., B13
#     base_variants.append(f"{letter_part}{int_val:03d}")    # e.g., B013

# # For every single variant generated, add the 0 vs O character swap rule
# final_prefixes = set()
# for v in base_variants:
#     final_prefixes.add(v)
#     final_prefixes.add(v.replace("0", "O"))
#     final_prefixes.add(v.replace("O", "0"))

# prefixes_to_try = sorted(list(final_prefixes))
# # ----------------------------------

# START_PAGE = 0
# END_PAGE = 500
# MAX_THREADS = 16 

# # Local directory setup matching the actual server folder name
# OUTPUT_DIR = os.path.abspath(os.path.join(".", dir_name))
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
# }

# print("\n[+] Exhaustive Structural Matrix Activated:")
# print(f"    -> Local Target Folder:    ./{dir_name}/")
# print(f"    -> Mutation Testing Matrix: {prefixes_to_try}")
# print(f"    -> Target Extension Type:  .{file_ext}\n")

# # =====================================================================
# # Core Download Routine
# # =====================================================================
# def download_page(page_num):
#     page_str = f"{page_num:03d}"
#     local_filename = f"{page_str}.{file_ext}"
#     local_path = os.path.join(OUTPUT_DIR, local_filename)
    
#     # Sweep through the entire prefix matrix for this specific index
#     for prefix in prefixes_to_try:
#         target_url = f"{base_folder_url}{prefix}-{page_str}.{file_ext}"
        
#         try:
#             head_response = requests.head(target_url, headers=HEADERS, timeout=5)
#             if head_response.status_code == 200:
#                 # Valid asset variant found!
#                 get_response = requests.get(target_url, headers=HEADERS, stream=True, timeout=15)
#                 if get_response.status_code == 200:
#                     with open(local_path, 'wb') as f:
#                         for chunk in get_response.iter_content(chunk_size=8192):
#                             if chunk:
#                                 f.write(chunk)
#                     return page_num, True, f"Saved via [{prefix}] -> ./{dir_name}/{local_filename}"
                    
#         except requests.exceptions.RequestException:
#             continue
            
#     return page_num, False, "Not found under any naming mutation"

# def main():
#     print("Scanning indices concurrently with advanced error-recovery loops...")
#     success_count = 0
#     total_scanned = 0
    
#     with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
#         future_to_page = {
#             executor.submit(download_page, i): i for i in range(START_PAGE, END_PAGE + 1)
#         }
        
#         for future in as_completed(future_to_page):
#             page_num, success, message = future.result()
#             total_scanned += 1
            
#             if success:
#                 success_count += 1
#                 print(f"[+] [Index {page_num:03d}]: {message}")

#     print("\n=====================================================================")
#     print("   PROCESSING COMPLETION SUMMARY")
#     print(f"   Total Target Signatures Checked: {total_scanned}")
#     print(f"   Total Downloaded Assets Stored:  {success_count} files in ./{dir_name}/")
#     print("=====================================================================")

# if __name__ == "__main__":
#     main()