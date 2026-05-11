from typing import TypedDict
from langgraph.graph import StateGraph, START, END
import time

class State(TypedDict):
    topic: str
    joke: str

def refine_topic(state: State):
    return {"topic": state["topic"] + " and cats"}

def generate_joke(state: State):
    time.sleep(1)
    return {"joke": f"This is a joke about {state['topic']}"}

graph = (
    StateGraph(State)
    .add_node(refine_topic)
    .add_node(generate_joke)
    .add_edge(START, "refine_topic")
    .add_edge("refine_topic", "generate_joke")
    .add_edge("generate_joke", END)
    .compile()
)

for chunk in graph.stream({"topic": "dogs"}, stream_mode="values"):
    """
    ● updates：每次输出只会输出节点中更新的state。
    ● values：每次输出会包含当前完整的state。
    ● messages：在调用大模型想流式输出时采用，会返回(LLM Token, metadata)。
    ● custom：从Graph节点或工具中流式输出。
    ● debug：在graph执行过程中会尽可能多的输出信息。
    """
    print(chunk)