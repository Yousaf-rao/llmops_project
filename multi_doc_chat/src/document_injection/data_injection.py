"""
data_injection.py — Document Ingestion Pipeline
================================================
Yeh file poore ingestion pipeline ka engine hai.
User jab PDF/DOCX/TXT upload karta hai tab yeh file:
  1. File ko disk par save karti hai
  2. Text load karti hai
  3. Text ko chunks mein todti hai
  4. Chunks ko FAISS vector DB mein store karti hai
  5. Chatbot ke liye Retriever return karti hai
"""

from __future__ import annotations             # OUTPUT: (koi output nahi - sirf Python ko type hints samjhata hai)

from pathlib import Path                       # OUTPUT: Path("faiss_index/session_xxx")  jaise objects deta hai
from typing import Iterable, List, Optional, Dict, Any  # OUTPUT: (koi output nahi - sirf type checking ke liye)

from langchain.schema import Document          # OUTPUT: Document(page_content="...", metadata={...})
from langchain_text_splitters import RecursiveCharacterTextSplitter  # OUTPUT: splitter object banata hai
from langchain_community.vectorstores import FAISS   # OUTPUT: FAISS vector database object

from multi_doc_chat.utils.model_loader import ModelLoader             # OUTPUT: ModelLoader() object
from multi_doc_chat.logger import GLOBAL_LOGGER as log                # OUTPUT: logger object (log.info/error use hoga)
from multi_doc_chat.exception.custom_exception import DocumentPortalException  # OUTPUT: custom exception class
from multi_doc_chat.utils.file_io import save_uploaded_files          # OUTPUT: [Path("data/session_xxx/resume.pdf")]
from multi_doc_chat.utils.document_ops import load_documents          # OUTPUT: [Document(...), Document(...)]

import json      # OUTPUT: '{"rows": {"resume.pdf::0": true}}'  (JSON string banana/padhna)
import uuid      # OUTPUT: UUID('a3f9c1b2-...') → phir .hex[:8] → "a3f9c1b2"
import hashlib   # OUTPUT: "b94f6f125c79e3a5ffaa826f..."  (SHA-256 hash string)
import sys       # OUTPUT: <module 'sys' (built-in)>  — system module reference
from datetime import datetime  # OUTPUT: datetime(2026, 4, 24, 22, 55, 0)


# ==============================================================================
# HELPER FUNCTION
# ==============================================================================

def generate_session_id() -> str:
    """Har naye chat session ke liye ek unique ID banata hai."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # OUTPUT: timestamp = "20260424_225500"

    unique_id = uuid.uuid4().hex[:8]
    # OUTPUT: unique_id = "a3f9c1b2"
    #   uuid4()      → UUID('a3f9c1b2-7d3e-4f1a-9b2c-...')
    #   .hex         → "a3f9c1b27d3e4f1a9b2c..."
    #   [:8]         → "a3f9c1b2"  (sirf pehle 8 characters)

    return f"session_{timestamp}_{unique_id}"
    # OUTPUT: "session_20260424_225500_a3f9c1b2"


# ==============================================================================
# CLASS 1: ChatIngestor
# ==============================================================================

class ChatIngestor:
    """Pipeline ka main manager/director class."""

    def __init__(
        self,
        temp_base: str = "data",
        faiss_base: str = "faiss_index",
        use_session_dirs: bool = True,
        session_id: Optional[str] = None,
    ):
        try:
            self.model_loader = ModelLoader()
            # OUTPUT: self.model_loader = <ModelLoader object>
            #   Internally: embedding model (e.g. HuggingFace) load ho gaya

            self.use_session = use_session_dirs
            # OUTPUT: self.use_session = True

            self.session_id = session_id or generate_session_id()
            # OUTPUT: self.session_id = "session_20260424_225500_a3f9c1b2"
            #   session_id argument None tha isliye generate_session_id() call hua

            self.temp_base = Path(temp_base)
            # OUTPUT: self.temp_base = PosixPath('data')

            self.temp_base.mkdir(parents=True, exist_ok=True)
            # OUTPUT: Folder ban gaya → data/  ✅ (ya pehle se tha toh kuch nahi hua)

            self.faiss_base = Path(faiss_base)
            # OUTPUT: self.faiss_base = PosixPath('faiss_index')

            self.faiss_base.mkdir(parents=True, exist_ok=True)
            # OUTPUT: Folder ban gaya → faiss_index/  ✅

            self.temp_dir = self._resolve_dir(self.temp_base)
            # OUTPUT: self.temp_dir = PosixPath('data/session_20260424_225500_a3f9c1b2')
            #   Folder bhi ban gaya: data/session_20260424_225500_a3f9c1b2/  ✅

            self.faiss_dir = self._resolve_dir(self.faiss_base)
            # OUTPUT: self.faiss_dir = PosixPath('faiss_index/session_20260424_225500_a3f9c1b2')
            #   Folder bhi ban gaya: faiss_index/session_20260424_225500_a3f9c1b2/  ✅

            log.info("ChatIngestor initialized",
                     session_id=self.session_id,
                     temp_dir=str(self.temp_dir),
                     faiss_dir=str(self.faiss_dir),
                     sessionized=self.use_session)
            # OUTPUT (console log):
            #   INFO | ChatIngestor initialized
            #     session_id  = "session_20260424_225500_a3f9c1b2"
            #     temp_dir    = "data/session_20260424_225500_a3f9c1b2"
            #     faiss_dir   = "faiss_index/session_20260424_225500_a3f9c1b2"
            #     sessionized = True

        except Exception as e:
            log.error("Failed to initialize ChatIngestor", error=str(e))
            # OUTPUT (agar error aye):
            #   ERROR | Failed to initialize ChatIngestor
            #     error = "No module named 'multi_doc_chat'"

            raise DocumentPortalException("Initialization error in ChatIngestor", e) from e
            # OUTPUT (exception):
            #   DocumentPortalException: Initialization error in ChatIngestor


    def _resolve_dir(self, base: Path) -> Path:
        """Session ka sub-folder resolve karta hai."""

        if self.use_session:
            # self.use_session = True  →  is block mein jayenge

            d = base / self.session_id
            # OUTPUT: d = PosixPath('data/session_20260424_225500_a3f9c1b2')
            #   (base = PosixPath('data'), session_id = "session_20260424_225500_a3f9c1b2")

            d.mkdir(parents=True, exist_ok=True)
            # OUTPUT: Folder bana diya on disk  ✅
            #   data/session_20260424_225500_a3f9c1b2/  (empty abhi)

            return d
            # OUTPUT: PosixPath('data/session_20260424_225500_a3f9c1b2')

        return base
        # OUTPUT (agar use_session=False hota): PosixPath('data')


    def _split(self, docs: List[Document], chunk_size=1000, chunk_overlap=200) -> List[Document]:
        """Bade documents ko chhote chunks mein todata hai."""

        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        # OUTPUT: splitter = <RecursiveCharacterTextSplitter chunk_size=1000 overlap=200>
        #   Yeh splitter pehle \n\n par todta hai, phir \n, phir words par

        chunks = splitter.split_documents(docs)
        # INPUT docs (3 pages ka resume):
        #   [Document(page="Muhammad Ali\nSoftware Eng... (800 chars)", meta={"source":"resume.pdf","page":0}),
        #    Document(page="Projects:\n1. LLMOps... (600 chars)",         meta={"source":"resume.pdf","page":1}),
        #    Document(page="Education:\nBSCS FAST... (400 chars)",        meta={"source":"resume.pdf","page":2})]
        #
        # OUTPUT chunks (7 tukre):
        #   [Document(page="Muhammad Ali\nSoftware Eng...",  meta={"source":"resume.pdf","page":0}),
        #    Document(page="...3 years Python\nSkills:...", meta={"source":"resume.pdf","page":0}),  ← 200 char overlap
        #    Document(page="Skills: LangChain, FAISS...",   meta={"source":"resume.pdf","page":0}),
        #    Document(page="Projects:\n1. LLMOps...",        meta={"source":"resume.pdf","page":1}),
        #    Document(page="...LLMOps RAG\n2. HVAC...",     meta={"source":"resume.pdf","page":1}),
        #    Document(page="Education:\nBSCS FAST...",       meta={"source":"resume.pdf","page":2}),
        #    Document(page="...FAST University 2023",        meta={"source":"resume.pdf","page":2})]

        log.info("Documents split into chunks",
                 total_chunks=len(chunks), chunk_size=chunk_size, overlap=chunk_overlap)
        # OUTPUT (console log):
        #   INFO | Documents split into chunks
        #     total_chunks = 7
        #     chunk_size   = 1000
        #     overlap      = 200

        return chunks
        # OUTPUT: List of 7 Document objects (upar wali list)


    def build_retriever(
        self,
        uploaded_files: Iterable,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        k: int = 5,
        search_type: str = "mmr",
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ):
        """Poora pipeline chalata hai aur chatbot ke liye Retriever return karta hai."""

        try:
            paths = save_uploaded_files(uploaded_files, self.temp_dir)
            # INPUT:  uploaded_files = [<StreamlitUploadedFile name="resume.pdf">]
            # OUTPUT: paths = [PosixPath('data/session_20260424_225500_a3f9c1b2/resume.pdf')]
            #   File disk par copy ho gayi!

            docs = load_documents(paths)
            # INPUT:  paths = [PosixPath('data/.../resume.pdf')]
            # OUTPUT: docs = [
            #   Document(page_content="Muhammad Ali\nSoftware Eng...", metadata={"source":"resume.pdf","page":0}),
            #   Document(page_content="Projects:\n1. LLMOps...",       metadata={"source":"resume.pdf","page":1}),
            #   Document(page_content="Education:\nBSCS FAST...",      metadata={"source":"resume.pdf","page":2}),
            # ]  ← 3 Document objects (ek per page)

            if not docs:
                raise ValueError("No valid documents loaded - check file format and content")
            # OUTPUT (agar docs empty hoti):
            #   ValueError: No valid documents loaded - check file format and content
            # (Yahan docs = 3 objects hai, toh yeh line skip hogi)

            chunks = self._split(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            # OUTPUT: chunks = [7 Document objects]  ← (upar _split() ka output dekho)

            fm = FaissManager(self.faiss_dir, self.model_loader)
            # OUTPUT: fm = <FaissManager index_dir='faiss_index/session_xxx/'>
            #   Internally:
            #     self._meta = {"rows": {}}  ← pehli dafa, koi data nahi
            #     self.emb   = <HuggingFaceEmbeddings model>

            texts = [c.page_content for c in chunks]
            # OUTPUT: texts = [
            #   "Muhammad Ali\nSoftware Eng...",   # chunk 1
            #   "...3 years Python\nSkills:...",   # chunk 2
            #   "Skills: LangChain, FAISS...",     # chunk 3
            #   "Projects:\n1. LLMOps...",         # chunk 4
            #   "...LLMOps RAG\n2. HVAC...",       # chunk 5
            #   "Education:\nBSCS FAST...",        # chunk 6
            #   "...FAST University 2023",         # chunk 7
            # ]  ← 7 plain strings

            metas = [c.metadata for c in chunks]
            # OUTPUT: metas = [
            #   {"source": "resume.pdf", "page": 0},  # chunk 1 ka metadata
            #   {"source": "resume.pdf", "page": 0},  # chunk 2 ka metadata
            #   {"source": "resume.pdf", "page": 0},  # chunk 3 ka metadata
            #   {"source": "resume.pdf", "page": 1},  # chunk 4 ka metadata
            #   {"source": "resume.pdf", "page": 1},  # chunk 5 ka metadata
            #   {"source": "resume.pdf", "page": 2},  # chunk 6 ka metadata
            #   {"source": "resume.pdf", "page": 2},  # chunk 7 ka metadata
            # ]

            vs = fm.load_or_create(texts=texts, metadatas=metas)
            # OUTPUT: vs = <FAISS vectorstore with 7 vectors>
            #   Pehli dafa:
            #     - 7 texts ke embeddings generate hue (1536-dim vectors)
            #     - FAISS index bana: faiss_index/session_xxx/index.faiss ✅
            #     - Mapping bani:     faiss_index/session_xxx/index.pkl   ✅

            added = fm.add_documents(chunks)
            # OUTPUT: added = 7
            #   7 naye chunks FAISS mein add hue (koi duplicate nahi tha)
            #   ingested_meta.json update hua:
            #   {"rows": {"resume.pdf::0":true, "resume.pdf::1":true, "resume.pdf::2":true, ...}}
            #
            #   AGAR SAME FILE DOBARA UPLOAD HOTI:
            #   OUTPUT: added = 0  ← sab fingerprints pehle se the, sab skip!

            log.info("FAISS index updated", new_chunks_added=added, index=str(self.faiss_dir))
            # OUTPUT (console log):
            #   INFO | FAISS index updated
            #     new_chunks_added = 7
            #     index = "faiss_index/session_20260424_225500_a3f9c1b2"

            search_kwargs = {"k": k}
            # OUTPUT: search_kwargs = {"k": 5}
            #   k=5 matlab: chatbot query par 5 sabse relevant chunks dhoondhega

            if search_type == "mmr":
                # search_type="mmr" → yeh block chalega

                search_kwargs["fetch_k"] = fetch_k
                search_kwargs["lambda_mult"] = lambda_mult
                # OUTPUT: search_kwargs = {"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
                #   fetch_k=20   : pehle 20 candidates nikalega
                #   lambda_mult=0.5 : results mein 50% relevance + 50% diversity

                log.info("Using MMR search strategy", k=k, fetch_k=fetch_k, lambda_mult=lambda_mult)
                # OUTPUT (console log):
                #   INFO | Using MMR search strategy
                #     k           = 5
                #     fetch_k     = 20
                #     lambda_mult = 0.5

            return vs.as_retriever(search_type=search_type, search_kwargs=search_kwargs)
            # OUTPUT: VectorStoreRetriever(
            #     search_type='mmr',
            #     search_kwargs={'k': 5, 'fetch_k': 20, 'lambda_mult': 0.5}
            # )
            #
            # Ab chatbot use karega:
            #   retriever.get_relevant_documents("What are his skills?")
            #   → [Document("Skills: LangChain, FAISS, Docker..."),
            #      Document("Projects: LLMOps RAG Pipeline..."),
            #      ... 5 chunks total]

        except Exception as e:
            log.error("Failed to build retriever", error=str(e))
            # OUTPUT (agar error aye):
            #   ERROR | Failed to build retriever
            #     error = "No valid documents loaded - check file format and content"

            raise DocumentPortalException("Failed to build retriever", e) from e
            # OUTPUT: DocumentPortalException: Failed to build retriever


# ==============================================================================
# CONSTANT
# ==============================================================================

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
# OUTPUT: {'.pdf', '.docx', '.txt'}
#   Sirf in 3 formats ki files accept hongi


# ==============================================================================
# CLASS 2: FaissManager
# ==============================================================================

class FaissManager:
    """FAISS vector database ka low-level driver — save, load, aur deduplicate."""

    def __init__(self, index_dir: Path, model_loader: Optional[ModelLoader] = None):

        self.index_dir = Path(index_dir)
        # OUTPUT: self.index_dir = PosixPath('faiss_index/session_20260424_225500_a3f9c1b2')

        self.index_dir.mkdir(parents=True, exist_ok=True)
        # OUTPUT: Folder ban gaya on disk ✅

        self.meta_path = self.index_dir / "ingested_meta.json"
        # OUTPUT: self.meta_path = PosixPath('faiss_index/session_xxx/ingested_meta.json')

        self._meta: Dict[str, Any] = {"rows": {}}
        # OUTPUT: self._meta = {"rows": {}}
        #   Pehli dafa: yeh empty dict hai

        if self.meta_path.exists():
            # Pehli dafa: file nahi hai → yeh block skip hoga
            # Doosri dafa: file hai → block chalega
            try:
                loaded = json.loads(self.meta_path.read_text(encoding="utf-8"))
                # OUTPUT (doosri dafa): loaded = {"rows": {"resume.pdf::0": true, ...}}

                self._meta = loaded or {"rows": {}}
                # OUTPUT: self._meta = {"rows": {"resume.pdf::0": true, ...}}
                #   'or {"rows": {}}' — agar file empty/null hoti toh default use hota

            except Exception:
                self._meta = {"rows": {}}
                # OUTPUT (corrupt JSON hone par): self._meta = {"rows": {}}  ← fresh start

        self.model_loader = model_loader or ModelLoader()
        # OUTPUT: self.model_loader = <ModelLoader object>
        #   (diya gaya tha ChatIngestor se, isliye naya nahi bana)

        self.emb = self.model_loader.load_embeddings()
        # OUTPUT: self.emb = <HuggingFaceEmbeddings model_name='all-MiniLM-L6-v2'>
        #   Yeh model text → numbers (vectors) mein convert karta hai

        self.vs: Optional[FAISS] = None
        # OUTPUT: self.vs = None
        #   Pehle None hai, load_or_create() se set hoga


    def _exists(self) -> bool:
        """Check karta hai ke FAISS index files disk par hain ya nahi."""

        return (
            (self.index_dir / "index.faiss").exists()
            and
            (self.index_dir / "index.pkl").exists()
        )
        # OUTPUT (pehli dafa — files nahi hain): False
        # OUTPUT (doosri dafa — files hain):     True
        #
        # Disk par check karta hai:
        #   faiss_index/session_xxx/index.faiss  →  exist? True/False
        #   faiss_index/session_xxx/index.pkl    →  exist? True/False
        #   Dono True hone chahiye → tabhi True return hoga


    @staticmethod
    def _fingerprint(text: str, md: Dict[str, Any]) -> str:
        """Har chunk ka ek unique ID (fingerprint) banata hai — duplicate check ke liye."""

        src = md.get("source") or md.get("file_path")
        # EXAMPLE 1 — PDF chunk:
        #   md = {"source": "resume.pdf", "page": 0}
        #   OUTPUT: src = "resume.pdf"
        #
        # EXAMPLE 2 — plain text (koi source nahi):
        #   md = {}
        #   OUTPUT: src = None

        rid = md.get("row_id")
        # EXAMPLE 1 (PDF): OUTPUT: rid = None  (PDFs mein row_id nahi hota)
        # EXAMPLE 3 (CSV): md = {"source": "data.csv", "row_id": 5}
        #                  OUTPUT: rid = 5

        if src is not None:
            row_part = "" if rid is None else str(rid)
            # EXAMPLE 1: row_part = ""   (page nahi liya kyunki row_id=None)
            # EXAMPLE 3: row_part = "5"  (CSV row number)

            return f"{src}::{row_part}"
            # EXAMPLE 1 OUTPUT: "resume.pdf::"
            # EXAMPLE 3 OUTPUT: "data.csv::5"

        return hashlib.sha256(text.encode("utf-8")).hexdigest()
        # EXAMPLE 2 OUTPUT: "b94f6f125c79e3a5ffaa826f584c010d17b00d1e4e71b6b7..."
        #   (64 character hex string — same text = same hash hamesha)


    def _save_meta(self):
        """In-memory metadata ko disk par JSON file mein save karta hai."""

        self.meta_path.write_text(
            json.dumps(self._meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # OUTPUT (disk par file ban gayi):
        # faiss_index/session_xxx/ingested_meta.json contents:
        # {
        #   "rows": {
        #     "resume.pdf::": true,
        #     "resume.pdf::": true,
        #     "resume.pdf::": true,
        #     "resume.pdf::": true,
        #     "resume.pdf::": true,
        #     "resume.pdf::": true,
        #     "resume.pdf::": true
        #   }
        # }
        # (koi return value nahi — sirf file likhta hai)


    def add_documents(self, docs: List[Document]) -> int:
        """FAISS mein documents add karta hai — duplicates automatically skip hote hain."""

        if self.vs is None:
            raise RuntimeError("FAISS vectorstore is not initialized. Call load_or_create() first.")
        # OUTPUT (agar load_or_create() na chali ho):
        #   RuntimeError: FAISS vectorstore is not initialized...
        # (Normal flow mein yeh error nahi aata)

        new_docs: List[Document] = []
        # OUTPUT: new_docs = []  ← shuru mein empty list

        for d in docs:
            # EXAMPLE: d = Document(page_content="Muhammad Ali...", metadata={"source":"resume.pdf"})

            key = self._fingerprint(d.page_content, d.metadata or {})
            # OUTPUT: key = "resume.pdf::"  ← is chunk ka unique ID

            if key in self._meta["rows"]:
                continue
                # PEHLI DAFA: key nahi hoga → yahan nahi rukenge
                # DOOSRI DAFA (same file dobara): key hoga → SKIP! continue

            self._meta["rows"][key] = True
            # OUTPUT: self._meta = {"rows": {"resume.pdf::": True, ...}}
            #   Yeh chunk mark ho gaya as "already indexed"

            new_docs.append(d)
            # OUTPUT: new_docs = [d]  ← chunk list mein aa gaya

        if new_docs:
            # PEHLI DAFA: new_docs = 7 chunks → yeh block chalega

            self.vs.add_documents(new_docs)
            # OUTPUT: FAISS mein 7 naye vectors add ho gaye
            #   Internally: text → embedding model → 1536-dim vector → FAISS index

            self.vs.save_local(str(self.index_dir))
            # OUTPUT: Disk par save ho gaya:
            #   faiss_index/session_xxx/index.faiss  ✅ (updated)
            #   faiss_index/session_xxx/index.pkl    ✅ (updated)

            self._save_meta()
            # OUTPUT: ingested_meta.json update ho gayi ✅

        return len(new_docs)
        # PEHLI DAFA OUTPUT: 7   ← 7 naye chunks add hue
        # DOOSRI DAFA OUTPUT: 0  ← sab duplicate the, kuch add nahi hua


    def load_or_create(
        self,
        texts: Optional[List[str]] = None,
        metadatas: Optional[List[dict]] = None,
    ) -> FAISS:
        """Existing FAISS index load karta hai ya nayi banata hai."""

        if self._exists():
            # PEHLI DAFA: False → yeh block skip
            # DOOSRI DAFA: True → yeh block chalega

            self.vs = FAISS.load_local(
                str(self.index_dir),
                embeddings=self.emb,
                allow_dangerous_deserialization=True,
            )
            # OUTPUT (doosri dafa): self.vs = <FAISS vectorstore loaded from disk>
            #   Yeh pehle se saved index.faiss + index.pkl se load hua

            return self.vs
            # OUTPUT: <FAISS vectorstore with N saved vectors>

        if not texts:
            raise DocumentPortalException(
                "No existing FAISS index found and no texts provided to create one.", None
            )
            # OUTPUT (agar texts=None aur index bhi nahi):
            #   DocumentPortalException: No existing FAISS index found...

        self.vs = FAISS.from_texts(texts=texts, embedding=self.emb, metadatas=metadatas or [])
        # INPUT: texts = ["Muhammad Ali...", "...Python Skills...", ... 7 strings]
        # OUTPUT: self.vs = <FAISS vectorstore with 7 new vectors>
        #   Internally har string ka vector bana:
        #   "Muhammad Ali..." → [0.023, -0.415, 0.871, ...]  (1536 numbers)
        #   "...Python skills" → [0.117, -0.203, 0.654, ...]
        #   ...7 vectors total FAISS mein store hue

        self.vs.save_local(str(self.index_dir))
        # OUTPUT: Disk par 2 files ban gayi:
        #   faiss_index/session_xxx/index.faiss  ✅
        #   faiss_index/session_xxx/index.pkl    ✅

        return self.vs
        # OUTPUT: <FAISS vectorstore with 7 vectors>
        #   Ab chatbot query dega aur yeh 5 sabse relevant chunks dhoondhega


# ==============================================================================
#
#   IS POORE CODE KA TOTAL MAQSAD (data_injection.py)
#   ===================================================
#
#   MASHLA (Problem):
#     AI/Chatbot seedha aapki PDF nahi padh sakta kyunki uski memory limited hai.
#     Ek 50-page document ek baar mein nahi dete.
#
#   HALL (Solution) — yeh file kya karti hai:
#
#     User         →  resume.pdf upload karta hai
#         ↓
#     [1] save_uploaded_files()
#         File ko disk par temporarily save karo
#         → "data/session_xxx/resume.pdf"
#         ↓
#     [2] load_documents()
#         PDF ka text extract karo (page by page)
#         → 3 Document objects (ek per page)
#         ↓
#     [3] _split()   ← RecursiveCharacterTextSplitter
#         Bade pages ko chhote tukron (chunks) mein todo
#         → 7 chunks (1000 chars each, 200 overlap)
#         ↓
#     [4] load_or_create()   ← FaissManager
#         Har chunk ka "meaning" numbers mein badlo (embedding)
#         → "Muhammad Ali Software Eng..." → [0.023, -0.415, 0.871, ...] (1536 numbers)
#         Phir FAISS database mein save karo (index.faiss + index.pkl)
#         ↓
#     [5] add_documents()   ← Deduplication magic!
#         Fingerprint check karo — same chunk dobara add mat karo
#         Pehli dafa: 7 chunks add   → added = 7
#         Dobara:     0 chunks add   → added = 0  (smart skip!)
#         ↓
#     [6] as_retriever()
#         Chatbot ke liye ek "Librarian" (Retriever) ready karo
#         Jo query aane par database se 5 sabse relevant chunks dhoondhega
#         → VectorStoreRetriever(search_type='mmr', k=5)
#         ↓
#     Chatbot      →  "What are his skills?"
#                  →  Retriever dhoondhega 5 chunks
#                  →  LLM un chunks se jawab banega
#                  →  "Muhammad Ali ke skills: LangChain, FAISS, Docker..."
#
#   DO MAIN CLASSES:
#     ChatIngestor  → Pipeline ka Director (upar se neeche tak coordination)
#     FaissManager  → Database Driver (store, load, deduplicate)
#
#   EK LINE MEIN:
#     "Yeh file aapki document ko AI ke liye ek searchable memory mein
#      convert karti hai — taake chatbot aapki apni files se sawal ka
#      jawab de sake."
#
# ==============================================================================
