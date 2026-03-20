import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect('conversations.db', check_same_thread=False)


conn.close()