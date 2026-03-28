from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.messages import SystemMessage, HumanMessage

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

import asyncio

load_dotenv()

model = init_chat_model(
    model="deepseek-chat"
)




async def simulate():
    conn = aiosqlite.connect("test.db", check_same_thread=False)
    checkpointer = AsyncSqliteSaver(conn)

    agent = create_agent(
        model=model,
        system_prompt=SystemMessage("你是一个全能助手！"),
        checkpointer=checkpointer
    )

    thread_id = str(1)
    config = {"configurable": {"thread_id": thread_id}}

    human_messages = [{"messages": [HumanMessage("我的第一个问题是？")]}]

    for human_message in human_messages:
        response = await agent.ainvoke(human_message, config=config)

    for message in response["messages"]:
        message.pretty_print()

if __name__ == "__main__":
    asyncio.run(simulate())