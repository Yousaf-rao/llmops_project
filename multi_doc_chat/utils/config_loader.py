import os
import yaml
from pathlib import Path
from multi_doc_chat.logger.customlogger import CustomLogger
from multi_doc_chat.exception.custom_exception import DocumentPortalException

# Logger setup
logger_setup = CustomLogger()
logger = logger_setup.get_logger(__file__)

def _project_root() -> Path:
    # Ye function dhoondta hai ke package ka main folder (multi_doc_chat) kahan hai
    return Path(__file__).resolve().parents[1] # parents[1] means multi_doc_chat/ folder


def load_config(config_path: str | None = None) -> dict:
    try:
        # Priority 1: Agar kisi ne rasta (path) khud dya hai
        # Priority 2: Agar environment variable set hai
        # Priority 3: Default path (project_root/config/config.yaml)
        env_path = os.getenv("CONFIG_PATH")
        if config_path is None:
            config_path = env_path or str(_project_root() / "config" / "config.yaml")

        path = Path(config_path)
        
        # Agar path relative hai tou usay absolute banana
        if not path.is_absolute():
            path = _project_root() / path

        logger.info(f"Config load ho rahi hai is raste se: {path}")

        if not path.exists():
            raise FileNotFoundError(f"Config file nahi mili: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            logger.info("Configuration successfully load ho gai.")
            return data or {}

    except Exception as e:
        # Humne apna custom exception use kiya taake line number mil sakay
        raise DocumentPortalException(f"Config load karne mein error aya: {str(e)}", error_details=e)

"""
=============================================================================
🎯 CODE KA DETAILED OBJECTIVE (MAQSAD)
=============================================================================
Is config_loader.py file ka main maqsad (objective) hamare project ki tamaam 
settings (jo config.yaml mein hoti hain) ko safely aur dynamically parse/load 
karna hai. Ye file application ka 'Settings Manager' hai.

⚠️ Is Config Loader ki zaroorat kyun pesh aayi?
Bade projects (jaise LLMOps) mein hum hardcoded settings (maslan chunk sizes, 
API paths, model names) seedha python files (.py) mein nahi likhte. Unhe ek 
alag configuration file (yaml ya json) mein rakha jata hai. Agar file path ko 
theek se handle na kiya jaye to application start hone se pehle hi crash ho
jati hai ("FileNotFoundError").

✅ Is Config Loader Ke Fawayed (Objectives Achieved):
1. Smart Path Detection: Yeh `_project_root()` function ke zariye khud-ba-khud 
   root folder dhoond leta hai, taake hum script ko project ki kisi bhi 
   directory se run karein to file path ka masla (Absolute/Relative) na aaye.
2. Flexible Priority System: Yeh 3 options dekhta hai:
   - Priority 1: Agar developer ne specifically path argument pass kiya hai.
   - Priority 2: Agar OS environment variable (CONFIG_PATH) set hai.
   - Priority 3: Default `config/config.yaml` uthata hai.
3. Safe Error Handling and Logging: Agar config file read na ho sake, ya 
   yaml mein formatting ka masla ho, to yeh wahi `DocumentPortalException` ko
   invoke karta hai jo humne tab banaya tha, jis se error line numbers aur proper 
   history ke sath hamare CustomLogger mei save ho jata hai.
=============================================================================
"""
