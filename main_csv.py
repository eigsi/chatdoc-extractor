from dotenv import load_dotenv
load_dotenv()

import json
from langchain.chat_models import init_chat_model
from typing_extensions import List, TypedDict, Optional
from langgraph.graph import START, StateGraph
from initiate_csv import prompt, LLM_NAME
from pydantic import BaseModel, ValidationError
from models import SessionLocal, BatteryPackModel,StepModel, SubStepModel, ToolModel
import uuid
import json

DOCS_PATH = "docs/Disassembly.csv"

llm = init_chat_model(LLM_NAME, model_provider="openai")

class State(TypedDict):
    question: str
    context: List[str]
    answer: str
    
# --------------------------- GRAPH STEPS --------------------------- 
def retrieve(state: State) -> dict:
    with open(DOCS_PATH, encoding="utf-8") as f:
        full_csv = f.read()
    return {"context": [full_csv]}

def generate(state: State) -> dict:
    context_text = state["context"][0] # the whole CSV file
    messages = prompt.invoke({
        "question": state["question"], 
        "context": context_text,
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
question = (
    "Given this CSV with columns: Id, Step Number, Title, Description, "
    "Time Estimation – Minutes, Identified Risk, Automation Potential, "
    "Step Type, Tools, Extracted Component, Annotated Pictures, Battery Pack Model, "
    "Battery-Fixings, Created, Last Modified, do the following for every disassembly step: \n"
    "1. From the Description field, break out each numbered line into a concise bullet-point sub-step.\n"
    "2. Extract the list of required tools from the Tools column.\n"
    "3. Take the duration (in minutes) from the Time Estimation – Minutes column.\n"
    "4. Summarize the Identified Risk column as a comma-separated list, omitting any purely repetitive-task risks.\n"
)

result = graph.invoke({ "question": question })
answer_text = result["answer"]

# --------------------------- SAVE ANSWER ---------------------------

print(answer_text)

# -------------------------- VERIFY ANSWER --------------------------
class SubStep(BaseModel):
    name: str
    number: int

class Tool(BaseModel):
    name: str

class Step(BaseModel):
    name: str
    number: int
    time: Optional[float]
    risks: Optional[str] = None
    sub_steps: List[SubStep]
    pictures: Optional[List[str]] = None
    tools: List[Tool]

class BatteryPack(BaseModel):
    name: str
    picture: Optional[str] = None
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
            for pic in step.get("pictures") or []:
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
                risks=step["risks"],
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
