from dotenv import load_dotenv
load_dotenv()

import json
from langchain.chat_models import init_chat_model
from typing_extensions import List, TypedDict, Optional
from langgraph.graph import START, StateGraph
from initiate_csv import prompt, LLM_NAME
from pydantic import BaseModel, ValidationError
from models import SessionLocal, BatteryPackModel,StepModel, SubStepModel, ToolModel, PictureModel
import uuid
import os, re, requests, json
from urllib.parse import urlparse
import pandas as pd

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

# ------------------------- RETREIVE URL ---------------------------
df = pd.read_csv(DOCS_PATH, encoding="utf-8")
raw_pack = df["Battery Pack Model"].dropna().iloc[0] # Extract the bp name
safe_pack = re.sub(r'[^A-Za-z0-9_-]', '_', raw_pack).lower() # Clean the bp name
os.makedirs("images", exist_ok=True)
images_map = {}
for _, row in df.iterrows():
    n = int(row["Step Number"])
    pics = row.get("Annotated Pictures", "")
    if pd.isna(pics) or not pics.strip(): 
        continue
    urls = re.findall(r'https?://[^\s\)\,]+', pics)
    images_map[n] = urls
    
# --------------------------- DL IMAGES -----------------------------
local_images = {}
for step_num, urls in images_map.items():
    local_images[step_num] = []
    for idx, url in enumerate(urls, 1):
        try:
            r = requests.get(url, timeout=10); r.raise_for_status()
        except Exception as e:
            print(f"Error while downloading {url}: {e}")
            continue
        ext = os.path.splitext(urlparse(url).path)[1] or ".jpg"
        fname = f"{safe_pack}_step_{step_num}_img{idx}{ext}"
        path = os.path.join("images", fname)
        with open(path, "wb") as f:
            f.write(r.content)
        local_images[step_num].append(path)

# ---------------------- ADD IMAGES TO THE JSON ----------------------

data = json.loads(answer_text)
for pack in data.get("batteryPacks", []):
    for step in pack.get("steps", []):
        pics = local_images.get(step["number"], [])
        step["pictures"] = pics if pics else None
answer_text = json.dumps(data, ensure_ascii=False)


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

# ----------------------- ADD ANSWER TO DB -------------------------
session = SessionLocal()
try: 
    # BatteryPack
    for pack in doc_dict["batteryPacks"]:
        pack_id = str(uuid.uuid4())
        bp = BatteryPackModel(
            id=pack_id,
            name=pack["name"],
            picture=pack.get("picture")
        )
        # Steps
        for step in pack["steps"]:
            step_id = str(uuid.uuid4())
            st = StepModel(
                id=step_id,
                name=step["name"],
                number=step["number"],
                risks=step["risks"],
                time=step["time"],
                batteryPack_id=pack_id
            )  
            # Sub Steps
            for sub in step["sub_steps"]:
                ss = SubStepModel(
                    id=str(uuid.uuid4()),
                    name=sub["name"],
                    number=sub["number"],
                    step_id=step_id
                )
                st.sub_steps.append(ss)
                
            # Pictures
            for pic_path in step.get("pictures") or []:
                pic_obj = PictureModel(
                    id=str(uuid.uuid4()),
                    link=pic_path,
                    step_id=step_id,
                )
                st.pictures.append(pic_obj)
            

            # Tools
            for tool in step["tools"]:
                tool_obj = ToolModel(
                    id=str(uuid.uuid4()),
                    name=tool["name"],
                    step_id=step_id,
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
