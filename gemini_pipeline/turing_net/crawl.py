import os
import re
import requests
import sys
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# =====================================================================
# Configuration
# =====================================================================
SEED_URL = "https://www.alanturing.net/turing_archive/archive/index/archiveindex.html"
MAX_DEPTH = 4                 
MAX_CRAWL_WORKERS = 10        
MAX_DOWNLOAD_WORKERS = 8     # Safe concurrency to prevent timeout drops on long sweeps
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Tracking Registries
visited_pages = set()
discovered_sequences = {}  # Format: {dir_name: (base_folder_url, file_prefix, file_ext)}

# =====================================================================
# Phase 1: Dynamic Discovery Crawler
# =====================================================================
def extract_links_and_register_folders(url):
    links = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code != 200:
            return links
            
        if ".gif" in response.text.lower():
            gif_matches = re.findall(r'([^/\"\'\s>]+)-\d{3,4}\.gif', response.text, re.IGNORECASE)
            if gif_matches:
                url_pattern = r"(https://.*/archive/[^/]+/([^/]+)/+)"
                match = re.search(url_pattern, url)
                if match:
                    base_folder_url = match.group(1)
                    dir_name = match.group(2)
                    file_prefix = gif_matches[0]
                    
                    ext_match = re.search(r'\.gif', response.text, re.IGNORECASE)
                    file_ext = ext_match.group(0).lower().replace(".", "") if ext_match else "gif"

                    if dir_name not in discovered_sequences:
                        discovered_sequences[dir_name] = (base_folder_url, file_prefix, file_ext)
                        sys.stdout.write(f"\r[+] Indexed Track #{len(discovered_sequences)}: ./{dir_name}/ (via {file_prefix})")
                        sys.stdout.flush()

        soup = BeautifulSoup(response.text, 'html.parser')
        for anchor in soup.find_all('a', href=True):
            href = anchor['href'].strip()
            if not href or href.startswith("#") or "javascript:" in href:
                continue
            full_url = urljoin(url, href)
            if "alanturing.net/turing_archive/" in full_url.lower():
                links.append(full_url)
    except Exception:
        pass
    return list(set(links))

def run_discovery_crawl(current_urls, depth=0):
    if depth > MAX_DEPTH or not current_urls:
        return

    next_layer_urls = set()
    with ThreadPoolExecutor(max_workers=MAX_CRAWL_WORKERS) as crawl_executor:
        future_to_url = {crawl_executor.submit(extract_links_and_register_folders, url): url for url in current_urls if url not in visited_pages}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            visited_pages.add(url)
            for link in future.result():
                if link not in visited_pages:
                    next_layer_urls.add(link)
                    
    run_discovery_crawl(list(next_layer_urls), depth + 1)

# =====================================================================
# Phase 2: Horizon-Scanning Sequential Downloader
# =====================================================================
def download_sequence_until_end(dir_name, config):
    base_folder_url, file_prefix, file_ext = config
    
    # Generate resilient mutation array for typos
    raw_clean = dir_name.upper().strip()
    letter_part = "".join([c for c in raw_clean if c.isalpha()])
    number_part = "".join([c for c in raw_clean if c.isdigit()])

    base_variants = [raw_clean, file_prefix.upper(), file_prefix.lower()]
    if number_part:
        int_val = int(number_part)
        base_variants.append(f"{letter_part}{int_val}")
        base_variants.append(f"{letter_part}{int_val:02d}")
        base_variants.append(f"{letter_part}{int_val:03d}")

    prefixes_to_try = set()
    for v in base_variants:
        prefixes_to_try.add(v)
        prefixes_to_try.add(v.replace("0", "O"))
        prefixes_to_try.add(v.replace("O", "0"))
        prefixes_to_try.add(v.replace("0", "o"))
        prefixes_to_try.add(v.replace("o", "0"))
    prefixes_to_try = sorted(list(prefixes_to_try))

    output_dir = os.path.abspath(os.path.join(".", dir_name))
    os.makedirs(output_dir, exist_ok=True)

    def test_and_download_page(page_num):
        page_str = f"{page_num:03d}"
        local_path = os.path.join(output_dir, f"{page_str}.{file_ext}")

        for prefix in prefixes_to_try:
            target_url = f"{base_folder_url}{prefix}-{page_str}.{file_ext}"
            for attempt in range(3):
                try:
                    head_resp = requests.head(target_url, headers=HEADERS, timeout=4)
                    if head_resp.status_code == 200:
                        get_resp = requests.get(target_url, headers=HEADERS, stream=True, timeout=10)
                        if get_resp.status_code == 200:
                            with open(local_path, 'wb') as f:
                                for chunk in get_resp.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            return True, page_num
                    elif head_resp.status_code == 404:
                        break
                except Exception:
                    time.sleep(0.5 * (attempt + 1))
                    continue
        return False, page_num

    print(f"\nProcessing Folder: ./{dir_name}/")
    
    current_chunk_start = 0
    chunk_size = 15          # Check pages in concurrent windows of 15
    consecutive_missing = 0
    saved_count = 0
    max_horizon_failures = 5 # Stop completely if 5 pages in a row don't exist
    
    keep_scanning = True
    
    while keep_scanning:
        page_range = range(current_chunk_start, current_chunk_start + chunk_size)
        chunk_results = {}
        
        with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as download_executor:
            futures = {download_executor.submit(test_and_download_page, idx): idx for idx in page_range}
            for future in as_completed(futures):
                success, p_num = future.result()
                chunk_results[p_num] = success
        
        # Evaluate results sequentially to track the consecutive missing threshold accurately
        for idx in sorted(page_range):
            if chunk_results[idx]:
                saved_count += 1
                consecutive_missing = 0  # Reset counter on a successful download hit
            else:
                consecutive_missing += 1
                
            if consecutive_missing >= max_horizon_failures:
                keep_scanning = False
                break
                
        sys.stdout.write(f"\r    -> Scanned up to page {max(page_range):03d} | Total Saved: {saved_count} files")
        sys.stdout.flush()
        
        current_chunk_start += chunk_size
        
    print() # Clear line formatting

# =====================================================================
# Main Execution Entrypoint
# =====================================================================
def main():
    print("=====================================================================")
    print("   PHASE 1: LAUNCHING RECURSIVE DISCOVERY SWEEP                      ")
    print("=====================================================================")
    run_discovery_crawl([SEED_URL], depth=0)
    
    total_discovered = len(discovered_sequences)
    print("\n\n=====================================================================")
    print("   PHASE 2: STARTING HORIZON-SCANNING DOWNLOAD QUEUE                 ")
    print("=====================================================================")
    print(f"Total Folders Discovered: {total_discovered}")

    for current_count, (dir_name, config) in enumerate(discovered_sequences.items(), 1):
        print(f"\n[{current_count}/{total_discovered}] Pipeline Engaged")
        download_sequence_until_end(dir_name, config)

    print("\n=====================================================================")
    print("   PIPELINE DISCOVERY RUN COMPLETE")
    print("=====================================================================")

if __name__ == "__main__":
    main()