from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_openrouter import ChatOpenRouter
from langchain.messages import HumanMessage

import yaml

# load_dotenv()

# model = ChatOpenRouter(model="qwen/qwen3.5-397b-a17b")

# print(model.invoke("hi"))
#
with open(r"D:\simulation\sim\text_simulation\config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

print(type(config['model_identifier']))