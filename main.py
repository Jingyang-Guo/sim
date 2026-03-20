import os
import re
from dotenv import load_dotenv
import json
from typing import TypedDict, Callable
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware
from langchain.messages import SystemMessage, HumanMessage
from prompt import system_prompt
from tqdm import tqdm


import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

def extract_id(file_name):
    match = re.search(r'\d+', file_name)
    return int(match.group()) if match else 0

class Facet(TypedDict):
    name: str
    description: str
    content: str

def simulate_persona(pid: int, input: str, facets: list[Facet]):
    @tool
    def retrieve_persona_facet(facet_name: str) -> str:
        """Retrieve the content of a specific facet of the persona, which includes historical responses to a series of questions. 

        Args:
            facet_name: The name of the facet to retrieve.
        """
        for facet in facets:
            if facet["name"] == facet_name:
                return f"Retrieved Facet: {facet_name}\n\nContent: {facet['content']}"

        available = ", ".join(f["name"] for f in facets)
        return f"Facet '{facet_name}' not found. Available facets for this persona: {available}"

    class FacetMiddleware(AgentMiddleware):        
        tools = [retrieve_persona_facet]
        
        def __init__(self):
            facet_list = []
            for facet in facets:
                facet_list.append(
                    f"- **{facet['name']}**: {facet['description']}"
                )
            self.facets_prompt = "\n".join(facet_list)

        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            facets_addendum = (
                f"\n\n## Available Facets\n\n{self.facets_prompt}\n\n"
                "Use the 'retrieve_persona_facet' tool when you need detailed information "
                "about the persona."
            )

            new_content = list(request.system_message.content_blocks) + [
                {"type": "text", "text": facets_addendum}
            ]
            new_system_message = SystemMessage(content=new_content)
            modified_request = request.override(system_message=new_system_message)
            return handler(modified_request)
    
    model = init_chat_model(model="deepseek-chat")

    conn = sqlite3.connect("conversations.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    agent = create_agent(
        model,
        system_prompt=SystemMessage(system_prompt),
        middleware=[FacetMiddleware()],
        checkpointer=checkpointer,
    )

    thread_id = str(pid)
    config = {"configurable": {"thread_id": thread_id}}

    result = agent.invoke(
        {"messages": [HumanMessage(input)]},
        config
    )

    return result

if __name__ == "__main__":
    input_files = sorted(os.listdir("questions"), key=extract_id)
    skills_files = sorted(os.listdir("skills"), key=extract_id)

    input_list = []
    skills_list = []

    for input_file, skills_file in zip(input_files, skills_files):
        with open(f"questions/{input_file}", "r", encoding="utf-8") as f:
            input_list.append(f.read())
        with open(f"skills/{skills_file}", "r", encoding="utf-8") as f:
            skills_list.append(json.load(f))

    input_list = input_list[:100]
    skills_list = skills_list[:100]

    pid = 1
    for input, skills in tqdm(zip(input_list, skills_list), total=len(input_list), desc="Simulating personas"):
        result = simulate_persona(pid, input, skills)
        pid += 1