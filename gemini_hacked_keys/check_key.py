import os
import sys
from google import genai
from google.genai.errors import APIError

def validate_and_inspect_key_visible():
    print("==================================================")
    print("          GEMINI API KEY VISIBLE VERIFIER        ")
    print("==================================================")
    
    # Standard visible text input
    api_key = input("Paste your Gemini API Key here: ").strip()
    
    if not api_key:
        print("\n[!] Error: No key entered. Exiting.")
        return

    print("\nConnecting to Google AI Studio infrastructure...")
    
    try:
        # Initialize the client explicitly with the entered token
        client = genai.Client(api_key=api_key)
        
        # Pull the live model listings authorized for this key
        available_models = []
        model_list = client.models.list()
        
        for model in model_list:
            model_id = model.name.replace("models/", "")
            available_models.append(model_id)
            
        print("\n[+] SUCCESS: API Key is valid and active.")
        print("--------------------------------------------------")
        
        # Evaluate Tier Metrics based on key capabilities
        print("Estimated Access Tier:")
        if any("gemini-2.5-pro" in m for m in available_models):
            print(" -> Tier status: Standard / Pay-As-You-Go Enabled (Pro Model Pipeline Available)")
        else:
            print(" -> Tier status: Free Tier Baseline (Flash / Flash-Lite Processing Constraints)")
            
        # Enumerate accessible models
        print(f"\n[+] Authorized Models Found ({len(available_models)} total):")
        
        core_models = [m for m in available_models if "gemini" in m or "text-embedding" in m]
        
        print("\n  Core Models Available:")
        for model in sorted(core_models):
            print(f"   - {model}")
                
    except APIError as e:
        print("\n[-] VALIDATION FAILED: The infrastructure rejected this credential.")
        print(f"    Error Details: {e.message if hasattr(e, 'message') else e}")
    except Exception as e:
        print(f"\n[!] System execution anomaly: {e}")

if __name__ == "__main__":
    validate_and_inspect_key_visible()