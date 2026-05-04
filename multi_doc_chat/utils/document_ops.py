from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from fastapi import UploadFile

from multi_doc_chat.logger.customlogger import CustomLogger
from multi_doc_chat.exception.custom_exception import DocumentPortalException


# ─────────────────────────────────────────────────────────────────────────────
#  MODULE-LEVEL LOGGER SETUP
# ─────────────────────────────────────────────────────────────────────────────
_logger_setup = CustomLogger()
log = _logger_setup.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  SUPPORTED DOCUMENT EXTENSIONS (SIRF INHE LOADERS SUPPORT KARTE HAIN)
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
# NOTE: file_io.py mein SUPPORTED_EXTENSIONS zyada broad hai (xlsx, csv, db wagera bhi)
#       lekin document_ops.py sirf woh formats support karta hai jinke liye
#       LangChain ke paas actual loaders maujood hain.


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN FUNCTION: DISK PAR SAVED FILES KO LANGCHAIN DOCUMENTS MEIN CONVERT KARO
# ─────────────────────────────────────────────────────────────────────────────
def load_documents(paths: Iterable[Path]) -> List[Document]:
    """
    Disk par maujood files ko parh kar LangChain Document objects ki list banao.

    Yeh function pipeline ka doosra qadam hai:
      [User Upload] → save_uploaded_files() → load_documents() ← YEH YAHAN HAI
                                                      ↓
                                          [Text + Metadata Documents]
                                                      ↓
                                          [ChatIngestor → FAISS DB]

    Parameters
    ----------
    paths : Iterable[Path]
        Un files ki Path objects ki list jo disk par save ho chuki hain.
        MISAAL: [Path("uploads/session_abc/report_a3f7c1b2.pdf"),
                 Path("uploads/session_abc/notes_d9e2f1a0.txt")]

    Returns
    -------
    List[Document]
        LangChain Document objects ki list.
        Har Document mein:
          - .page_content → us page/file ka actual text
          - .metadata     → {"source": "path/to/file", "page": 0}

    Raises
    ------
    DocumentPortalException
        Agar koi unexpected error aaye (file corrupt ho, permissions na hon, wagera)
    """

    docs: List[Document] = []

    try:
        # ── STEP 1: HARF HARF FILE PROCESS KARO ──────────────────────────────
        for p in paths:

            # ── STEP 1a: FILE KA EXTENSION NIKALO ────────────────────────────
            ext = p.suffix.lower()

            # ── STEP 1b: SAHI LOADER CHUNIYE ─────────────────────────────────
            if ext == ".pdf":
                # Har page ka ek alag Document object banta hai
                loader = PyPDFLoader(str(p))

            elif ext == ".docx":
                # Poora DOCX ek single Document mein aata hai
                loader = Docx2txtLoader(str(p))

            elif ext == ".txt":
                # encoding="utf-8" → Urdu, Arabic, Chinese wagera bhi sahi parhe
                loader = TextLoader(str(p), encoding="utf-8")

            else:
                # ── UNSUPPORTED EXTENSION: SKIP KARO ─────────────────────────
                log.warning(
                    "Unsupported extension skipped",
                    path=str(p),
                    supported=sorted(SUPPORTED_EXTENSIONS),
                )
                continue

            # ── STEP 1c: LOADER SE DOCUMENTS LOAD KARO ───────────────────────
            docs.extend(loader.load())

        # ── STEP 2: SUCCESS LOG ───────────────────────────────────────────────
        log.info("Documents loaded", count=len(docs))

        # ── STEP 3: DOCUMENTS KI LIST WAPIS KARO ─────────────────────────────
        return docs

    except Exception as e:
        log.error("Failed loading documents", error=str(e))
        raise DocumentPortalException(
            "Error loading documents",
            error_details=e,
        ) from e


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER CLASS: FastAPI UploadFile KO UNIFIED INTERFACE MEIN CONVERT KARO
# ─────────────────────────────────────────────────────────────────────────────
class FastAPIFileAdapter:
    """
    FastAPI ke UploadFile object ko ek simple, unified interface mein wrap karo.

    PROBLEM:
        file_io.py ka save_uploaded_files() function teen qisam ke objects
        support karta hai (.filename, .file.read, .read, .getbuffer).
        Lekin kabhi kabhi aapko directly FastAPI UploadFile se bytes chahiye
        hoti hain kisi aur jagah — is liye yeh adapter hai.

    SOLUTION:
        Is class ka object banao aur aapko milega:
          .name        → original file naam (string)
          .getbuffer() → file ka raw binary data (bytes)

    USE KAISE KARO (MISAAL):
        @app.post("/upload")
        async def upload(file: UploadFile):
            adapted = FastAPIFileAdapter(file)
            print(adapted.name)         # "report.pdf"
            data = adapted.getbuffer()  # b"%PDF-1.4..."
    """

    def __init__(self, uf: UploadFile):
        self._uf = uf
        self.name = uf.filename or "file"
        # uf.filename = None hone par fallback naam "file" use hoga

    def getbuffer(self) -> bytes:
        """
        UploadFile ki binary content (raw bytes) wapis karo.

        Returns
        -------
        bytes
            File ka poora binary data.

        NOTE:
            seek(0) isliye zaruri hai kyunki FastAPI pehle hi file ko
            partially parh chuka hota hai — bina seek(0) ke bytes missing
            ho sakti hain.
        """
        self._uf.file.seek(0)   # cursor wapas shuruaat par lao
        return self._uf.file.read()


"""
=============================================================================
🎯 IS FILE (document_ops.py) KA MAQSAD (DETAILED OBJECTIVE)
=============================================================================

Is file ka kaam hai — disk par save shuda files (PDF, DOCX, TXT) ko parh kar
LangChain ke Document objects mein convert karna, taake baad mein ChatIngestor
unhe process karke FAISS vector database mein store kar sake.

───────────────────────────────────────────────────────────────────────────────
🔄 PIPELINE MEIN IS FILE KA ROLE
───────────────────────────────────────────────────────────────────────────────

  [User Upload (Streamlit / FastAPI)]
           ↓
  save_uploaded_files()       ← file_io.py ka kaam
           ↓
  [Disk par safe, unique files — e.g. "report_a3f7c1b2.pdf"]
           ↓
  load_documents()            ← YEH FILE YAHAN KAAM KARTI HAI
           ↓
  [List[Document] — har page/section ek alag Document object]
           ↓
  ChatIngestor.ingest_documents()   ← data_ingestion.py ka kaam
           ↓
  [Text chunks → Embeddings → FAISS Vector DB]
           ↓
  [User ka question → Similarity Search → LLM → Answer]

───────────────────────────────────────────────────────────────────────────────
✅ IS FILE KE FAYDE
───────────────────────────────────────────────────────────────────────────────

1. MULTI-FORMAT SUPPORT:
   Ek hi function teen qisam ki files handle karta hai:
     - PDF  → PyPDFLoader    (har page alag Document)
     - DOCX → Docx2txtLoader (poori file ek Document)
     - TXT  → TextLoader     (poori file ek Document, UTF-8 encoding)

2. SAFE EXTENSION FILTERING:
   Sirf supported extensions (.pdf, .docx, .txt) wali files load hoti hain.
   Baaki skip ho jati hain with a warning log — koi crash nahi.

3. PROJECT PATTERNS KE SAATH ALIGNED:
   - CustomLogger use kiya (GLOBAL_LOGGER nahi — project ka actual pattern)
   - DocumentPortalException(msg, error_details=e) — sahi signature

4. FastAPIFileAdapter:
   FastAPI ke UploadFile ko ek simple .name + .getbuffer() interface deta hai
   taake file_io.py ka save_uploaded_files() ise bhi handle kar sake.

───────────────────────────────────────────────────────────────────────────────
⚠️ file_io.py SE FARQ (DIFFERENCE)
───────────────────────────────────────────────────────────────────────────────

  file_io.py      → uploaded files ko DISK PAR SAVE karta hai
  document_ops.py → disk par saved files ko LANGCHAIN DOCUMENTS mein LOAD karta hai

  Dono milkar pipeline ka Step 1 aur Step 2 banate hain.

=============================================================================
"""
