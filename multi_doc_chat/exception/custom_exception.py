import sys          # Misaal: Jaise aap doctor se poochte ho "abhi kya hua?" — sys bhi Python se poochta hai "abhi kaunsi error chal rahi hai?"
import traceback    # Misaal: Jaise crime scene ki history — error kahan se shuru hoker kahan tak gaya
from typing import Optional, cast
# Optional matlab: "yeh value ho bhi sakti hai ya na bhi ho"
# Misaal: Optional[str] → ya toh "hello" hoga ya None hoga


# ═══════════════════════════════════════════════════════════════
#  YEH HAMARI APNI CUSTOM ERROR CLASS HAI
# ═══════════════════════════════════════════════════════════════
#
#  Python mein pehle se errors hote hain jaise:
#    ZeroDivisionError  → 10/0 karne par
#    FileNotFoundError  → file na mile toh
#    ValueError         → wrong value dene par
#
#  Lekin un errors mein sirf ek line hoti hai jaise:
#    "division by zero"
#
#  Hamari class yeh kaam karti hai:
#    ✅ File ka naam bhi batao (kahan hua)
#    ✅ Line number bhi batao (kis line par hua)
#    ✅ Apna custom message bhi do
#    ✅ Poori history (traceback) bhi save karo
#
#  USE KAISE KARO:
#    raise DocumentPortalException("Document nahi mila!")
# ═══════════════════════════════════════════════════════════════
class DocumentPortalException(Exception):

    def __init__(self, error_message, error_details: Optional[object] = None):
        #
        # error_message  → aap apna message dete ho
        #   MISAAL: "File upload nahi hoi" ya "Database band hai"
        #
        # error_details  → optional: original Python error dete ho
        #   MISAAL: except Exception as e → e yahan dete ho
        #   Agar nahi diya toh None hoga (default)
        #

        # ┌─────────────────────────────────────────────────────┐
        # │  STEP 1: MESSAGE KO SAFE STRING BANAO               │
        # └─────────────────────────────────────────────────────┘
        #
        #  Kabhi kabhi error_message ek Exception object hota hai
        #  Kabhi seedha "string" hota hai
        #  Dono cases mein str() lagao — safe string mil jayegi
        #
        #  MISAAL:
        #    error_message = "File nahi mili"     → norm_msg = "File nahi mili"
        #    error_message = ValueError("galat!") → norm_msg = "galat!"
        #
        if isinstance(error_message, BaseException):
            norm_msg = str(error_message)   # Exception object tha → text nikaal liya
        else:
            norm_msg = str(error_message)   # Pehle se string tha → waise hi rakha

        # ┌─────────────────────────────────────────────────────┐
        # │  STEP 2: ERROR KI TECHNICAL DETAILS NIKALO          │
        # └─────────────────────────────────────────────────────┘
        #
        #  Teen cheezein chahiye:
        #    exc_type  → Error ki qisam  → MISAAL: ZeroDivisionError
        #    exc_value → Error ka message → MISAAL: "division by zero"
        #    exc_tb    → Error ka trail   → MISAAL: line 10 → line 5 → line 2
        #
        exc_type = exc_value = exc_tb = None   # pehle teeno ko khali rakho

        if error_details is None:
            # Aap ne koi error_details nahi diya
            # Python se poocho: "abhi kaunsi error active hai?"
            # MISAAL: except ke andar ho toh Python batayega kya hua
            exc_type, exc_value, exc_tb = sys.exc_info()

        else:
            if hasattr(error_details, "exc_info"):
                # Agar koi special object diya jisme exc_info() method ho (bahut rare case)
                exc_info_obj = cast(sys, error_details)
                exc_type, exc_value, exc_tb = exc_info_obj.exc_info()

            elif isinstance(error_details, BaseException):
                # Seedha Exception object diya — yeh sabse common case hai!
                #
                # MISAAL:
                #   except Exception as e:
                #       raise DocumentPortalException("galat!", error_details=e)
                #                                                           ↑ yeh e yahan aata hai
                #
                #   exc_type  = ZeroDivisionError   (error ki qisam)
                #   exc_value = e                    (error ka object)
                #   exc_tb    = e.__traceback__      (kahan hua trail)
                #
                exc_type, exc_value, exc_tb = type(error_details), error_details, error_details.__traceback__

            else:
                # Kuch aur diya — directly Python se lo
                exc_type, exc_value, exc_tb = sys.exc_info()

        # ┌─────────────────────────────────────────────────────┐
        # │  STEP 3: ASAL MASLE KI LINE DHOONDO                 │
        # └─────────────────────────────────────────────────────┘
        #
        #  Error ek chain ki tarah hoti hai:
        #    main() → load_file() → read_line() → 💥 ERROR
        #
        #  Traceback (exc_tb) mein yeh poori chain hoti hai
        #  Hum seedha AAKHRI frame tak pohanchte hain — wahan actual error hua
        #
        #  MISAAL (chain ka safar):
        #    exc_tb           → main() ka frame
        #    exc_tb.tb_next   → load_file() ka frame
        #    exc_tb.tb_next   → read_line() ka frame  ← last_tb yahan rukta hai
        #    tb_next = None   → chain khatam
        #
        last_tb = exc_tb                    # chain ki shuruwat se shuru karo
        while last_tb and last_tb.tb_next:
            last_tb = last_tb.tb_next       # agle frame par jao jab tak chain khatam na ho

        # Aakhri frame se file ka naam nikalo
        # MISAAL: self.file_name = "custom_exception.py"
        self.file_name = last_tb.tb_frame.f_code.co_filename if last_tb else "<unknown>"

        # Aakhri frame se line number nikalo
        # MISAAL: self.lineno = 113
        self.lineno = last_tb.tb_lineno if last_tb else -1

        # Clean message save karo
        # MISAAL: self.error_message = "Math ka calculation fail ho gaya!"
        self.error_message = norm_msg

        # ┌─────────────────────────────────────────────────────┐
        # │  STEP 4: POORI ERROR HISTORY SAVE KARO              │
        # └─────────────────────────────────────────────────────┘
        #
        #  traceback.format_exception() → error ki poori kahani deta hai
        #
        #  MISAAL output:
        #    Traceback (most recent call last):
        #      File "test.py", line 58, in <module>
        #        faulty_function()
        #      File "test.py", line 55, in faulty_function
        #        return 10 / 0        ← yahan error hua
        #    ZeroDivisionError: division by zero
        #
        if exc_type and exc_tb:
            self.traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            # "".join() → list ki saari lines ko ek bari string mein jodta hai
        else:
            self.traceback_str = ""  # koi traceback nahi mila → khali rakho

        # Parent Exception class ko bhi batao yeh error kya hai
        # RESULT: Python ka error system samajh jaata hai is error ka message
        super().__init__(self.__str__())

    # ─────────────────────────────────────────────────────────
    #  JAB print(error) LIKHTE HAIN TAB YEH CHALTA HAI
    # ─────────────────────────────────────────────────────────
    def __str__(self):
        # MISAAL output:
        # "Math ka calculation fail ho gaya! (File: custom_exception.py, Line: 113)"
        return f"{self.error_message} (File: {self.file_name}, Line: {self.lineno})"

    # ─────────────────────────────────────────────────────────
    #  JAB repr(error) LIKHTE HAIN TAB YEH CHALTA HAI
    #  (Zyada detailed format — debugging ke liye)
    # ─────────────────────────────────────────────────────────
    def __repr__(self):
        # MISAAL output:
        # DocumentPortalException(file='custom_exception.py', line=113, message='Math ka...')
        return f"DocumentPortalException(file={self.file_name!r}, line={self.lineno}, message={self.error_message!r})"


# ═══════════════════════════════════════════════════════════════
#  DIRECT RUN TEST — python custom_exception.py likhne par
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":

    def faulty_function():
        # Jaan boojh kar 10 ko 0 se divide karte hain
        # Yeh hamesha ZeroDivisionError deta hai
        # MISAAL: Jaise ATM mein 0 rupay withdraw karne ki koshish karo
        return 10 / 0

    try:
        faulty_function()   # Yahan error aayega

    except Exception as original_error:
        # original_error = Python ka ZeroDivisionError object
        # Ise apni class mein wrap karo — apna message + file + line mile
        custom_error = DocumentPortalException(
            "Math ka calculation fail ho gaya!",   # apna custom message
            error_details=original_error           # original error diya
        )

        print("--- CUSTOM ERROR PAKRA GAYA ---")
        print(repr(custom_error))
        # EXPECTED OUTPUT:
        # DocumentPortalException(file='...custom_exception.py', line=113, message='Math ka calculation fail ho gaya!')

        print("\n--- ERROR KI MUKAMMAL HISTORY (Traceback) ---")
        print(custom_error.traceback_str)
        # EXPECTED OUTPUT:
        # Traceback (most recent call last):
        #   File "custom_exception.py", line 117, in <module>
        #     faulty_function()
        #   File "custom_exception.py", line 113, in faulty_function
        #     return 10 / 0
        # ZeroDivisionError: division by zero

"""
=============================================================================
🎯 CODE KA DETAILED OBJECTIVE (MAQSAD)
=============================================================================
Is custom exception (DocumentPortalException) file ka main maqsad yeh hai ke 
Python ke aam (normal) errors ko zyada detail aur asaan zaban mein capture 
kiya jaye, taake Production (yaani jab app live ho) mein jab bhi koi 
masla aaye, to error ki debugging (masla talash karna) nihayat asaan ho. 

⚠️ Aam Python Errors mein kya masla hai?
Misaal ke tor par jab error aata hai to wo sirf ek line deta hai (jaise 
"division by zero"). Bade projects (jaise apka LLMOps project) mein jab 
hazaaron lines ka code ho, to yeh pata lagana mushkil hota hai ke:
  1. Error kis specific file mein aaya?
  2. Kis line number par fail hua?
  3. Error aane k waqt module kya kaam kar raha tha (custom message)?
  4. Error pichey kahan se shuru ho kar yahan tak pohancha (Traceback)?

✅ Is Custom Exception Ka Faida (Objective Achieved):
1. User-Friendly Messages: Hum har error par apna dsi/custom message de 
   sakte hain (e.g., "Vector Database se connection toot gaya").
2. Pinpoint Accuracy: Yeh code khud-ba-khud (automatically) python ke sys 
   module aur traceback chain ke aakhri hisse (last frame) tak jata hai aur 
   root cause wali file ka naam (self.file_name) aur line (self.lineno) 
   nikal leta hai.
3. Traceback Persistence: Yeh poori error history (traceback_str) apne 
   andar save kar leta hai. Ise log files (.log) mein write kar sakte hain, 
   jis se bug ya error ko theek karna minto (minutes) ka kaam ban jata hai.
=============================================================================
"""