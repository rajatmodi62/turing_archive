import os
import sys
from google import genai
from google.genai import types

def run_gemini_35_flash_query():
    # 1. Retrieve the key securely from the local environment memory
    api_key = 'AIzaSyC52G_WrGgisY8-rd9Ky6z8-j8G7XRIk8w'#os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("[!] Execution Error: GEMINI_API_KEY environment variable is not set.")
        print("Please set it in your terminal before running:")
        print("  Linux/macOS: export GEMINI_API_KEY='your_key'")
        print("  Windows:     set GEMINI_API_KEY='your_key'")
        sys.exit(1)

    print("Initializing client configuration...")
    client = genai.Client(api_key=api_key)
    
    # 2. Define our prompt and target the new Gemini 3.5 architecture
    model_id = "gemini-3.5-flash"
    prompt = "Explain the core concept of a part-whole hierarchy in representation learning using exactly two clear sentences."
    
    print(f"Routing request to model tier: [{model_id}]...")
    
    try:
        # 3. Call the generation engine using standard parameters
        # Note: For Gemini 3.5 architectures, Google strongly recommends 
        # dropping old temperature/top_p overrides to let the model optimize natively.
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                # Gemini 3.5 natively supports built-in thinking levels: 
                # Options are: 'MINIMAL', 'LOW', 'MEDIUM', 'HIGH'
                thinking_config=types.ThinkingConfig(thinking_level="MEDIUM")
            )
        )
        
        # 4. Print output payload
        print("\n================== MODEL RESPONSE ==================")
        print(response.text)
        print("====================================================")
        
    except Exception as e:
        print(f"\n[!] Network or API pipeline error occurred: {e}")

if __name__ == "__main__":
    run_gemini_35_flash_query()