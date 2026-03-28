from multi_doc_chat.logger.customlogger import CustomLogger
import time
import random

# 1. Logger setup karein
logger_setup = CustomLogger()
logger = logger_setup.get_logger(__file__)

def simulate_app():
    logger.info("Application start ho rahi hai...")
    
    try:
        # Simulation: Data loading
        logger.info("Data fetching process shuru...", source="Database", status="connecting")
        time.sleep(1)
        
        # Randomly simulate progress
        for i in range(1, 4):
            logger.info(f"Chunk {i} process ho raha hai...", progress=f"{i*33}%")
            time.sleep(0.5)
        
        # Simulation: Kuch warning paida karte hain
        battery = 15
        if battery < 20:
            logger.warning("System ki battery kam hai!", level="Critical", battery_left=f"{battery}%")
        
        # Simulation: Ek achanak masla (Error)
        logger.info("Final calculation shuru...")
        if random.choice([True, False]):
            raise ValueError("Kuch galat ho gaya simulation mein!")
            
        logger.info("Task kamyabi se mukammal ho gaya! ✅")

    except Exception as e:
        logger.error("Application mein Error agaya!", error_msg=str(e), severity="High")

if __name__ == "__main__":
    simulate_app()
    print("\n--- Test Khatam! Ab apne 'logs/' folder mein ja kar nayi file check karein ---")
