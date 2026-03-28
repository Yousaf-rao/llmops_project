import os
# Hum LangChain se ChatGroq import kar rahe hain taake Groq LLM model use kar sakein
from langchain_groq import ChatGroq
# Hum LangChain se ChatGoogleGenerativeAI import kar rahe hain taake Google Gemini models use kar sakein
from langchain_google_genai import ChatGoogleGenerativeAI
# Hum LangChain se GoogleGenerativeAIEmbeddings import kar rahe hain taake Google ke embedding models use kar sakein
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Humne config load karne ka function import kiya jo apne banaya tha
from multi_doc_chat.utils.config_loader import load_config
# Hum custom exception bhi import kar rahe hain taake error ko sahi se handle aur trace kar sakein
from multi_doc_chat.exception.custom_exception import DocumentPortalException
# Humne logger apna import kiya hai taake code ka har step trace me log ho
from multi_doc_chat.logger.customlogger import CustomLogger

# Logger ka format/setup call kiya aur load karwaya apne general setup se
logger_setup = CustomLogger()
# Is existing file (__file__) ka specific naam use kar k logger initialize karaya taake pata chale console log kahan se aaye hain
logger = logger_setup.get_logger(__file__)

class ModelLoader:
    # Ye ModelLoader class ka constructor (yani jab class ka object start up ho) call hota hai
    def __init__(self, config_path: str = None):
        # Yahan hum shru me try block use kar rahe hain taake program crash na ho aur error hum pakar lein
        try:
            # Apne loader utility (load_config) ki madad se YAML config parhi, aur output class attribute (self.config) me save ho gayi
            self.config = load_config(config_path)
            # Log kiya ke configuration successfully object mein assign ho chuki hai
            logger.info("Model load karne ke liye config successfully load ho gayi hai.")
        except Exception as e:
            # Agar file read ya initialize mai koi masla hua to Custom Exception raise karo jisme detail aa jaye gi
            raise DocumentPortalException(f"Initialize karte waqt config load nai ho saki pyare bhai: {e}", e)

    # Ye function config yaml read krke Google embeddings ka object ya connection create karta hai 
    def get_embedding_model(self):
         # Execution safe rakhne ke liye sub function b try-except me rakha hai
         try:
             # Ek trace pe string record ki ke ye code run hone ja raha hai
             logger.info("Embedding model object banana shuru...")
             
             # self.config aik dictionary bun chuki h, hum ne asani se "embedding_model" wale hissay ka data bahir get krliya
             emb_config = self.config.get("embedding_model", {})
             
             # Agar configuration config de "provider" ki value me "google" de rahi ho (.lower() is liye kia ke check lowercase format me sahi se ho sakay)
             if emb_config.get("provider", "").lower() == "google":
                 # config se humne "model_name" get kia ("models/text-embedding-004") default value hum ne set kr di in-case nahi milta
                 model_name = emb_config.get("model_name", "models/text-embedding-004")
                 
                 # LangChain ki module "GoogleGenerativeAIEmbeddings" class se humne AI connection init kiya aur object banaya
                 embeddings = GoogleGenerativeAIEmbeddings(model=model_name)
                 
                 # Info terminal / backend pe log/print ho jayegi
                 logger.info(f"Google embedding model '{model_name}' successfully load ho gaya.")
                 # function apna kaam kr chuka to woh is successfully bani hui connections ya embeddings ko result ki shakal main caller ko return(dega) karega
                 return embeddings
             else:
                 # config me "google" k siwa humare pas kuch aur allowed logic me define nae ha filhal to Error pheank do
                 raise ValueError("Unsupported embedding provider in config. Sirf 'google' default supported hai config me.")
                 
         except Exception as e:
             # Hum error raise ker rehe hen trace stack exception custom wale class ki format per
             raise DocumentPortalException(f"Embedding model create/load karte huay error aya pyare bhai: {e}", e)

    # Ye function model ko instantiate krne k liye banaya  gaya ha string param (provider_name = 'google' ya 'groq') deta hs
    def get_llm(self, provider_name: str = "google"):
         try:
             # Sab se pehle function level start message generate kara ta k logs clean hon
             logger.info(f"LLM model ka provider '{provider_name}' instantiate karna shuru kiya...")
             
             # Config ki base main level per jo 'llm' tha (jisme parameters mojood thy), use fetch keya dict element tor per
             llms_config = self.config.get("llm", {})
             # Phir specific provider ka block retrieve kiya (config yaml ki inner list k provider jaise 'google' ya 'groq')
             provider_config = llms_config.get(provider_name.lower())
             
             # agr argument parameter ghalat aye ga ya config ghalat ho gy tw none aega dict, Error raise maro user p
             if not provider_config:
                 raise ValueError(f"Config me '{provider_name}' ki details nahi mili.")
             
             # parameters ki fetch block mein se hamen config dictionary ki "temperature" setting pakar li
             temperature = provider_config.get("temperature", 0)
             # "model_name" parameter bhi as key get krni hy model file mein  (For Instance gemini-2.0 ya meta vagera)
             model_name = provider_config.get("model_name")
             # Max output tokens limit v get kia string ya integer ki base par (by default 2048 lga dia fallbeck ki shakal m)
             max_tokens = provider_config.get("max_output_tokens", 2048)
             
             # Agar parameter (provider_name) request ya function se "groq" aya tha to Groq k parameters instantiate krr
             if provider_name.lower() == "groq":
                 # terminal pr message de diya Groq k mutalaq
                 logger.info(f"Groq LLM initialize horaha hai model={model_name} k sath...")
                 # Yahan per actually instance Create hua hy Groq api object or humne required details (models/temp) send krien hen parameter m
                 llm = ChatGroq(
                     model_name=model_name,
                     temperature=temperature,
                     max_tokens=max_tokens
                 )
                 # connection ho gya or object  ab caller tk pass kia gya logic
                 return llm
                 
             # Aur agar parameter humen (provider_name) string provider "google" hai tab  if nai bhal ke elif use karo
             elif provider_name.lower() == "google":
                 # google logging init format chalaya terminal p
                 logger.info(f"Google (Gemini) LLM initialize horaha hai model={model_name} k sath...")
                 # ChatGoogleGenerativeAI (Langchain module se) instance google ko generate ya instantiate kare gay config detail format krk
                 llm = ChatGoogleGenerativeAI(
                     model=model_name,
                     temperature=temperature,
                     max_output_tokens=max_tokens
                 )
                 # is object ko as ai/llm instance model result call out kare ge model/app code se
                 return llm
                 
             else:
                  # ager uper 2 me se provider (yani na google hy or na groq hi ho) to return exception kare ga failure p
                  raise ValueError(f"Unsupported LLM provider agya: {provider_name}")
                  
         except Exception as e:
               # Try format crash krke log or detailed traceback output humme Custom Exception console me print krna bhot awwal farz h developer p
               raise DocumentPortalException(f"LLM (Language Model) create karne main error aa gya: {e}", e)
