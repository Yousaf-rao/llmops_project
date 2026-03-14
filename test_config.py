from multi_doc_chat.utils.configuration_loader import load_config
import json

# Hum sirf load_config() call karenge bina kisi path ke
# Ye khudi _project_root() use kar ke config.yaml dhoond lega
try:
    print("--- Testing Configuration Loader ---")
    config = load_config()
    
    # Result ko thora saaf dikhane ke liye JSON format use kar raha hoon
    print("\n✅ Success! Configuration dhoond li aur load kar li.")
    print("Aapki settings ye hain:")
    print(json.dumps(config, indent=4))
    
    # Aik specific value check karte hain
    print(f"\nModel Name being used: {config['llm']['google']['model_name']}")

except Exception as e:
    print(f"\n❌ Masla aya hai: {e}")
