import sys
import traceback
from typing import Optional, cast

class DocumentPortalException(Exception):
    def __init__(self, error_message, error_details: Optional[object] = None):
        # 1. Normalize message (Error message ko string mein badalna)
        if isinstance(error_message, BaseException):
            norm_msg = str(error_message)
        else:
            norm_msg = str(error_message)
            
        # 2. Resolve exc_info (Error ki details nikalna)
        exc_type = exc_value = exc_tb = None
        if error_details is None:
            exc_type, exc_value, exc_tb = sys.exc_info()
        else:
            if hasattr(error_details, "exc_info"):  # e.g., sys
                exc_info_obj = cast(sys, error_details)
                exc_type, exc_value, exc_tb = exc_info_obj.exc_info()
            elif isinstance(error_details, BaseException):
                exc_type, exc_value, exc_tb = type(error_details), error_details, error_details.__traceback__
            else:
                exc_type, exc_value, exc_tb = sys.exc_info()

        # 3. Walk to the last frame to report the most relevant location (Asal masle ki jagah dhoondna)
        last_tb = exc_tb
        while last_tb and last_tb.tb_next:
            last_tb = last_tb.tb_next

        self.file_name = last_tb.tb_frame.f_code.co_filename if last_tb else "<unknown>"
        self.lineno = last_tb.tb_lineno if last_tb else -1
        self.error_message = norm_msg

        # 4. Full pretty traceback (if available) - (Mukammal history save karna)
        if exc_type and exc_tb:
            self.traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        else:
            self.traceback_str = ""

        # Parent class (Exception) ko initialize karna
        super().__init__(self.__str__())

    def __str__(self):
        return f"{self.error_message} (File: {self.file_name}, Line: {self.lineno})"

    def __repr__(self):
        return f"DocumentPortalException(file={self.file_name!r}, line={self.lineno}, message={self.error_message!r})"


# --- TEST KARNE KE LIYE (Aap isay run kar ke check kar sakte hain) ---
if __name__ == "__main__":
    def faulty_function():
        # Jaan boojh kar ek error paida karte hain (Divide by zero)
        return 10 / 0

    try:
        faulty_function()
    except Exception as original_error:
        # Original error ko pakar kar apne Custom Exception mein daal diya
        custom_error = DocumentPortalException("Math ka calculation fail ho gaya!", error_details=original_error)
        
        print("--- CUSTOM ERROR PAKRA GAYA ---")
        print(repr(custom_error))
        print("\n--- ERROR KI MUKAMMAL HISTORY (Traceback) ---")
        print(custom_error.traceback_str)