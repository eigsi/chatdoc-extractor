import os
os.environ["USER_AGENT"] = "MonScript/1.0 (+https://github.com/eigsi)"
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from models import init_db
from dotenv import load_dotenv

# ------------------------------ ENV VARIABLES ------------------------------
load_dotenv()

os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

LLM_NAME = "gpt-4.1-nano-2025-04-14"
DOCS_PATH = "docs/"
PERSIST_DIR = "./chroma_langchain_db"

# ---------------------------- LOAD & SPLIT DOCS ----------------------------
def load_and_split_documents(path, glob="**/*.pdf", chunk_size=1000, chunk_overlap=250):
    loader = DirectoryLoader(path, glob=glob)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(docs)

# --------------------------- CREATE VECTOR STORE ---------------------------
def create_vector_store(persist_directory):
    client = Chroma(
        embedding_function=OpenAIEmbeddings(),
        persist_directory=persist_directory
    )
    return client

# ----------------------------- PROMPT TEMPLATE -----------------------------
template = """Réponds **uniquement** par un JSON valide respectant exactement ce schéma:
{{
  "lichens": [
    {{
      "name": "<nom du lichen>",
      "description": "<courte description>"
    }},
    {{… plusieurs fois selon ce que tu trouves …}}
  ]
}}


Context from the course: {context}
Question: {question}

— Ne mets aucun commentaire, aucune explication, rien avant ou après le JSON.  
— Si tu ne trouve pas de nouveaux lichens, renvoie `"lichens": []`."""

prompt = PromptTemplate.from_template(template)

# --------------------------- SET UP VECTOR STORE ---------------------------
if __name__ == "__main__":
    docs = load_and_split_documents(DOCS_PATH)
    vector_store = create_vector_store(PERSIST_DIR)
    vector_store.add_documents(docs)
    print("✅ Vector store initialisé dans", PERSIST_DIR)
    init_db() # INIT DB POSTGRESQL
    print("✅ db initialisée")
    