import os
import subprocess
import logging
from multiprocessing import Pool

# ==========================================
# Logging & Configuration Setup
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

PROCESSED_DIR = "./processed_pdfs"
TOTAL_CORES = os.cpu_count() or 1
MAX_CONCURRENT_COMPILATIONS = max(1, TOTAL_CORES - 1)
ERROR_LOG_FILE = "failed_compilations.txt"  # <-- Name of your persistent error list

def compile_single_tex(dir_name):
    """Worker function executed by independent CPU cores."""
    target_dir = os.path.join(PROCESSED_DIR, dir_name)
    tex_file = "manuscript.tex"
    tex_path = os.path.join(target_dir, tex_file)
    
    if not os.path.exists(tex_path):
        return None

    logging.info(f"[{dir_name}] Launching XeLaTeX compilation...")
    
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-file-line-error",
        tex_file
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logging.info(f"[{dir_name}] SUCCESS. PDF compiled successfully.")
        return {
            "dir": dir_name, 
            "status": "SUCCESS", 
            "full_output": result.stdout,
            "errors": []
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"[{dir_name}] FAILED. Engine encountered compilation syntax bugs.")
        
        error_summary = []
        for line in e.stdout.splitlines():
            if "error" in line.lower() or "fatal" in line.lower() or line.startswith("!"):
                error_summary.append(line.strip())
                
        if not error_summary:
            error_summary = [e.stderr.strip() if e.stderr else "Non-zero exit status thrown by engine."]
            
        return {
            "dir": dir_name,
            "status": "FAILED",
            "full_output": e.stdout,
            "errors": error_summary
        }
    except Exception as e:
        logging.error(f"[{dir_name}] SYSTEM CALL ERROR: {e}")
        return {
            "dir": dir_name, 
            "status": "SYSTEM_ERROR", 
            "full_output": "", 
            "errors": [str(e)]
        }

def main():
    if not os.path.exists(PROCESSED_DIR):
        print(f"Error: The target directory '{PROCESSED_DIR}' does not exist.")
        return

    all_contents = os.listdir(PROCESSED_DIR)
    sub_dirs = [d for d in all_contents if os.path.isdir(os.path.join(PROCESSED_DIR, d))]
    
    if not sub_dirs:
        print(f"No sub-directories detected inside '{PROCESSED_DIR}'.")
        return

    print(f"System detected {TOTAL_CORES} cores.")
    print(f"Spawning {MAX_CONCURRENT_COMPILATIONS} parallel XeLaTeX compilation engines across folders...\n")

    pool = Pool(processes=MAX_CONCURRENT_COMPILATIONS)
    try:
        results = [r for r in pool.map(compile_single_tex, sub_dirs) if r is not None]
    finally:
        pool.close()
        pool.join()

    # ==========================================
    # Final Reporting & Full Log Aggregation
    # ==========================================
    print("\n" + "="*60)
    print("         DETAILED XELATEX OUTPUTS & ENGINE LOGS         ")
    print("="*60)

    for res in results:
        print(f"\n📂 FOLDER DATASTREAM: {res['dir']}")
        print(f"Status: {'✅ SUCCESS' if res['status'] == 'SUCCESS' else '❌ FAILED'}")
        print("-" * 40)
        
        if res['status'] == 'SUCCESS':
            summary_lines = [l for l in res['full_output'].splitlines() if "Output written on" in l or "pages" in l]
            if summary_lines:
                for sl in summary_lines:
                    print(f"   {sl}")
            else:
                print("   Document compiled successfully. (Log output compressed)")
        else:
            print("🛑 Engine Syntax Errors Triggered:")
            for err in res['errors'][:8]:
                print(f"   -> {err}")
                
            print("\n📋 Last 15 Lines of Raw Engine Context Log:")
            raw_lines = res['full_output'].splitlines()
            for line in raw_lines[-15:]:
                print(f"   | {line}")
        print("-" * 60)

    # ==========================================
    # PERSISTENT STORAGE WRITEBACK (New Addition)
    # ==========================================
    failures = [r for r in results if r["status"] != "SUCCESS"]
    
    if failures:
        try:
            with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
                f.write("=== FAILED COMPILATIONS MANIFEST ===\n")
                f.write(f"The following folders triggered XeLaTeX layout exceptions:\n\n")
                for fail in failures:
                    f.write(f"📁 {fail['dir']}\n")
                    f.write(f"   Primary Error: {fail['errors'][0] if fail['errors'] else 'Unknown layout bug'}\n\n")
            print(f"\n💾 Saved persistent manifest of broken runs to: {ERROR_LOG_FILE}")
        except Exception as file_err:
            print(f"\n⚠️ System failed to write tracking manifest to disk: {file_err}")
    else:
        # If a subsequent run passes completely clean, purge the old error file
        if os.path.exists(ERROR_LOG_FILE):
            os.remove(ERROR_LOG_FILE)

    # Global Stats Banner
    print("\n" + "="*60)
    print("                  COMPILATION METRICS                       ")
    print("="*60)
    print(f"Total Folders Processed: {len(results)}")
    print(f"Flawless Conversions:    {len(results) - len(failures)}")
    print(f"Syntax/Layout Failures:  {len(failures)}")
    print("="*60)

if __name__ == "__main__":
    main()