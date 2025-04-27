import json
from langchain.chat_models import init_chat_model
from typing_extensions import List, TypedDict
from langchain_core.documents import Document
from langgraph.graph import START, StateGraph
from initiate import create_vector_store, prompt, PERSIST_DIR, LLM_NAME
from pydantic import BaseModel, ValidationError
from models import SessionLocal, LichenModel

llm = init_chat_model(LLM_NAME, model_provider="openai")
vector_store = create_vector_store(PERSIST_DIR)

class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

# --------------------------- GRAPH STEPS --------------------------- 
def retrieve(state: State) -> dict:
    docs: List[Document] = vector_store.similarity_search(state["question"], k=10)
    return { "context": docs }

def generate(state: State) -> dict:
    context_text = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({
        "question": state["question"], 
        "context": context_text
         })
    answer = llm.invoke(messages)
    return {"answer": answer.content}

# -------------------------- INITIATE GRAPH -------------------------
graph = (
    StateGraph(State)
    .add_sequence([retrieve, generate])
    .add_edge(START, "retrieve")
    .compile()
)

# -------------------------- ASK QUESTION ---------------------------
question = "Lis ce cours à propos des lichens et liste tous les types que tu trouves avec leur nom et une courte description. Tu dois mettre tous les types que tu trouves pas seulement le premier"

result = graph.invoke({ "question": question })
answer_text = result["answer"]

# --------------------------- SAVE ANSWER ---------------------------
answer_doc = Document(
    page_content = answer_text,
    metadata = {"source": "chat_response"},
)
vector_store.add_documents([answer_doc])

print(answer_text)

# -------------------------- VERIFY ANSWER --------------------------
class Lichen(BaseModel):
    name: str
    description: str
    
class LichensList(BaseModel):
    lichens: List[Lichen]

try: 
    data = json.loads(answer_text)
    doc = LichensList(**data)
    print("✅ JSON valide, objet prêt à l'emploi")
except(json.JSONDecodeError, ValidationError) as e:
      print("❌ Erreur de parsing :", e)
      
# ----------------------- ADD ANSWER TO DB -------------------------
session = SessionLocal()
try: 
    for lichen in doc.lichens:
        orm_obj = LichenModel(name=lichen.name, description=lichen.description)
        session.merge(orm_obj)
    session.commit()
    print("✅ Données insérées/mises à jour dans lichens")
except Exception as e:
    session.rollback()
    print("❌ Erreur en base :", e)
finally:
    session.close()
