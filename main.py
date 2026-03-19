import json
from typing import TypedDict, Callable
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware
from langchain.messages import SystemMessage, HumanMessage

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

class Skill(TypedDict):
    """A skill that can be progressively disclosed to the agent."""
    name: str
    description: str
    content: str

with open(f"skills/pid_{pid}_skills.json", "r", encoding="utf-8") as f:
    skills = json.load(f)

@tool
def load_skill(skill_name: str) -> str:
    """Load the full content of a skill into the agent's context.

    Use this when you need detailed information about how to handle a specific
    type of request. This will provide you with comprehensive instructions,
    policies, and guidelines for the skill area.

    Args:
        skill_name: The name of the skill to load.
    """
    for skill in skills:
        if skill["name"] == skill_name:
            return f"Loaded skill: {skill_name}\n\n{skill['content']}"

    available = ", ".join(s["name"] for s in skills)
    return f"Skill '{skill_name}' not found. Available skills: {available}"

class SkillMiddleware(AgentMiddleware):
    """Middleware that injects skill descriptions into the system prompt."""

    # Register the load_skill tool as a class variable
    tools = [load_skill]

    def __init__(self):
        """Initialize and generate the skills prompt from skills."""
        # Build skills prompt from the skills list
        skills_list = []
        for skill in skills:
            skills_list.append(
                f"- **{skill['name']}**: {skill['description']}"
            )
        self.skills_prompt = "\n".join(skills_list)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Sync: Inject skill descriptions into system prompt."""
        # Build the skills addendum
        skills_addendum = (
            f"\n\n## Available Skills\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request."
        )

        # Append to system message content blocks
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return handler(modified_request)

from langchain.chat_models import init_chat_model
model = init_chat_model(model="deepseek-chat")

conn = sqlite3.connect("conversations.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

agent = create_agent(
    model,
    system_prompt=SystemMessage("You are a helpful assistant."),
    middleware=[SkillMiddleware()],
    checkpointer=checkpointer,
)

if __name__ == "__main__":
    thread_id = str(1)
    config = {"configurable": {"thread_id": thread_id}}

    result = agent.invoke(
        {"messages": [HumanMessage("你好，我是小明")]},
        config
    )

    for message in result["messages"]:
        if hasattr(message, 'pretty_print'):
            message.pretty_print()
        else:
            print(f"{message.type}: {message.content}")