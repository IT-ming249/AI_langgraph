from typing import TypedDict, Annotated
from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import RunnableConfig
from operator import add
from langgraph.graph import MessagesState

"""
State是用于在多个节点之间传递数据的对象，它可以是typing.TypedDict类对象，也可以是pydantic.BaseModel对象，
他可以定义每个字段的类型，约束条件以及更新字段值的函数等。
通常情况下，Graph对象的Input State和OutputState是相同的，但是也可以定义不同的Input和Output Schema，
甚至还可以定义内部节点传输数据的PrivateState
"""

### 基础只是
# State中定义的字段，在多个Node之间传递时，当值发生改变时，默认情况下是替换
# 想在多个节点之间更新State的时候不是直接替换，那么可以设置reducer函数↓
class State(TypedDict):
    username: int
    input:  str
    hobbies: Annotated[list[str], add] #这样以后遇到新的hobby就会添加进列表中而不是替换

# Node函数的第一个参数为state，
# 第二个参数为config: langchain_core.runnables.RunnableConfig，在config中可以存放比如线程id（thread_id）等
def node_demo(state: State, config: RunnableConfig):
    print("In node: ", config["configurable"]["user_id"])
    return {"results": f"Hello, {state['input']}!"}


## 实际demo
class InputState(TypedDict):
    user_input: str

class OutputState(TypedDict):
    graph_output: str

class OverallState(TypedDict):
    device: str
    user_input: str
    graph_output: str

class PrivateState(TypedDict):
    emotion: int


def node_1(state: InputState) ->OutputState:
    device = state['user_input'].split(":")[-1]
    return {"device": device} # user_input langgraph会自己从state里面识别，找得到就会添加进去

def node_2(state: OverallState) ->PrivateState:
    user_input = state['user_input']
    if user_input.index("开心") > 0:
        return {"emotion": 10}
    elif user_input.index("不开心") > 0:
        return {"emotion": -10}
    return {"emotion": 0}

def node_3(state: PrivateState) ->OutputState:
    return {"graph_output": f"你的心情是{state['emotion']}"}

# graph_builder = StateGraph(MessagesState) MessagesState已经预定义了messages字段，可以直接使用, 或者像demo01 一样手动定义
builder = StateGraph(state_schema=OverallState, input_schema=InputState, output_schema=OutputState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

# START节点是一个特殊节点，由它指向的节点将会成为该智能体第一个执行的节点。
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
# END节点也是一个特殊节点，当他的上一个节点执行完后，代表当次智能体的运行已经结束
builder.add_edge("node_3", END)
graph = builder.compile()

# 本次没有调用任何大模型，这个demo里面的是高级用法，一般来说input_schema和output_schema是相同的
result = graph.invoke({"user_input": "今天开心。 来自:安卓"})
print(result)

