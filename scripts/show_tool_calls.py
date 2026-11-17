"""Lab 42: hand the tool wall to the real model and look at the tool calls it asks for.

Run with: uv run python scripts/show_tool_calls.py
Needs Ollama on http://localhost:11434 with the chat model pulled. No tool is executed:
we only look at what the model requests.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from sovereign_brain.core.settings import get_settings
from sovereign_brain.graphs.research import RESEARCH_PROMPT
from sovereign_brain.llm.factory import get_chat_model
from sovereign_brain.tools.registry import RESEARCH_TOOLS, wire_format

QUESTION = (
    "Client C-1042 (Amina Rahman Holdings, private-banking, risk profile moderate): "
    "What would a 40% fall in energy stocks cost this portfolio? The sector holds "
    "185000 USD of a 1000000 USD portfolio."
)

print("What the model receives for the stress_test tool:")
print(json.dumps(wire_format(RESEARCH_TOOLS[-1]), indent=2))

model = get_chat_model(get_settings()).bind_tools(RESEARCH_TOOLS)
reply = model.invoke([SystemMessage(RESEARCH_PROMPT), HumanMessage(QUESTION)])

print("\nWhat the model asks for:")
for call in reply.tool_calls:
    print(f"- {call['name']}({json.dumps(call['args'])})  id={call['id']}")
if not reply.tool_calls:
    print(f"- no tool call; the model answered directly: {reply.content}")
