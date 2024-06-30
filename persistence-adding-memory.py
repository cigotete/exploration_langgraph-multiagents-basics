from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph.message import add_messages



# ------------------------ Setting up the State
# ------------------------------------------------
# Add messages essentially does this with more robust handling:
# def add_messages(left: list, right: list):
#     return left + right


class State(TypedDict):
    messages: Annotated[list, add_messages]



# ------------------------ Setting up the tools
# ------------------------------------------------
from langchain_core.tools import tool
@tool
def search(query: str):
    """Call to surf the web."""
    # This is a placeholder for the actual implementation
    return ["The answer to your question lies within."]

tools = [search]

from langgraph.prebuilt import ToolNode
tool_node = ToolNode(tools)



# ------------------------ Setting up the model
# ------------------------------------------------
from langchain_openai import ChatOpenAI

# We will set streaming=True so that we can stream tokens
model = ChatOpenAI(temperature=0, streaming=True)
bound_model = model.bind_tools(tools)



# ------------------------ Defining the graph
# ------------------------------------------------
# Define the function that determines whether to continue or not
from typing import Literal

def should_continue(state: State) -> Literal["action", "__end__"]:
    """Return the next node to execute."""
    last_message = state["messages"][-1]
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return "__end__"
    # Otherwise if there is, we continue
    return "action"

# Define the function that calls the model
def call_model(state: State):
    response = model.invoke(state["messages"])
    # We return a list, because this will get added to the existing list
    return {"messages": response}

from langgraph.graph import StateGraph

# Define a new graph
workflow = StateGraph(State)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)

# Set the entrypoint as `agent`
# This means that this node is the first one called
workflow.set_entry_point("agent")

# We now add a conditional edge
workflow.add_conditional_edges(
    # First, we define the start node. We use `agent`.
    # This means these are the edges taken after the `agent` node is called.
    "agent",
    # Next, we pass in the function that will determine which node is called next.
    should_continue,
)

# We now add a normal edge from `tools` to `agent`.
# This means that after `tools` is called, `agent` node is called next.
workflow.add_edge("action", "agent")



# ------------------------ Persistence
# ------------------------------------------------
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string(":memory:")

# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
app = workflow.compile(checkpointer=memory)

app.get_graph(xray=1).draw_mermaid_png(output_file_path="persistence-adding-memory.png")



# ------------------------  Interacting with the agent.
# ------------------------------------------------
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "2"}}
input_message = HumanMessage(content="hi! I'm bob")
for event in app.stream({"messages": [input_message]}, config, stream_mode="values"):
    event["messages"][-1].pretty_print()

input_message = HumanMessage(content="what is my name?")
for event in app.stream({"messages": [input_message]}, config, stream_mode="values"):
    event["messages"][-1].pretty_print()

# A different thread gives a new conversation, due all then memories are gone.
input_message = HumanMessage(content="what is my name?")
for event in app.stream(
    {"messages": [input_message]},
    {"configurable": {"thread_id": "3"}},
    stream_mode="values",
):
    event["messages"][-1].pretty_print()

# Resuming previous thread.
input_message = HumanMessage(content="You forgot??")
for event in app.stream(
    {"messages": [input_message]},
    {"configurable": {"thread_id": "2"}},
    stream_mode="values",
):
    event["messages"][-1].pretty_print()