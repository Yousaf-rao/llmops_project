import logging        # Python ka built-in logging system import kiya — yeh file/console mein likhne ka kaam karta hai
import os              # Operating system functions — folders banana, path banana wagera
from datetime import datetime  # Waqt (date & time) hasil karne ke liye
import structlog       # Structlog library — JSON format mein logs likhne ke liye (pip se install hoti hai)

class CustomLogger:
    # ─────────────────────────────────────────────
    # SAHIH 1: OBJECT BANTE WAQT YEH CHALTA HAI
    # logger_setup = CustomLogger() likhne par yeh __init__ chalta hai
    # ─────────────────────────────────────────────
    def __init__(self, log_dir="logs"):

        # os.getcwd() = current folder ka path deta hai, jaise: C:\Users\...\LLMOPS_SERIES
        # os.path.join() = uss path mein "logs" folder jod deta hai
        # RESULT → self.logs_dir = "C:\Users\...\LLMOPS_SERIES\logs"
        self.logs_dir = os.path.join(os.getcwd(), log_dir)

        # Agar "logs" naam ka folder nahi hai toh bana do, hai toh kuch mat karo (exist_ok=True)
        # RESULT → logs/ folder ban jata hai (ya pehle se tha toh kuch nahi hua)
        os.makedirs(self.logs_dir, exist_ok=True)

        # datetime.now() = abhi ka waqt, strftime() = usse is format mein likho: 03_27_2026_23_25_00
        # RESULT → log_file = "03_27_2026_23_25_00.log"
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"

        # logs/ folder + file ka naam jod ke poora path banaya
        # RESULT → self.log_file_path = "C:\...\logs\03_27_2026_23_25_00.log"
        self.log_file_path = os.path.join(self.logs_dir, log_file)

    # ─────────────────────────────────────────────
    # SAHIH 2: LOGGER HASIL KARNA
    # logger_setup.get_logger(__file__) likhne par yeh chalta hai
    # ─────────────────────────────────────────────
    def get_logger(self, name=__file__):

        # __file__ mein poora path hota hai, basename() sirf file ka naam leta hai
        # MISAAL: "C:\...\test_logger_power.py" → "test_logger_power.py"
        logger_name = os.path.basename(name)

        # FileHandler = woh handler jo .log FILE mein likhta hai
        # self.log_file_path par jo file bani thi — usi mein likhega
        # RESULT → file handler tayyar — abhi tak kuch likha nahi
        file_handler = logging.FileHandler(self.log_file_path)

        # Is file handler ko sirf INFO ya usse bade level ki cheezein likhni hain
        # Levels: DEBUG < INFO < WARNING < ERROR < CRITICAL
        file_handler.setLevel(logging.INFO)

        # Format set kiya: sirf raw message likhna hai (structlog khud JSON banayega)
        # RESULT → file mein: {"event": "...", "level": "info", ...} likhega
        file_handler.setFormatter(logging.Formatter("%(message)s"))

        # StreamHandler = woh handler jo TERMINAL (screen) par dikhata hai
        # RESULT → console handler tayyar
        console_handler = logging.StreamHandler()

        # Console par bhi sirf INFO+ level dikhao
        console_handler.setLevel(logging.INFO)

        # Console par bhi raw JSON message dikhao
        # RESULT → terminal par: {"event": "...", "level": "info", ...} dikhega
        console_handler.setFormatter(logging.Formatter("%(message)s"))

        # basicConfig = Python ke logging system ko configure karna
        # Dono handlers (file + console) ko ek saath active karna
        # RESULT → ab logger.info() likhne se dono jagah output jayega
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",           # Structlog JSON banayega, yeh sirf pass karega
            handlers=[console_handler, file_handler]  # ← FILE + CONSOLE dono active
        )

        # Structlog ko configure karna — yeh actual JSON message banata hai
        structlog.configure(
            processors=[
                # Step 1: Har message mein timestamp add karo (UTC/ISO format mein)
                # RESULT → "timestamp": "2026-03-27T18:25:00Z"
                structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),

                # Step 2: Log level add karo (info / warning / error)
                # RESULT → "level": "info"
                structlog.processors.add_log_level,

                # Step 3: message key ka naam "event" rakh do
                # RESULT → "event": "Application start ho rahi hai..."
                structlog.processors.EventRenamer(to="event"),

                # Step 4: Sab kuch ek JSON string mein convert karo
                # RESULT → {"timestamp": "...", "level": "info", "event": "..."}
                structlog.processors.JSONRenderer()
            ],
            # Python ka standard logging system use karna (file+console wala jo upar banaya)
            logger_factory=structlog.stdlib.LoggerFactory(),
            # BoundLogger = extra fields (source=, battery=) add karne ki suvidha deta hai
            wrapper_class=structlog.stdlib.BoundLogger,
            # Pehli baar logger banana slow hota hai — cache karo taake baar baar na bane
            cache_logger_on_first_use=True,
        )

        # Tayyar shuda structured logger wapis karo
        # RESULT → caller ko ek logger milta hai jis par .info() .warning() .error() call kar sakte hain
        return structlog.get_logger(logger_name)


# ─────────────────────────────────────────────────────────────────
# DIRECT RUN TEST — python customlogger.py likhne par yeh chalta hai
# (jab koi doosri file import kare tab nahi chalta — sirf direct run par)
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # CustomLogger ka object banao → logs/ folder bana, .log file ka naam tayyar hua
    logger_setup = CustomLogger()

    # Logger hasil karo → file+console handlers set hue, structlog configure hua
    my_logger = logger_setup.get_logger()

    # INFO level log → Terminal + .log file mein JSON jayega:
    # {"timestamp": "...", "level": "info", "event": "System successfully start ho gaya hai."}
    my_logger.info("System successfully start ho gaya hai.")

    # WARNING log + extra field → free_space bhi JSON mein add hoga:
    # {"timestamp": "...", "level": "warning", "event": "Storage thori kam hai.", "free_space": "2GB"}
    my_logger.warning("Storage thori kam hai.", free_space="2GB")

    # ERROR log → sabse serious level:
    # {"timestamp": "...", "level": "error", "event": "Database se connection toot gaya!"}
    my_logger.error("Database se connection toot gaya!")