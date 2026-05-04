from __future__ import annotations
# INPUT : Python version compatibility directive
# OUTPUT: "annotations" feature ON — type hints strings tak simit hain, runtime par evaluate nahi hoti
#         (Python 3.7+ mein future feature tha, 3.10+ mein default hai)

import re
# INPUT : Standard library — Regular Expressions ka module
# OUTPUT: re.sub() jaise functions milte hain jo strings mein pattern dhoondh kar replace karte hain
#         MISAAL: re.sub(r'[^a-zA-Z0-9]', '_', "my file.pdf") → "my_file_pdf"

import uuid
# INPUT : Standard library — Universally Unique Identifier banane ke liye
# OUTPUT: uuid.uuid4().hex → 32 character ka random hexadecimal string
#         MISAAL: uuid.uuid4().hex[:6] → "a3f7c1"  (har baar naya, unique)

from pathlib import Path
# INPUT : Standard library — File aur folder paths handle karne ke liye OOP style
# OUTPUT: Path objects milte hain jo .suffix, .stem, .mkdir() jaisi properties dete hain
#         MISAAL: Path("docs/file.pdf").suffix → ".pdf"

from typing import Iterable, List
# INPUT : Standard library — Type hints ke liye
# OUTPUT: Iterable[X] = koi bhi loop-able cheez (list, generator, tuple)
#         List[X]     = specifically Python list
#         MISAAL: List[Path] = Path objects ki list

from multi_doc_chat.logger.customlogger import CustomLogger
# INPUT : Hamare project ka apna logger (customlogger.py se)
# OUTPUT: CustomLogger class import hoti hai jis ka .get_logger() structlog logger deta hai
#         NOTICE: File ka naam "customlogger.py" hai (bina space) — is liye yahi import sahi hai

from multi_doc_chat.exception.custom_exception import DocumentPortalException
# INPUT : Hamare project ki apni exception class (custom_exception.py se)
# OUTPUT: DocumentPortalException class milti hai jo error message + file name + line number
#         automatically capture karti hai — debugging mein bahut madad karti hai


# ─────────────────────────────────────────────────────────────────────────────
#  SUPPORTED FILE TYPES KI LIST
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".pdf",     # Adobe PDF documents — sab se common document format
    ".docx",    # Microsoft Word files
    ".txt",     # Plain text files
    ".pptx",    # Microsoft PowerPoint presentations
    ".md",      # Markdown files — documentation ke liye
    ".csv",     # Comma Separated Values — tabular data
    ".xlsx",    # Microsoft Excel (new format)
    ".xls",     # Microsoft Excel (old format)
    ".db",      # SQLite database file
    ".sqlite",  # SQLite database file (alternate extension)
    ".sqlite3", # SQLite database file (version 3 extension)
}
# INPUT : Allowed file extensions ka set (set = O(1) lookup — list se zyada fast)
# OUTPUT: Jab bhi koi file upload ho, iska extension is set se check hoga
#         MISAAL: ".pdf" in SUPPORTED_EXTENSIONS → True   (allowed)
#                 ".exe" in SUPPORTED_EXTENSIONS → False  (reject hoga)


# ─────────────────────────────────────────────────────────────────────────────
#  MODULE-LEVEL LOGGER SETUP
# ─────────────────────────────────────────────────────────────────────────────
logger_setup = CustomLogger()
# INPUT : CustomLogger() — bina kisi argument ke (default log_dir="logs" use hoga)
# OUTPUT: CustomLogger object banta hai:
#         - logs/ folder project root mein create hota hai (agar nahi tha toh)
#         - Naya .log file naam tayyar hota hai (jaise: 04_30_2026_22_15_00.log)
#         MISAAL: C:\Users\...\LLMOPS_SERIES\logs\04_30_2026_22_15_00.log

log = logger_setup.get_logger(__name__)
# INPUT : __name__ = is module ka naam (jaise: "multi_doc_chat.utils.file_io")
# OUTPUT: Structlog ka configured logger object milta hai jis se yeh log ho sakta hai:
#         log.info("...")    → JSON format mein info log
#         log.warning("...") → JSON format mein warning log
#         log.error("...")   → JSON format mein error log
#         MISAAL terminal output: {"timestamp": "2026-04-30T17:15:00Z", "level": "info",
#                                  "event": "File saved for ingestion", "uploaded": "report.pdf"}


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN FUNCTION: UPLOADED FILES KO DISK PAR SAVE KARNA
# ─────────────────────────────────────────────────────────────────────────────
def save_uploaded_files(uploaded_files: Iterable, target_dir: Path) -> List[Path]:
    """
    Uploaded files (Streamlit ya FastAPI UploadFile) ko disk par save karo.

    Parameters
    ----------
    uploaded_files : Iterable
        Koi bhi loop-able collection jisme uploaded file objects hon.
        Supported objects:
          - Starlette / FastAPI UploadFile → .filename + .file attributes hote hain
          - Streamlit UploadedFile        → .name + .read() method hoti hai
          - BytesIO / similar             → .read() ya .getbuffer() hota hai

    target_dir : Path
        Woh folder path jahan files disk par save ki jayengi.
        MISAAL: Path("uploads/session_abc123")

    Returns
    -------
    List[Path]
        Un tamaam files ki Path list jo successfully save hui hain.
        MISAAL: [Path("uploads/session_abc123/a3f7c1b2.pdf"),
                 Path("uploads/session_abc123/d9e2f1a0.docx")]

    Raises
    ------
    DocumentPortalException
        Agar koi unexpected error aaye (disk full, permission denied, etc.)
    """

    try:
        # ── STEP 1: TARGET FOLDER BANANA ─────────────────────────────────
        target_dir.mkdir(parents=True, exist_ok=True)
        # INPUT : target_dir = Path("uploads/session_abc123")
        # OUTPUT: Folder "uploads/session_abc123" disk par ban jata hai
        #         parents=True  → beech ke folders bhi bana deta hai (agar nahi the)
        #         exist_ok=True → folder pehle se ho toh koi error nahi aata
        #         MISAAL: Path("uploads/session_abc/").mkdir() → folder ready

        saved: List[Path] = []
        # INPUT : Khali Python list initialize ki
        # OUTPUT: Baad mein jo files successfully save hongi, unke Path objects yahan add honge
        #         MISAAL: saved = [] → phir → saved = [Path("uploads/.../a3f7c1.pdf")]

        # ── STEP 2: HARF HARF FILE PROCESS KARO ─────────────────────────
        for uf in uploaded_files:
            # INPUT : uploaded_files = [uf1, uf2, uf3, ...] — har loop mein aik file object aata hai
            # OUTPUT: uf = current file object
            #         MISAAL uf (Streamlit): uf.name="report.pdf", uf.read()=b"..."
            #         MISAAL uf (FastAPI):   uf.filename="report.pdf", uf.file=<SpooledTemporaryFile>

            # ── STEP 2a: FILE KA ORIGINAL NAAM NIKALO ────────────────────
            name = getattr(uf, "filename", getattr(uf, "name", "file"))
            # INPUT : uf — file object (Starlette ya Streamlit ya kuch aur)
            # OUTPUT: name = original file ka naam string
            #         getattr(uf, "filename", ...) → FastAPI UploadFile ke liye: "report.pdf"
            #         getattr(uf, "name", "file")  → Streamlit ke liye: "report.pdf"
            #         "file"                        → fallback agar dono nahi mile
            #         MISAAL: name = "my report 2024.pdf"

            # ── STEP 2b: EXTENSION NIKALO AUR LOWERCASE BANAO ────────────
            ext = Path(name).suffix.lower()
            # INPUT : name = "my report 2024.PDF"
            # OUTPUT: ext  = ".pdf"  (lowercase — taake ".PDF" aur ".pdf" dono match hon)
            #         Path("my report 2024.PDF").suffix → ".PDF"
            #         .lower()                           → ".pdf"
            #         MISAAL: ext = ".pdf"

            # ── STEP 2c: UNSUPPORTED FILES SKIP KARO ─────────────────────
            if ext not in SUPPORTED_EXTENSIONS:
                # INPUT : ext = ".exe"  (ya koi aur unsupported format)
                # OUTPUT: Warning log hoga aur yeh file skip ho jayegi (continue)
                log.warning(
                    "Unsupported file type — skipped",
                    # ↑ Log ka main event message
                    filename=name,
                    # ↑ Kaunsi file skip hui — JSON field mein record hoga
                    supported=sorted(SUPPORTED_EXTENSIONS),
                    # ↑ Allowed extensions bhi log mein dalein — debugging mein madad
                )
                # MISAAL log output:
                # {"event": "Unsupported file type — skipped", "level": "warning",
                #  "filename": "virus.exe", "supported": [".csv", ".db", ...]}
                continue
                # INPUT : (koi nahi)
                # OUTPUT: Loop ka yeh iteration skip — next file par jao

            # ── STEP 2d: UNIQUE SAFE FILE NAAM BANAO ─────────────────────
            safe_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(name).stem).lower()
            # INPUT : name = "my report 2024.pdf"
            #         Path(name).stem → "my report 2024"
            # OUTPUT: safe_stem = "my_report_2024"
            #         re.sub() → har character jo alphanumeric, dash, ya underscore nahi
            #                    use '_' se replace karo
            #         .lower() → sab lowercase
            #         MISAAL: "My File (copy).pdf" → stem="My File (copy)" → "my_file__copy_"

            fname = f"{safe_stem}_{uuid.uuid4().hex[:8]}{ext}"
            # INPUT : safe_stem = "my_report_2024"
            #         uuid.uuid4().hex[:8] = "a3f7c1b2"  (8 char ka random hex)
            #         ext = ".pdf"
            # OUTPUT: fname = "my_report_2024_a3f7c1b2.pdf"
            #         Har upload ka naam unique hoga — name collision impossible
            #         MISAAL: "report_a3f7c1b2.pdf", "report_d9e2f1a0.pdf" (alag alag runs)

            # ── STEP 2e: FINAL OUTPUT PATH BANAO ─────────────────────────
            out = target_dir / fname
            # INPUT : target_dir = Path("uploads/session_abc123")
            #         fname      = "my_report_2024_a3f7c1b2.pdf"
            # OUTPUT: out = Path("uploads/session_abc123/my_report_2024_a3f7c1b2.pdf")
            #         "/" operator Path objects ko join karta hai (os.path.join ka OOP version)

            # ── STEP 2f: FILE KA DATA PARHNA AUR LIKHNA ──────────────────
            with open(out, "wb") as f:
                # INPUT : out  = Path("uploads/session_abc123/my_report_2024_a3f7c1b2.pdf")
                #         "wb" = write-binary mode (text nahi, raw bytes)
                # OUTPUT: File disk par khul jati hai likhne ke liye
                #         Context manager (with) → kaam khatam hone par file auto-close

                if hasattr(uf, "file") and hasattr(uf.file, "read"):
                    # INPUT : uf = FastAPI/Starlette UploadFile — uf.file = SpooledTemporaryFile
                    # OUTPUT: uf.file.read() → bytes  (poori file ka raw binary data)
                    #         f.write()      → woh bytes disk par likh deta hai
                    #         MISAAL: b"%PDF-1.4..." (PDF ki raw bytes)
                    f.write(uf.file.read())

                elif hasattr(uf, "read"):
                    # INPUT : uf = Streamlit UploadedFile ya BytesIO — .read() method hai
                    # OUTPUT: uf.read() → bytes ya memoryview
                    data = uf.read()
                    # INPUT : data = bytes ya memoryview object
                    # OUTPUT: Agar memoryview hai toh bytes mein convert karo
                    #         MISAAL: memoryview(b"hello") → bytes: b"hello"
                    if isinstance(data, memoryview):
                        data = data.tobytes()
                        # INPUT : data = memoryview object
                        # OUTPUT: data = b"..." (proper bytes object)
                    f.write(data)
                    # INPUT : data = bytes
                    # OUTPUT: Bytes disk par likh diye gaye

                else:
                    # INPUT : uf = koi aur object (jaise BytesIO variant) jis mein .getbuffer() ho
                    # OUTPUT: buf = getbuffer function (agar mila)
                    buf = getattr(uf, "getbuffer", None)
                    # INPUT : uf = object, "getbuffer" = method ka naam
                    # OUTPUT: buf = callable function  ya  None (agar nahi mila)
                    #         MISAAL: buf = <built-in method getbuffer of BytesIO>

                    if callable(buf):
                        # INPUT : buf = callable (getbuffer method milgaya)
                        # OUTPUT: buf() → memoryview ya bytes
                        data = buf()
                        if isinstance(data, memoryview):
                            data = data.tobytes()
                            # INPUT : data = memoryview
                            # OUTPUT: data = bytes — safe format for writing
                        f.write(data)
                        # INPUT : data = bytes
                        # OUTPUT: File mein bytes likh diye

                    else:
                        # INPUT : uf = aisa object jis mein koi readable interface nahi
                        # OUTPUT: ValueError raise hogi — yeh unsupported object hai
                        raise ValueError(
                            f"Unsupported uploaded file object '{type(uf).__name__}': "
                            "no readable interface found (.file.read / .read / .getbuffer)"
                        )
                        # MISAAL: ValueError("Unsupported uploaded file object 'MyCustomObj': ...")

            # ── STEP 2g: SAVED LIST MEIN ADD KARO ────────────────────────
            saved.append(out)
            # INPUT : out = Path("uploads/session_abc123/my_report_2024_a3f7c1b2.pdf")
            # OUTPUT: saved list mein yeh path add ho gaya
            #         MISAAL: saved = [Path("uploads/.../my_report_2024_a3f7c1b2.pdf")]

            # ── STEP 2h: SUCCESS LOG ──────────────────────────────────────
            log.info(
                "File saved for ingestion",
                # ↑ Event: kya hua — file ingest ke liye save ho gayi
                uploaded=name,
                # ↑ Original file name — user ne kya upload kiya tha
                saved_as=str(out),
                # ↑ Disk par kahan save hua — debugging ke liye
            )
            # MISAAL log output (terminal + .log file):
            # {"timestamp": "2026-04-30T17:20:00Z", "level": "info",
            #  "event": "File saved for ingestion",
            #  "uploaded": "my report 2024.pdf",
            #  "saved_as": "uploads/session_abc123/my_report_2024_a3f7c1b2.pdf"}

        # ── STEP 3: SAVED FILES KI LIST WAPIS KARO ───────────────────────
        return saved
        # INPUT : (koi nahi — loop khatam ho gaya)
        # OUTPUT: List[Path] — successfully saved files ki paths
        #         MISAAL: [Path("uploads/.../a3f7.pdf"), Path("uploads/.../b8e2.docx")]
        #         Agar koi file nahi bachi (sab unsupported thi): []

    except Exception as e:
        # INPUT : e = koi bhi unexpected exception object
        #         MISAAL: PermissionError, OSError, ValueError, etc.
        # OUTPUT: Error log hoga aur DocumentPortalException raise hogi

        log.error(
            "Failed to save uploaded files",
            # ↑ Event: kya galat hua
            error=str(e),
            # ↑ Original error ka message — JSON mein record hoga
            target_dir=str(target_dir),
            # ↑ Kaunse folder mein save karna tha — context ke liye
        )
        # MISAAL log output:
        # {"timestamp": "...", "level": "error",
        #  "event": "Failed to save uploaded files",
        #  "error": "[Errno 13] Permission denied: 'uploads/...'",
        #  "target_dir": "uploads/session_abc123"}

        raise DocumentPortalException(
            "Failed to save uploaded files",
            # ↑ Human-readable custom message
            error_details=e,
            # ↑ Original exception — DocumentPortalException iske andar se
            #   file naam aur line number khud extract karega
        ) from e
        # INPUT : e = original exception
        # OUTPUT: DocumentPortalException raise hoti hai jis mein:
        #         .error_message = "Failed to save uploaded files"
        #         .file_name     = "file_io.py"
        #         .lineno        = exact line number jahan error hua
        #         .traceback_str = poori error history (chain)
        # "from e" → Python mein exception chaining maintain karti hai
        # MISAAL: DocumentPortalException("Failed to save...", File: file_io.py, Line: 143)


"""
=============================================================================
🎯 FILE KA MAQSAD (DETAILED OBJECTIVE)
=============================================================================

Is file (file_io.py) ka main kaam hai — kisi bhi jagah se upload hui files
(chahe Streamlit se hon, FastAPI se hon, ya kisi aur framework se) ko safely,
reliably aur traceable tarike se disk par save karna, taake baad mein
document ingestion pipeline (ChatIngestor, FaissManager) un files ko utha
kar process kar sake.

───────────────────────────────────────────────────────────────────────────────
⚠️ YEH FUNCTION KYU ZARURI HAI?
───────────────────────────────────────────────────────────────────────────────
LLMOps pipeline mein documents (PDF, DOCX, CSV wagera) alag alag sources se
aakar ingest hote hain. Har framework ka "uploaded file object" thoda alag
hota hai:

  - Streamlit UploadedFile  → .name + .read()
  - FastAPI/Starlette       → .filename + .file (SpooledTemporaryFile)
  - Python BytesIO          → .read() ya .getbuffer()

Agar is difference ko handle na kiya jaye, to ek framework ke liye likha
code doosre framework mein crash kar jata hai. Is function ne ek unified
interface banaya hai jo teen qisam ke objects ko ek hi jagah handle karta hai.

───────────────────────────────────────────────────────────────────────────────
✅ IS FILE KE FAYDE (OBJECTIVES ACHIEVED)
───────────────────────────────────────────────────────────────────────────────

1. MULTI-FRAMEWORK COMPATIBILITY:
   Ek hi function teen qisam ke file objects support karta hai — Starlette,
   Streamlit, aur BytesIO. Koi bhi naya object aaye to sirf ek jagah code
   update karna hoga.

2. UNIQUE FILE NAMING (COLLISION PREVENTION):
   Har save ki gayi file ka naam: {safe_stem}_{uuid8}{ext}
   MISAAL: "my_report_2024_a3f7c1b2.pdf"
   UUID ensure karta hai ke agar 100 log ek hi naam ki file upload karein
   to koi overwrite na ho — har file alag file hogi.

3. EXTENSION FILTERING (SECURITY + CORRECTNESS):
   Sirf allowed extensions (SUPPORTED_EXTENSIONS) wali files save hoti hain.
   .exe, .py, .sh wagera reject kar diye jate hain — security ka pehla qaddam.

4. STRUCTURED LOGGING (AUDITABILITY):
   Har save par JSON format mein log likha jata hai (original naam + saved path).
   Agar baad mein koi masla aaye, log file mein history milegi:
   "2026-04-30: user ne report.pdf upload kiya, a3f7c1b2.pdf mein save hua"

5. DETAILED ERROR HANDLING (DEBUGGING):
   Agar koi bhi unexpected error aaye (disk full, permission error, etc.) to:
   - log.error() se structured JSON error log hota hai
   - DocumentPortalException raise hoti hai jis mein:
       ✔ Custom message
       ✔ File ka naam (file_io.py)
       ✔ Exact line number
       ✔ Poori traceback history
   Yeh debugging ko minutes ka kaam bana deta hai.

───────────────────────────────────────────────────────────────────────────────
🔄 PIPELINE MEIN IS FILE KA ROLE
───────────────────────────────────────────────────────────────────────────────

  [User Upload (Streamlit/FastAPI)]
           ↓
  save_uploaded_files()   ← YEH FILE YAHAN KAAM KARTI HAI
           ↓
  [Disk par safe unique files]
           ↓
  ChatIngestor.ingest_documents()   (data_injection.py)
           ↓
  [Text chunks → Embeddings → FAISS Vector DB]
           ↓
  [User ka question → Similarity Search → LLM → Answer]

=============================================================================
"""
