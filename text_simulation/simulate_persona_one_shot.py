import os
import re
import json
import yaml
import argparse
from dotenv import load_dotenv
from typing import TypedDict, Callable
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_openrouter import ChatOpenRouter
from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware
from langchain.messages import SystemMessage, HumanMessage
from create_question_one_shot import SYSTEM_PROMPT

import asyncio
import aiosqlite
from tqdm.asyncio import tqdm
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

def extract_id(file_name):
    match = re.search(r'\d+', file_name)
    return int(match.group()) if match else 0

class Facet(TypedDict):
    name: str
    description: str
    content: str

async def simulate_persona_with_pid(model, pid: int, input_text: str, facets: list[Facet], sem, checkpointer):

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

        def awrap_model_call(
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

    agent = create_agent(
        model,
        system_prompt=SystemMessage(SYSTEM_PROMPT),
        middleware=[FacetMiddleware()],
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": str(pid)}}

    async with sem:
        response = await agent.ainvoke(
            {"messages": [HumanMessage(input_text)]},
            config
        )

    return response

async def simulate_persona(model, config):
    load_dotenv()

    input_files = sorted(os.listdir(config['input_dir']), key=extract_id)[:config['max_personas']]
    persona_files = sorted(os.listdir(config['persona_dir']), key=extract_id)[:config['max_personas']]

    input_text_list = []
    persona_facets_list = []

    for input_file, persona_file in zip(input_files, persona_files):
        with open(os.path.join(config['input_dir'], input_file), "r", encoding="utf-8") as f:
            input_text_list.append(f.read())
        with open(os.path.join(config['persona_dir'], persona_file), "r", encoding="utf-8") as f:
            persona_facets_list.append(json.load(f))
    
    sem = asyncio.Semaphore(config['semaphore'])
    conn = aiosqlite.connect(config['save_path'], check_same_thread=False)
    checkpointer = AsyncSqliteSaver(conn)
    tasks = [simulate_persona_with_pid(model, pid, input_text, facets, sem, checkpointer)
             for pid, (input_text, facets) in enumerate(zip(input_text_list, persona_facets_list), start=1)]

    results = await tqdm.gather(*tasks, total=len(tasks), desc="Simulating persona")
    return results
        
async def simulate_persona_with_config(config):
    model = init_chat_model(
        model=config['model_identifier'],
        temperature = config["temperature"],
        base_url="http://localhost:8000/v1",
        model_provider="openai",
        extra_body={"chat_template_kwargs": {"enable_thinking": False}}
    )

    output_dir = config['output_dir']
    os.makedirs(output_dir, exist_ok=True)

    print("Start simulating...")
    results = await simulate_persona(model, config)

    for pid, response in enumerate(results, start=1):
        response_json = {"persona_id": f"pid_{pid}", "response_text": response["messages"][-1].content}
        with open(os.path.join(output_dir, f"pid_{pid}_response.json"), "w") as f:
            json.dump(response_json, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)

    args = parser.parse_args()

    try:
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error opening config file: {e}")

    asyncio.run(simulate_persona_with_config(config))