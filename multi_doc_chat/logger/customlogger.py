import logging
import os
from datetime import datetime
import structlog

class CustomLogger:
    def __init__(self, log_dir="logs"):
        # Ensure logs directory exists (Folder banayega)
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Timestamped log file (Waqt ke hisaab se file ka naam banayega)
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
        self.log_file_path = os.path.join(self.logs_dir, log_file)

    def get_logger(self, name=__file__):
        logger_name = os.path.basename(name)

        # Configure logging for console + file (File mein likhne ki setting)
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(message)s")) # Raw JSON lines

        # Screen (terminal) par dikhane ki setting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))

        # Dono handlers ko active karna
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s", # Structlog will handle JSON rendering
            handlers=[console_handler, file_handler]
        )

        # Configure structlog for JSON structured logging (JSON factory)
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
                structlog.processors.add_log_level,
                structlog.processors.EventRenamer(to="event"),
                structlog.processors.JSONRenderer()
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Tayyar shuda logger wapis karna
        return structlog.get_logger(logger_name)


# --- TEST KARNE KE LIYE (Aap isay neechay test kar sakte hain) ---
if __name__ == "__main__":
    # 1. Setup karna
    logger_setup = CustomLogger()
    
    # 2. Logger hasil karna
    my_logger = logger_setup.get_logger()
    
    # 3. Logs likhna
    my_logger.info("System successfully start ho gaya hai.")
    my_logger.warning("Storage thori kam hai.", free_space="2GB")
    my_logger.error("Database se connection toot gaya!")