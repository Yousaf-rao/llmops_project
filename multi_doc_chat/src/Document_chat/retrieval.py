from __future__ import annotations
# Yeh line Python 3.7+ mein type hints ko strings ki tarah treat karne deti hai
# taake circular imports ya forward references ka masla na aaye

import sys
# sys.exc_info() use hota hai DocumentPortalException ke liye
# Lekin is file mein hum seedha 'e' (exception object) pass karenge — sahi tarika

import os
# INPUT : Standard library
# OUTPUT: os.path.isdir() jaise functions milte hain — folder exist check ke liye

from operator import itemgetter
# INPUT : Standard library
# OUTPUT: itemgetter("key") → dictionary se kisi key ki value nikalne ka shortcut
#         MISAAL: itemgetter("input")({"input": "Hello"}) → "Hello"
#         LCEL chain mein payload dictionary se values nikalne ke liye use hota hai

from typing import List, Optional, Dict, Any
# Type hints ke liye:
# List[X]     = Python list
# Optional[X] = Ya X hoga ya None
# Dict[K,V]   = Dictionary
# Any         = Koi bhi type

from langchain_core.messages import BaseMessage
# INPUT : LangChain Core library
# OUTPUT: Chat history ke messages ka base class
#         HumanMessage, AIMessage — dono is class se inherit karte hain
#         MISAAL: [HumanMessage(content="Hi"), AIMessage(content="Hello!")]

from langchain_core.output_parsers import StrOutputParser
# INPUT : LangChain Core library
# OUTPUT: LLM ka output (jo AIMessage hota hai) → plain string mein convert karta hai
#         MISAAL: AIMessage(content="Paris hai") → "Paris hai"

from langchain_core.prompts import ChatPromptTemplate
# INPUT : LangChain Core library
# OUTPUT: Prompt template class — variables ke saath dynamic prompts banata hai
#         MISAAL: "Answer: {context}\nQuestion: {input}" → fill ho kar LLM ko jata hai

from langchain_community.vectorstores import FAISS
# INPUT : LangChain Community library
# OUTPUT: FAISS vectorstore class — disk se load karne aur similarity search ke liye

from multi_doc_chat.utils.model_loader import ModelLoader
# INPUT : Hamare project ka model factory
# OUTPUT: ModelLoader class — LLM aur Embedding model load karne ke liye
#         .get_llm()             → Groq ya Gemini LLM object
#         .get_embedding_model() → Google Embedding model

from multi_doc_chat.exception.custom_exception import DocumentPortalException
# INPUT : Hamare project ki custom exception class
# OUTPUT: Error mein file naam + line number + traceback automatically milta hai

from multi_doc_chat.logger.customlogger import CustomLogger
# INPUT : Hamare project ka JSON logger
# OUTPUT: log.info() / log.error() → structured JSON logs

from multi_doc_chat.prompts.prompt_library import PROMPT_REGISTRY
# INPUT : Hamare project ka prompt dictionary
# OUTPUT: PROMPT_REGISTRY["contextualize_question"] → ChatPromptTemplate object
#         PROMPT_REGISTRY["context_qa"]             → ChatPromptTemplate object

from multi_doc_chat.model.models import PromptType, ChatAnswer
# INPUT : Hamare project ke Pydantic models
# OUTPUT: PromptType → Enum (CONTEXTUALIZE_QUESTION, CONTEXT_QA)
#         ChatAnswer → Pydantic model jo answer string validate karta hai

from pydantic import ValidationError
# INPUT : Pydantic library
# OUTPUT: Agar ChatAnswer validation fail ho toh yeh exception uthti hai


# ─────────────────────────────────────────────────────────────────────────────
#  MODULE-LEVEL LOGGER SETUP
# ─────────────────────────────────────────────────────────────────────────────
_logger_setup = CustomLogger()
log = _logger_setup.get_logger(__name__)
# log.info("...")  → {"timestamp": "...", "level": "info", "event": "..."}


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN CLASS: CONVERSATIONAL RAG (Retrieval Augmented Generation)
# ─────────────────────────────────────────────────────────────────────────────
class ConversationalRAG:
    """
    LCEL-based Conversational RAG — chat history ke saath document search + answer.

    RAG ka matlab:
        R = Retrieval  → FAISS se relevant document chunks dhoondho
        A = Augmented  → woh chunks LLM ko context ke roop mein do
        G = Generation → LLM jawab generate karta hai

    Conversation ka matlab:
        Sirf aakhri question nahi — poori chat history use hoti hai.
        Pehle question ko history ke saath rewrite kiya jata hai
        taake context-aware search ho sake.

    Pipeline (3 qadam):
        1. Question Rewrite  → chat history + user question → better question
        2. FAISS Retrieval   → better question → relevant document chunks
        3. LLM Answer        → chunks + original question → final answer

    USE KAISE KARO (MISAAL):
        rag = ConversationalRAG(session_id="user_abc")
        rag.load_retriever_from_faiss(index_path="faiss_index/user_abc")
        answer = rag.invoke("Document mein kya likha hai?", chat_history=[])
    """

    def __init__(self, session_id: Optional[str], retriever=None):
        """
        ConversationalRAG ka object banao.

        Parameters
        ----------
        session_id : Optional[str]
            User session ka unique identifier — logs mein track karne ke liye.
            MISAAL: "session_20260504_221500_a3f7c1b2"

        retriever : optional
            Agar pehle se tayyar retriever ho toh seedha yahan de sakte hain.
            Aksar None hota hai — baad mein load_retriever_from_faiss() se set hota hai.
        """
        try:
            self.session_id = session_id
            # User ka unique session ID — sab logs mein track hoga

            # ── LLM LOAD KARO ─────────────────────────────────────────────────
            self.llm = self._load_llm()
            # INPUT : (koi nahi — ModelLoader khud config.yaml parh lega)
            # OUTPUT: self.llm = Groq ya Gemini LLM object
            #         MISAAL: ChatGroq(model="llama3-8b-8192") ya ChatGoogleGenerativeAI(model="gemini-2.0-flash")

            # ── PROMPTS LOAD KARO ──────────────────────────────────────────────
            self.contextualize_prompt: ChatPromptTemplate = PROMPT_REGISTRY[
                PromptType.CONTEXTUALIZE_QUESTION.value
            ]
            # INPUT : PROMPT_REGISTRY = dictionary of all prompts
            #         PromptType.CONTEXTUALIZE_QUESTION.value = "contextualize_question" (string key)
            # OUTPUT: self.contextualize_prompt = ChatPromptTemplate
            #         KAAM: Chat history + current question → standalone question banata hai
            #         MISAAL prompt: "Given chat history: {chat_history}\nRewrite: {input}"

            self.qa_prompt: ChatPromptTemplate = PROMPT_REGISTRY[
                PromptType.CONTEXT_QA.value
            ]
            # INPUT : PromptType.CONTEXT_QA.value = "context_qa" (string key)
            # OUTPUT: self.qa_prompt = ChatPromptTemplate
            #         KAAM: Context + question → final answer
            #         MISAAL prompt: "Context: {context}\nQuestion: {input}\nAnswer:"

            # ── RETRIEVER (LAZY INITIALIZATION) ───────────────────────────────
            self.retriever = retriever
            # Aksar None hota hai — baad mein load_retriever_from_faiss() set karega

            self.chain = None
            # LCEL chain — jab tak retriever set na ho, chain bhi None rahega

            # ── AGAR RETRIEVER PEHLE SE DIYA HAI TO CHAIN BANA DO ─────────────
            if self.retriever is not None:
                self._build_lcel_chain()
            # INPUT : retriever = already built retriever object
            # OUTPUT: self.chain = complete LCEL pipeline (rewrite → retrieve → answer)

            log.info("ConversationalRAG initialized", session_id=self.session_id)

        except Exception as e:
            log.error("Failed to initialize ConversationalRAG", error=str(e))
            raise DocumentPortalException(
                "Initialization error in ConversationalRAG", error_details=e
            ) from e

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC METHOD 1: FAISS SE RETRIEVER LOAD KARO
    # ─────────────────────────────────────────────────────────────────────────
    def load_retriever_from_faiss(
        self,
        index_path: str,
        k: int = 5,
        index_name: str = "index",
        search_type: str = "mmr",
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        search_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """
        Disk par saved FAISS index se retriever load karo aur LCEL chain banao.

        Parameters
        ----------
        index_path : str
            FAISS index folder ka path.
            MISAAL: "faiss_index/session_20260504_221500_a3f7c1b2"

        k : int
            Retrieval mein kitne document chunks wapas chahiye.
            MISAAL: k=5 → har query par 5 sabse relevant chunks milenge

        index_name : str
            FAISS files ka prefix naam.
            MISAAL: "index" → "index.faiss" + "index.pkl" files dhoondega

        search_type : str
            Search algorithm ka naam.
            "similarity" → sabse close vectors return karo
            "mmr"        → Maximum Marginal Relevance — diverse results (default)

        fetch_k : int  (sirf MMR ke liye)
            MMR ke liye pehle itne docs fetch karo, phir re-rank karo.
            MISAAL: fetch_k=20 → 20 docs laao, phir 5 best + diverse chunno

        lambda_mult : float  (sirf MMR ke liye)
            0.0 = maximum diversity (alag alag results)
            1.0 = maximum relevance (similar results)
            0.5 = balanced (default)

        search_kwargs : dict, optional
            Custom search parameters — agar diya toh baaki parameters override honge.

        Returns
        -------
        retriever
            LangChain retriever object — LCEL chain mein use hoga.
        """
        try:
            # ── STEP 1: FOLDER EXIST CHECK ────────────────────────────────────
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"FAISS index directory not found: {index_path}")
            # INPUT : index_path = "faiss_index/session_abc"
            # OUTPUT: Agar folder nahi → FileNotFoundError raise hogi
            #         Agar hai → aage chalte hain

            # ── STEP 2: EMBEDDING MODEL LOAD KARO ────────────────────────────
            embeddings = ModelLoader().get_embedding_model()
            # INPUT : (config.yaml se embedding model settings aati hain)
            # OUTPUT: embeddings = GoogleGenerativeAIEmbeddings object
            #         KAAM: Text → numbers (vectors) mein convert karta hai
            #         ZAROORAT: FAISS ko text query numbers mein convert karni hoti hai search ke liye

            # ── STEP 3: FAISS INDEX DISK SE LOAD KARO ────────────────────────
            vectorstore = FAISS.load_local(
                index_path,
                embeddings,
                index_name=index_name,
                allow_dangerous_deserialization=True,
            )
            # INPUT : index_path = "faiss_index/session_abc"
            #         embeddings = GoogleGenerativeAIEmbeddings
            #         index_name = "index" → "index.faiss" + "index.pkl" files load hongi
            # OUTPUT: vectorstore = FAISS object (memory mein loaded vector database)
            #         allow_dangerous_deserialization=True → zaruri hai pickle files ke liye
            #         MISAAL: 500 document chunks ke 500 vectors memory mein load ho gaye

            # ── STEP 4: SEARCH PARAMETERS TAYYAR KARO ────────────────────────
            if search_kwargs is None:
                search_kwargs = {"k": k}
                if search_type == "mmr":
                    search_kwargs["fetch_k"] = fetch_k
                    search_kwargs["lambda_mult"] = lambda_mult
            # INPUT : search_type="mmr", k=5, fetch_k=20, lambda_mult=0.5
            # OUTPUT: search_kwargs = {"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
            #         MISAAL (similarity): search_kwargs = {"k": 5}
            #         MISAAL (mmr):        search_kwargs = {"k": 5, "fetch_k": 20, "lambda_mult": 0.5}

            # ── STEP 5: RETRIEVER BANAO ───────────────────────────────────────
            self.retriever = vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs,
            )
            # INPUT : vectorstore = FAISS in-memory DB
            #         search_type = "mmr"
            #         search_kwargs = {"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
            # OUTPUT: self.retriever = LangChain Retriever object
            #         Jab retriever.invoke("query") chalega:
            #           1. "query" → embedding → [0.023, -0.415, ...] (vector)
            #           2. FAISS mein closest 20 vectors dhoondho
            #           3. MMR se best 5 diverse chunks chunno
            #           4. [Document(...), Document(...), ...] wapas karo

            # ── STEP 6: LCEL CHAIN BANAO ──────────────────────────────────────
            self._build_lcel_chain()
            # INPUT : self.retriever (abhi set hua)
            # OUTPUT: self.chain = complete pipeline (3 qadam)

            log.info(
                "FAISS retriever loaded successfully",
                index_path=index_path,
                index_name=index_name,
                search_type=search_type,
                k=k,
                session_id=self.session_id,
            )
            return self.retriever

        except Exception as e:
            log.error("Failed to load retriever from FAISS", error=str(e))
            raise DocumentPortalException(
                "Loading error in ConversationalRAG", error_details=e
            ) from e

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC METHOD 2: USER QUESTION KA JAWAB DO
    # ─────────────────────────────────────────────────────────────────────────
    def invoke(
        self,
        user_input: str,
        chat_history: Optional[List[BaseMessage]] = None,
    ) -> str:
        """
        User ka question le kar LCEL pipeline chalao aur jawab string return karo.

        Parameters
        ----------
        user_input : str
            User ka sawal.
            MISAAL: "Document mein salary kitni likhi hai?"

        chat_history : List[BaseMessage], optional
            Pichli conversation ki history.
            MISAAL: [HumanMessage(content="Hi"), AIMessage(content="Hello!")]
            Khali list = pehla sawaal (koi history nahi)

        Returns
        -------
        str
            LLM ka jawab — plain string.
            MISAAL: "Document ke mutabiq salary 50,000 rupay hai."
        """
        try:
            # ── CHAIN CHECK ───────────────────────────────────────────────────
            if self.chain is None:
                raise DocumentPortalException(
                    "RAG chain not initialized. Call load_retriever_from_faiss() before invoke().",
                    error_details=None,
                )
            # Chain None hai matlab load_retriever_from_faiss() abhi nahi chala
            # Pehle woh call karo, phir invoke() chalao

            # ── HISTORY DEFAULT ────────────────────────────────────────────────
            chat_history = chat_history or []
            # INPUT : chat_history = None
            # OUTPUT: chat_history = []  (None ki jagah khali list)

            # ── PIPELINE CHALAO ────────────────────────────────────────────────
            payload = {"input": user_input, "chat_history": chat_history}
            answer = self.chain.invoke(payload)
            # INPUT : payload = {"input": "Salary kitni hai?", "chat_history": [...]}
            # OUTPUT: answer = "50,000 rupay hai." (plain string — StrOutputParser ne convert kiya)
            #
            # Andar 3 qadam hotay hain (LCEL chain):
            #   QADAM 1 — Question Rewrite:
            #     "Salary kitni hai?" + history → "Document mein salary kitni likhi hai?"
            #   QADAM 2 — FAISS Retrieval:
            #     "Document mein salary..." → [Doc(chunk1), Doc(chunk2), Doc(chunk3)]
            #   QADAM 3 — LLM Answer:
            #     chunks + question → "50,000 rupay hai."

            # ── EMPTY ANSWER CHECK ─────────────────────────────────────────────
            if not answer:
                log.warning("No answer generated", user_input=user_input, session_id=self.session_id)
                return "no answer generated."
            # LLM ne khali string di → fallback message return karo

            # ── PYDANTIC VALIDATION ────────────────────────────────────────────
            try:
                validated = ChatAnswer(answer=str(answer))
                answer = validated.answer
            except ValidationError as ve:
                log.error("Invalid chat answer", error=str(ve))
                raise DocumentPortalException("Invalid chat answer", error_details=ve) from ve
            # INPUT : answer = "50,000 rupay hai." (raw string)
            # OUTPUT: validated.answer = "50,000 rupay hai." (Pydantic ne check kiya)
            #         ChatAnswer model ensure karta hai:
            #           - answer string hai
            #           - empty nahi hai
            #           - length limit ke andar hai

            log.info(
                "Chain invoked successfully",
                session_id=self.session_id,
                user_input=user_input,
                answer_preview=str(answer)[:150],
            )
            return answer

        except Exception as e:
            log.error("Failed to invoke ConversationalRAG", error=str(e))
            raise DocumentPortalException(
                "Invocation error in ConversationalRAG", error_details=e
            ) from e

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE METHOD 1: LLM LOAD KARO
    # ─────────────────────────────────────────────────────────────────────────
    def _load_llm(self):
        """ModelLoader se LLM load karo — config.yaml mein jo provider set hai."""
        try:
            llm = ModelLoader().get_llm()
            # INPUT : (config.yaml se provider, model_name, temperature, max_tokens)
            # OUTPUT: llm = ChatGroq ya ChatGoogleGenerativeAI object
            #         MISAAL: ChatGroq(model="llama3-8b-8192", temperature=0)

            if not llm:
                raise ValueError("LLM could not be loaded")

            log.info("LLM loaded successfully", session_id=self.session_id)
            return llm

        except Exception as e:
            log.error("Failed to load LLM", error=str(e))
            raise DocumentPortalException(
                "LLM loading error in ConversationalRAG", error_details=e
            ) from e

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE METHOD 2: DOCUMENTS FORMAT KARO (STATIC)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _format_docs(docs) -> str:
        """
        LangChain Document objects ki list → ek string mein join karo.

        INPUT  → [Document(page_content="Para 1..."), Document(page_content="Para 2...")]
        OUTPUT → "Para 1...\n\nPara 2..."  (double newline se alag)

        LLM ko context string chahiye hoti hai, Document objects nahi.
        """
        return "\n\n".join(getattr(d, "page_content", str(d)) for d in docs)
        # getattr(d, "page_content", str(d)):
        #   → agar d mein page_content attribute hai → use karo
        #   → nahi hai → str(d) se fallback

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE METHOD 3: LCEL CHAIN BANAO (3-STEP PIPELINE)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_lcel_chain(self):
        """
        LCEL (LangChain Expression Language) ki 3-step pipeline build karo.

        LCEL mein "|" (pipe) ka matlab hai:
            output of A → input of B
            A | B | C = A ka output B mein, B ka output C mein

        Poori Pipeline:
        ┌─────────────────────────────────────────────────────────────┐
        │  STEP 1: QUESTION REWRITER                                  │
        │  {input, chat_history} → contextualize_prompt → LLM → str  │
        │  "Salary?" + history → "Document mein salary kitni hai?"    │
        ├─────────────────────────────────────────────────────────────┤
        │  STEP 2: RETRIEVER                                          │
        │  rewritten_question → FAISS → [Doc1, Doc2, Doc3]           │
        │  "Document mein salary..." → relevant chunks dhoondho       │
        ├─────────────────────────────────────────────────────────────┤
        │  STEP 3: ANSWER GENERATOR                                   │
        │  {context, input, chat_history} → qa_prompt → LLM → str    │
        │  chunks + question → "50,000 rupay hai."                    │
        └─────────────────────────────────────────────────────────────┘
        """
        try:
            if self.retriever is None:
                raise DocumentPortalException(
                    "No retriever set before building chain", error_details=None
                )

            # ── STEP 1: QUESTION REWRITER BANAO ──────────────────────────────
            question_rewriter = (
                {
                    "input": itemgetter("input"),
                    "chat_history": itemgetter("chat_history"),
                }
                | self.contextualize_prompt
                | self.llm
                | StrOutputParser()
            )
            # INPUT : {"input": "Salary?", "chat_history": [HumanMsg, AIMsg]}
            # OUTPUT: "Document mein mentioned salary kitni hai?"
            #
            # Kaise kaam karta hai:
            #   itemgetter("input")        → payload se "input" key ki value le
            #   itemgetter("chat_history") → payload se "chat_history" ki value le
            #   | contextualize_prompt     → template mein values fill karo
            #   | self.llm                 → LLM se rewritten question lo
            #   | StrOutputParser()        → AIMessage → plain string

            # ── STEP 2: RETRIEVER CHAIN BANAO ─────────────────────────────────
            retrieve_docs = question_rewriter | self.retriever | self._format_docs
            # INPUT : rewritten question string = "Document mein salary kitni hai?"
            # OUTPUT: "Para 1 text...\n\nPara 2 text...\n\nPara 3 text..."
            #
            # Kaise kaam karta hai:
            #   question_rewriter   → rewritten question string
            #   | self.retriever    → FAISS se relevant [Document, Document, ...] lo
            #   | self._format_docs → Documents → single context string

            # ── STEP 3: FINAL ANSWER CHAIN BANAO ──────────────────────────────
            self.chain = (
                {
                    "context": retrieve_docs,
                    "input": itemgetter("input"),
                    "chat_history": itemgetter("chat_history"),
                }
                | self.qa_prompt
                | self.llm
                | StrOutputParser()
            )
            # INPUT : {
            #   "context": "Para 1...\n\nPara 2...",   (retrieve_docs se)
            #   "input": "Salary?",                     (original question — rewrite nahi)
            #   "chat_history": [...]                   (poori history)
            # }
            # OUTPUT: "50,000 rupay hai." (plain string)
            #
            # Kaise kaam karta hai:
            #   retrieve_docs         → context string tayyar karo (Steps 1+2)
            #   itemgetter("input")   → original user question (rewritten nahi)
            #   itemgetter("history") → chat history
            #   | self.qa_prompt      → sab template mein fill karo
            #   | self.llm            → LLM se final answer lo
            #   | StrOutputParser()   → AIMessage → plain string

            log.info("LCEL graph built successfully", session_id=self.session_id)

        except Exception as e:
            log.error("Failed to build LCEL chain", error=str(e), session_id=self.session_id)
            raise DocumentPortalException(
                "Failed to build LCEL chain", error_details=e
            ) from e


"""
=============================================================================
🎯 IS FILE (retrieval.py) KA MAQSAD (DETAILED OBJECTIVE)
=============================================================================

Yeh file LLMOps pipeline ka AAKHRI AUR SABSE IMPORTANT hissa hai.
Pehle data_ingestion.py ne documents ko FAISS mein store kiya —
ab yeh file user ke sawal ka jawab deti hai.

───────────────────────────────────────────────────────────────────────────────
🔄 PIPELINE MEIN IS FILE KA ROLE
───────────────────────────────────────────────────────────────────────────────

  file_io.py          → Upload → Disk par Save
  document_ops.py     → Disk → LangChain Documents
  data_ingestion.py   → Documents → Chunks → FAISS Vector DB
  retrieval.py        ← YEH FILE YAHAN HAI
                        FAISS → Search → LLM → Answer

───────────────────────────────────────────────────────────────────────────────
🧠 3-STEP LCEL PIPELINE (ANDAR KYA HOTA HAI)
───────────────────────────────────────────────────────────────────────────────

  User: "Salary?"  + Chat History: ["Hi", "Hello!"]
         │
         ▼
  STEP 1 — Question Rewrite (contextualize_prompt + LLM)
         "Salary?" + history → "Document mein mentioned salary kitni hai?"
         │
         ▼
  STEP 2 — FAISS Retrieval (retriever)
         "Document mein salary..." → [Doc(chunk1), Doc(chunk2), Doc(chunk3)]
         → format_docs() → "Chunk1 text\n\nChunk2 text\n\nChunk3 text"
         │
         ▼
  STEP 3 — LLM Answer (qa_prompt + LLM)
         context + question + history → "50,000 rupay hai."
         │
         ▼
  User ko jawab milta hai ✅

───────────────────────────────────────────────────────────────────────────────
✅ IS FILE KE FAYDE
───────────────────────────────────────────────────────────────────────────────

1. CONVERSATIONAL MEMORY:
   Sirf current question nahi — chat history bhi consider hoti hai.
   "Is mein kya difference hai?" → history ke bina senseless
   → history ke saath: "Model A aur B mein kya difference hai?"

2. MMR SEARCH (Maximum Marginal Relevance):
   Sirf closest results nahi — diverse aur relevant results.
   fetch_k=20 mein se best + alag 5 chunks chunna.

3. LAZY INITIALIZATION:
   Retriever pehle load karne ki zaroorat nahi — baad mein bhi set kar sakte ho.
   self.chain = None → jab retriever set ho → chain build ho.

4. PYDANTIC VALIDATION:
   LLM ka jawab ChatAnswer model se validate hota hai — empty ya invalid
   answers automatically reject ho jate hain.

5. PROJECT PATTERNS:
   - CustomLogger (GLOBAL_LOGGER nahi)
   - DocumentPortalException(msg, error_details=e) — sahi signature
   - get_llm() / get_embedding_model() — model_loader.py ke actual methods

=============================================================================
"""
