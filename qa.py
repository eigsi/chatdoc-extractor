import os
os.environ["USER_AGENT"] = "MonScript/1.0 (+https://github.com/eigsi)"
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from typing_extensions import List, TypedDict
from langchain_core.documents import Document
from langgraph.graph import START, StateGraph
from dotenv import load_dotenv


# Environment variables
load_dotenv()
os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Choose llm model
llm = init_chat_model("gpt-4.1-nano-2025-04-14", model_provider="openai")

# Create vector store
vector_store = Chroma(
    embedding_function=OpenAIEmbeddings(),
)

# load the document
loader = DirectoryLoader("docs/test/", glob="**/*.pdf")

docs=loader.load()

# Split the text
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=250)
all_splits = text_splitter.split_documents(docs)

# Index chunks
_= vector_store.add_documents(documents=all_splits)

# Define Prompt
template = """Use the following pieces of context from a student course to answer the question at the end. 
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
Use three sentences maximum and keep the answer as concise as possible.

Context from the website: {context}
Question: {question}

Helpful Answer:"""
prompt = PromptTemplate.from_template(template)

class State(TypedDict):
    question: str
    context: List[Document]
    answer: str
    
def retreive(state: State):
    retreived_docs = vector_store.similarity_search(state["question"])
    return {"context": retreived_docs}

def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({
        "question": state["question"], 
        "context": docs_content
         })
    response = llm.invoke(messages)
    return {"answer": response.content}

# Compile application and test
graph_builder = StateGraph(State).add_sequence([retreive, generate])
graph_builder.add_edge(START, "retreive")
graph = graph_builder.compile()

# Question
response = graph.invoke({"question": "Quelles informations de ce documents tu pourrais mettre en tableau de façon pertiente ? fait le "})

# Print
print(response["answer"])