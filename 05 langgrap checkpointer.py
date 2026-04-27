from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class State(TypedDict):
    username: str
    hobbies: Annotated[list[str], add]


def node_a(state: State):
    return {"username": "张三", "hobbies": ["唱", "跳"]}

def node_b(state: State):
    return {"username": "坤坤", "hobbies": ["篮球"]}

builder = StateGraph(state_schema=State)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")


checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# 注意：InMemorySaver仅适用于开发和测试环境
# 生产环境应使用支持持久化存储的checkpointer，如：
# - SqliteSaver（SQLite数据库）
# - PostgresSaver（PostgreSQL数据库）
# - MemorySaver（内存，与InMemorySaver类似但API略有不同）

config = {"configurable": {"thread_id": "1"}}
response = graph.invoke({"username": ""}, config)
print(response, end="\n\n")

# 获取最近一次的状态
# lastest_state = graph.get_state(config)
# print(lastest_state)

# 获取历史状态
for state_snapshot in graph.get_state_history(config):
    print(state_snapshot, end="\n\n")