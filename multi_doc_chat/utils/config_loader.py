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
