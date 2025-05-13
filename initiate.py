import os
os.environ["USER_AGENT"] = "MonScript/1.0 (+https://github.com/eigsi)"
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from glob import glob
from utils.images import extract_main_image
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
template = """Respond **only** with a valid JSON respecting exactly this format:
{{
  "batteryPacks": [
    {{
      "name": "<name of the pack>",
      "picture": "{main_image}",
      "steps": [
        {{
          "name": "<name of the step>",
          "number": <number>,
          "time": <duration as float>,
          "risks": "<risks as key words >",
          "sub_steps": [
            {{
              "name": "<name of the sub-step>",
              "number": <number>
            }}
            {{… repeat as many as you find …}}
          ],
          "pictures": [
            {{
              "link": "<url of the picture>"
            }}
            {{… repeat as many as you find …}}
          ],
          "tools": [
            {{
              "name": "<name of the tool>"
            }}
            {{… repeat as many as you find …}}
          ]
        }}
        {{… repeat as many as you find …}}
      ]
    }}
    {{… repeat as many as you find …}}
  ]
}}


Context from the battery pack disassembly: {context}
Question: {question}

— Do not include any comments, trailing commas, or ellipses (`…`) in the JSON.
— If you do not find new items, return "batteryPacks": [].
"""

prompt = PromptTemplate.from_template(template)

# --------------------------- SET UP VECTOR STORE ---------------------------
if __name__ == "__main__":
    # EXTRACT MAIN IMAGE
    main_images = {
      pdf_file: extract_main_image(pdf_file)
      for pdf_file in glob(f"{DOCS_PATH}/**/*.pdf", recursive=True)
    }

    docs = load_and_split_documents(DOCS_PATH)

    for doc in docs:
      src = doc.metadata["source"]
      doc.metadata["main_image"] = main_images.get(src, "")
      
  
    vector_store = create_vector_store(PERSIST_DIR)
    vector_store.add_documents(docs)
    print("✅ Vector store initialisé dans", PERSIST_DIR)
    init_db() # INIT DB POSTGRESQL
    print("✅ db initialisée")
    