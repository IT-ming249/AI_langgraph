from dataclasses import dataclass
from langgraph.graph import StateGraph, START
from langchain.messages import HumanMessage
from llm import model
import time


@dataclass
class MyState:
    topic: str
    joke: str = ""


def call_model(state: MyState):
    """Call the LLM to generate a joke about a topic"""
    # 大模型调用可以使用model.invoke而不用stream，因为stream_mode="messages"会解决一切流式
    model_response = model.invoke([HumanMessage(content=f"生成一个关于{state.topic}的笑话。")])
    return {"joke": model_response.content}

graph = (
    StateGraph(MyState)
    .add_node(call_model)
    .add_edge(START, "call_model")
    .compile()
)


for chunk, metadata in graph.stream(
    {"topic": "dogs"},
    stream_mode="messages",
):
    # stream_mode="messages"才能一个token一个token的流式输出
    if chunk.content:
        time.sleep(1)
        print(chunk.content, end="|", flush=True)