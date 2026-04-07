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
from langchain.messages import SystemMessage, HumanMessage, AIMessage
from create_question_multi_shot import SYSTEM_PROMPT

import asyncio
import aiofiles
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

import asyncio
import os
import aiofiles

def read_question(input_dir: str) -> list:
    questions = sorted(os.listdir(input_dir))
    
    def read_file(file_name):
        file_path = os.path.join(input_dir, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    question_text_list = [read_file(q) for q in questions]
    return question_text_list


async def simulate_persona_with_pid(model, pid: int, input_dir: str, facets: list[Facet], sem, checkpointer):

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

        async def awrap_model_call(
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
            return await handler(modified_request)

    agent = create_agent(
        model,
        system_prompt=SystemMessage(SYSTEM_PROMPT),
        middleware=[FacetMiddleware()],
        checkpointer=checkpointer,
    )

    question_text_list = read_question(input_dir)

    async def process_question(question_id, question_text):
        async with sem:
            response = await agent.ainvoke(
                {"messages": [HumanMessage(question_text)]},
                config={"configurable": {"thread_id": f"pid_{pid}_Q{question_id}"}}
            )
            return response

    tasks = [
        process_question(i, text) 
        for i, text in enumerate(question_text_list, start=1)
    ]
    
    response_to_all_question = await asyncio.gather(*tasks)
    return response_to_all_question

async def simulate_persona(model, config):
    load_dotenv()

    input_dirs = sorted(os.listdir(config['input_dir']), key=extract_id)[:config['max_personas']]
    persona_files = sorted(os.listdir(config['persona_dir']), key=extract_id)[:config['max_personas']]

    input_dir_list = []
    persona_facets_list = []

    for input_dir, persona_file in zip(input_dirs, persona_files):
        input_dir_list.append(os.path.join(config['input_dir'], input_dir))

        with open(os.path.join(config['persona_dir'], persona_file), "r", encoding="utf-8") as f:
            persona_facets_list.append(json.load(f))
    
    sem = asyncio.Semaphore(config['semaphore'])
    async with aiosqlite.connect(config['save_path'], check_same_thread=False) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        tasks = [simulate_persona_with_pid(model, pid, input_dir, facets, sem, checkpointer)
             for pid, (input_dir, facets) in enumerate(zip(input_dir_list, persona_facets_list), start=1)]
        results = await tqdm.gather(*tasks, total=len(tasks), desc="Simulating persona")

    return results

def process_response_text(response_text) -> dict:
    try:
        if "```json" in response_text:
            response_text_json = json.loads(response_text.split("```json")[1].split("```")[0])
        else:
            json_pattern = r'(\{.*\}|\[.*\])'
            match = re.search(json_pattern, response_text, re.DOTALL)
            response_text_json = json.loads(match.group(1))
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error parsing response JSON for: {e}")
        return {}

    return response_text_json

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

    for pid, response_to_all_question in enumerate(results, start=1):
        converge_json = {}
        for response_to_one_question in response_to_all_question:
            text_to_one_question = response_to_one_question["messages"][-1].content
            json_to_one_question = process_response_text(text_to_one_question)
            converge_json.update(json_to_one_question)

        response_json = {"persona_id": f"pid_{pid}", "response_text": json.dumps(converge_json)}
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