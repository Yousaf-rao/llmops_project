<h1 align="center">
  <br>
  <img src="https://raw.githubusercontent.com/Yousaf-rao/llmops_project/main/static/logo.png" alt="LLMOps Project" width="150" onerror="this.src='https://cdn-icons-png.flaticon.com/512/8636/8636841.png'">
  <br>
  🤖 Multi-Document Chat (LLMOps Pipeline)
  <br>
</h1>

<p align="center">
  <strong>An advanced Retrieval-Augmented Generation (RAG) conversational pipeline for querying multiple documents seamlessly.</strong>
</p>

<p align="center">
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  </a>
  <a href="https://langchain.com/">
    <img src="https://img.shields.io/badge/LangChain-Integration-green.svg" alt="LangChain">
  </a>
  <a href="https://faiss.ai/">
    <img src="https://img.shields.io/badge/VectorDB-FAISS-red.svg" alt="FAISS">
  </a>
  <a href="https://groq.com/">
    <img src="https://img.shields.io/badge/LLM-Groq%20%7C%20Gemini-orange.svg" alt="Groq & Gemini">
  </a>
</p>

---

## 🌟 Overview

The **Multi-Document Chat** project is an end-to-end LLMOps pipeline designed to ingest multiple file formats (PDF, DOCX, TXT), convert them into vector embeddings, and allow users to chat with their documents using state-of-the-art Large Language Models (LLMs) like **Groq (LLaMA/Mixtral)** and **Google Gemini**.

It implements an **LCEL-based (LangChain Expression Language) Conversational RAG** that maintains chat history, rewrites context-aware questions, and retrieves answers with high accuracy using FAISS with Maximum Marginal Relevance (MMR) search.

## 🚀 Key Features

*   📑 **Multi-Format Ingestion:** Seamlessly process PDF, DOCX, and TXT files.
*   🧠 **Smart RAG Pipeline:** Context-aware question rewriting and history tracking.
*   ⚡ **Fast Vector Search:** Uses FAISS for lightning-fast similarity and MMR search.
*   🔄 **Dynamic LLM Switching:** Easily switch between `groq` and `google` models via config.
*   🛡️ **Custom Exception Handling:** Highly trackable `DocumentPortalException` for exact debugging.
*   📝 **Structured JSON Logging:** Implements structlog for clean, auditable logs.
*   🔍 **Duplicate Prevention:** Fingerprinting logic ensures chunks are not ingested multiple times.

## 🗂️ Project Architecture

```text
LLMOPS_SERIES/
├── .env                          # API Keys (GROQ_API_KEY, GOOGLE_API_KEY)
├── multi_doc_chat/
│   ├── config/
│   │   └── config.yaml           # Model settings, tokens, chunk sizes
│   ├── document_ingestion/
│   │   ├── data_ingestion.py     # Main ingestion controller & FAISS manager
│   │   └── retrieval.py          # LCEL RAG Chain & LLM interaction
│   ├── exception/
│   │   └── custom_exception.py   # Advanced error tracking (File + Line Number)
│   ├── logger/
│   │   └── customlogger.py       # JSON Log generator
│   └── utils/
│       ├── config_loader.py      # Safely loads config.yaml
│       ├── model_loader.py       # Validates keys & loads Gemini/Groq + Embeddings
│       ├── file_io.py            # Safely saves user uploaded files to disk
│       └── document_ops.py       # Converts saved files to LangChain Documents
├── data/                         # Temporary raw uploads storage
├── faiss_index/                  # Persisted Vector DB storage
└── logs/                         # Structured JSON run logs
```

## 🛠️ Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Yousaf-rao/llmops_project.git
   cd llmops_project
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file in the root directory and add your API keys:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```

## 💻 Usage

### 1. Configure Settings
Modify `multi_doc_chat/config/config.yaml` to select your preferred LLM provider (`google` or `groq`) and tweak chunk sizes.

### 2. Ingesting Data
Files can be uploaded via a UI (like Streamlit or FastAPI). The backend pipeline will:
1. Save files securely (`file_io.py`)
2. Parse documents into LangChain format (`document_ops.py`)
3. Split, Embed, and save to FAISS (`data_ingestion.py`)

### 3. Querying the Pipeline
Once the FAISS index is built, `retrieval.py` kicks in. It builds an LCEL chain to answer user questions using the ingested context.

```python
from multi_doc_chat.document_ingestion.retrieval import ConversationalRAG

rag = ConversationalRAG(session_id="user_abc123")
rag.load_retriever_from_faiss(index_path="faiss_index/user_abc123")
answer = rag.invoke("What does the document say about project deadlines?", chat_history=[])
print(answer)
```

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!

---
<p align="center">Made with ❤️ by <b>Yousaf Rao</b></p>
