import os
os.environ["USER_AGENT"] = "MonScript/1.0 (+https://github.com/eigsi)"
from langchain_core.prompts import PromptTemplate
from models import init_db
from dotenv import load_dotenv

# ------------------------------ ENV VARIABLES ------------------------------
load_dotenv()

os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# LLM_NAME = "gpt-4.1-nano-2025-04-14"
LLM_NAME = "gpt-4.1"

# ----------------------------- PROMPT TEMPLATE -----------------------------
template = """Respond **only** with a valid JSON respecting exactly this format:
{{
  "batteryPacks": [
    {{
      "name": "<name of the pack>",
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
- Ignore images.
— If you do not find new items, return "batteryPacks": [].
— **If a field is missing, use `null`.**
"""

prompt = PromptTemplate.from_template(template)

# --------------------------- INIT DB ---------------------------
if __name__ == "__main__":

    init_db() # INIT DB POSTGRESQL
    print("✅ db initialisée")
    