import os
import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Iterable, List, Optional, Dict, Any

from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from multi_doc_chat.utils.model_loader import ModelLoader
from multi_doc_chat.logger.customlogger import CustomLogger
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.utils.document_ops import load_documents
from multi_doc_chat.utils.file_io import save_uploaded_files
# -------------------------------------------------------------
# 1. SETUP: Logger
# Aapke project ka standard CustomLogger yahan initialize ho gaya hai.
# -------------------------------------------------------------
logger_setup = CustomLogger()
log = logger_setup.get_logger(__file__)

# -------------------------------------------------------------
# MOCK / TEMPORARY FUNCTIONS 
# (jab tak aap "file_io.py" aur "document_ops.py" nahi banate us waqt tak 
#  application error avoid karne ke liye yeh use hongay)
# -------------------------------------------------------------
def save_uploaded_files(uploaded_files: Iterable, temp_dir: Path) -> List[Path]:
    log.info(f"Uploading files saved in: {temp_dir}")
    return [temp_dir / "sample_doc.txt"]

def load_documents(paths: List[Path]) -> List[Document]:
    log.info("Loading texts from documents...")
    return [Document(page_content="LLMOps project bilkul theek kaam kar raha hai. AI automation faiday mand hai.", metadata={"source": "sample_doc.txt"})]

def generate_session_id() -> str:
    """Session ID with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"session_{timestamp}_{unique_id}"

# =============================================================
# 2. FAISS VECTOR DB MANAGER
# =============================================================
class FaissManager:
    """
    FaissManager ka maqsad Vector Database ko create aur update karna hai bina duplicates bheje.
    """
    def __init__(self, index_dir: Path, model_loader: Optional[ModelLoader] = None):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Yeh 'ingested_meta.json' file list rakhti hai kon konsi files pehle add hochuki hain
        self.meta_path = self.index_dir / "ingested_meta.json"
        self._meta: Dict[str, Any] = {"rows": {}} 

        if self.meta_path.exists():
            try:
                self._meta = json.loads(self.meta_path.read_text(encoding="utf-8")) or {"rows": {}} 
            except Exception:
                self._meta = {"rows": {}}

        self.model_loader = model_loader or ModelLoader()
        
        # Hum Embedding Model (e.g Google) ModelLoader se le rahe hain
        self.emb = self.model_loader.get_embedding_model()
        self.vs: Optional[FAISS] = None

    def _exists(self) -> bool:
        return (self.index_dir / "index.faiss").exists() and (self.index_dir / "index.pkl").exists()

    @staticmethod
    def _fingerprint(text: str, md: Dict[str, Any]) -> str:
        # Har file/chunk ka ek unique code banata hai. Agar file ka text change hua tou naya code banega!
        src = md.get("source") or md.get("file_path")
        rid = md.get("row_id")
        if src is not None:
            return f"{src}::{'' if rid is None else rid}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _save_meta(self):
        self.meta_path.write_text(json.dumps(self._meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_documents(self, docs: List[Document]):
        if self.vs is None:
            raise RuntimeError("Call load_or_create() pehle call karein.")

        new_docs: List[Document] = []
        for d in docs:
            # Check karte hain ke kya yeh file already Vector database ka hissa hai?
            key = self._fingerprint(d.page_content, d.metadata or {})
            if key in self._meta["rows"]:
                continue
            self._meta["rows"][key] = True
            new_docs.append(d)

        # Sirf NAYI files FAISS vector mein daali jayengi
        if new_docs:
            self.vs.add_documents(new_docs)
            self.vs.save_local(str(self.index_dir))
            self._save_meta()
        return len(new_docs)

    def load_or_create(self, texts: Optional[List[str]] = None, metadatas: Optional[List[dict]] = None):
        if self._exists():
            log.info("Purana FAISS index mil gaya.")
            self.vs = FAISS.load_local(
                str(self.index_dir),
                embeddings=self.emb,
                allow_dangerous_deserialization=True,
            )
            return self.vs

        if not texts:
            raise DocumentPortalException("FAISS initialize krne ko Data nahi mila.")
            
        log.info("Naya FAISS index Create kia ja raha hai.")
        self.vs = FAISS.from_texts(texts=texts, embedding=self.emb, metadatas=metadatas or [])
        self.vs.save_local(str(self.index_dir))
        return self.vs

# =============================================================
# 3. CHAT INGESTOR (Main Controller)
# =============================================================
class ChatIngestor:
    def __init__( self,
        temp_base: str = "data",
        faiss_base: str = "faiss_index",
        use_session_dirs: bool = True,
        session_id: Optional[str] = None,
    ):
        try:
            self.model_loader = ModelLoader()
            self.use_session = use_session_dirs
            self.session_id = session_id or generate_session_id()

            # Folders verify karte hain
            self.temp_base = Path(temp_base)
            self.temp_base.mkdir(parents=True, exist_ok=True)
            self.faiss_base = Path(faiss_base)
            self.faiss_base.mkdir(parents=True, exist_ok=True)

            self.temp_dir = self._resolve_dir(self.temp_base)
            self.faiss_dir = self._resolve_dir(self.faiss_base)

            log.info("ChatIngestor Setup Mukammal hogaya!")
        except Exception as e:
            log.error(f"ChatIngestor error: {e}")
            raise DocumentPortalException("Initialization error in ChatIngestor", e) from e


    def _resolve_dir(self, base: Path):
        """User Session based folders banata hai."""
        if self.use_session:
            d = base / self.session_id 
            d.mkdir(parents=True, exist_ok=True) 
            return d
        return base 

    def _split(self, docs: List[Document], chunk_size=1000, chunk_overlap=200) -> List[Document]:
        """LangChain ka function jo bari text file ko small 1000 alphabets pieces mein tord dega."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_documents(docs)
        log.info(f"Done: {len(chunks)} Chunks mein split ho gaye.")
        return chunks

    def built_retriever( self,
        uploaded_files: Iterable,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        k: int = 5,
        search_type: str = "mmr",
        fetch_k: int = 20,
        lambda_mult: float = 0.5):
        
        try:
            # 1. Jo User PDF upload kare ga us ko load karwate hain
            paths = save_uploaded_files(uploaded_files, self.temp_dir)
            docs = load_documents(paths)
            if not docs:
                raise ValueError("No valid documents loaded")

            # 2. Text Chunks me Convert karte hain (Maslan: Kitaab ke panno ko lines me badalna)
            chunks = self._split(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

            # 3. Vector Database Engine Call
            fm = FaissManager(self.faiss_dir, self.model_loader)
            texts = [c.page_content for c in chunks]
            metas = [c.metadata for c in chunks]

            # 4. Embeddings Calculate hoti hain AI Model k database mein
            try:
                vs = fm.load_or_create(texts=texts, metadatas=metas)
            except Exception:
                vs = fm.load_or_create(texts=texts, metadatas=metas)

            added = fm.add_documents(chunks)
            log.info(f"Data Base mein {added} New Pieces enter hochukay hain.")

            # Search Algorithms mmr vs similarity
            search_kwargs = {"k": k}
            if search_type == "mmr":
                search_kwargs["fetch_k"] = fetch_k
                search_kwargs["lambda_mult"] = lambda_mult
            
            # Akhir mein ek 'Retriever' Engine wapas bhejta hai jo Chatting k doraan data utha kr LLM(Groq/Gemini) ko dega.
            return vs.as_retriever(search_type=search_type, search_kwargs=search_kwargs)

        except Exception as e:
            raise DocumentPortalException("Retriever nahi ban saka", e) from e


# ==================================================
# PRACTICAL TESTING (Ta k Aap Action me dekh sakin)
# Ye command run karen: python default_ingestion.py
# ==================================================
if __name__ == "__main__":
    print("---------------------------------------------")
    print("🚀 Practical Action Phase: User ne 'book.pdf' upload kar di.")
    
    # Ingestion Start (System Session Banayega)
    ingestor = ChatIngestor(use_session_dirs=True)
    
    # Data load + chunk + Embeddings pass ho rahi hai
    dummy_files = ["fake_uploaded_book.pdf"]
    retriever_engine = ingestor.built_retriever(dummy_files)
    
    print("\n✅ FAISS VECTOR DB NE APKA RETRIEVER TAYYAR KAR DIYA HAI!")
    print(retriever_engine)
    print("---------------------------------------------")
