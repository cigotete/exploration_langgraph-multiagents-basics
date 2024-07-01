from typing import Literal
from langchain_core.runnables import ConfigurableField
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from checkpointer import PostgresSaver


@tool
def get_weather(city: Literal["nyc", "sf"]):
    """Use this to get weather information."""
    if city == "nyc":
        return "It might be cloudy in nyc"
    elif city == "sf":
        return "It's always sunny in sf"
    else:
        raise AssertionError("Unknown city")


tools = [get_weather]
model = ChatOpenAI(model_name="gpt-4o", temperature=0)



# ----------------------- Use sync connection

DB_URI = "postgresql://postgres:postgres@localhost:5432/langraph_checkpointer_data?sslmode=disable"


## ------ With a connection pool

from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    # Example configuration
    conninfo=DB_URI,
    max_size=20,
)

checkpointer = PostgresSaver(
    sync_connection=pool
)
checkpointer.create_tables(pool)

graph = create_react_agent(model, tools=tools, checkpointer=checkpointer)
config = {"configurable": {"thread_id": "1"}}
res = graph.invoke({"messages": [("human", "what's the weather in sf")]}, config)


## ------ With a connection

from psycopg import Connection

with Connection.connect(DB_URI) as conn:
    checkpointer = PostgresSaver(
        sync_connection=conn
    )

    graph = create_react_agent(model, tools=tools, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "2"}}
    res = graph.invoke({"messages": [("human", "what's the weather in sf")]}, config)

    checkpoint_tuple = checkpointer.get_tuple(config)

