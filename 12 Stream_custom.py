import time
from typing import TypedDict
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    query: str
    answer: str

def node(state: State):
    # 获取流式输出器
    writer = get_stream_writer()
    for x in range(10):
        time.sleep(0.5)
        # 更新六十输出器
        writer(f"{x}/10")
    return {"answer": "hello world"}


builder = StateGraph(State)
builder.add_node(node)
builder.add_edge(START, "node")
builder.add_edge("node", END)
graph = builder.compile()


for chunk in graph.stream({"query": "hello world"}, stream_mode=["custom", "values"]):
    # 使用 stream_mode="custom" 时，只会流式输出通过 writer() 发送的自定义内容，而不会自动包含节点返回的状态更新
    print(chunk)



