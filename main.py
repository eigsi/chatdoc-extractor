import json
from langchain.chat_models import init_chat_model
from typing_extensions import List, TypedDict, Optional
from langchain_core.documents import Document
from langgraph.graph import START, StateGraph
from initiate import create_vector_store, prompt, PERSIST_DIR, LLM_NAME
from pydantic import BaseModel, ValidationError
from models import SessionLocal, BatteryPackModel,StepModel, SubStepModel, ToolModel, PictureModel
import uuid

llm = init_chat_model(LLM_NAME, model_provider="openai")
vector_store = create_vector_store(PERSIST_DIR)

class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

# --------------------------- GRAPH STEPS --------------------------- 
def retrieve(state: State) -> dict:
    docs: List[Document] = vector_store.similarity_search(state["question"], k=30)
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
question = "Retrieve all the disassembly steps for this battery pack, including sub-steps formulated from each step’s description, the necessary tools for each step, and the corresponding photos."


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
class SubStep(BaseModel):
    name: str
    number: int

class Picture(BaseModel):
    link: str

class Tool(BaseModel):
    name: str

class Step(BaseModel):
    name: str
    number: int
    time: float
    sub_steps: List[SubStep]
    pictures: List[Picture]
    tools: List[Tool]

class BatteryPack(BaseModel):
    name: str
    picture: Optional[str]
    steps: List[Step]

class BatteryPacksList(BaseModel):
    batteryPacks: List[BatteryPack]


try: 
    data = json.loads(answer_text)
    doc = BatteryPacksList(**data)
    print("✅ JSON valide, objet prêt à l'emploi")
except(json.JSONDecodeError, ValidationError) as e:
      print("❌ Erreur de parsing :", e)

doc_dict = doc.model_dump()

# -------------------------- ADD ALL ID --------------------------
for pack in doc_dict["batteryPacks"]:
        pack_id = uuid.uuid4()
        pack["id"] = str(pack_id)
        for step in pack["steps"]:
            step_id = uuid.uuid4()
            step["id"] = str(step_id)
            step["batteryPack_id"] = str(pack_id)
            for sub in step["sub_steps"]:
                sub_id = uuid.uuid4()
                sub["id"] = str(sub_id)
                sub["step_id"] = str(step_id)
            for pic in step["pictures"]:
                pic_id = uuid.uuid4()
                pic["id"] = str(pic_id)
                pic["step_id"] = str(step_id)
            for tool in step["tools"]:
                tool_id = uuid.uuid4()
                tool["id"] = str(tool_id)
                tool["step_id"] = str(step_id)

# ----------------------- ADD ANSWER TO DB -------------------------
session = SessionLocal()
try: 
    # BatteryPack
    for pack in doc_dict["batteryPacks"]:
        bp = BatteryPackModel(
            id=pack["id"],
            name=pack["name"],
            picture=pack.get("picture")
        )
        # Steps
        for step in pack["steps"]:
            st = StepModel(
                id=step["id"],
                name=step["name"],
                number=step["number"],
                time=step["time"],
                batteryPack_id=step["batteryPack_id"]
            )  
            # Sub Steps
            for sub in step["sub_steps"]:
                ss = SubStepModel(
                    id=sub["id"],
                    name=sub["name"],
                    number=sub["number"],
                    step_id=sub["step_id"]
                )
                st.sub_steps.append(ss)

            # Pictures
            for pic in step["pictures"]:
                pic_obj = PictureModel(
                    id=pic["id"],
                    link=pic["link"],
                    step_id=pic["step_id"]
                )
                st.pictures.append(pic_obj)
            # Tools
            for tool in step["tools"]:
                tool_obj = ToolModel(
                    id=tool["id"],
                    name=tool["name"],
                    step_id=tool["step_id"]
                )
                st.tools.append(tool_obj)

            bp.steps.append(st)

        session.merge(bp)

    session.commit()
    print("✅ Données insérées/mises à jour dans batteryPacks")
except Exception as e:
    session.rollback()
    print("❌ Erreur en base :", e)
finally:
    session.close()
