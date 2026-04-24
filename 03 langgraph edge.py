from typing import Annotated
from langgraph.types import Send, Command
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START
from langgraph.graph import StateGraph
from operator import add
from pydantic import BaseModel


class State(BaseModel):
    username: str
    calls: str | None = None

# 这是routing function, 不是具体节点
def vip_entry(state: State, config: RunnableConfig):
    vip_level = config["configurable"]["vip_level"]
    if vip_level == 1:
        return "basic_vip_node"
    elif vip_level == 2:
        return "pro_vip_node"
    elif vip_level == 3:
        return "ultra_vip_node"
    return "free_node"


def conditional_edge_demo():

    """
    条件边是通过运行一个函数来决定下一个边应该如何指向。
    这个函数可以返回一个节点的名称，也可以返回节点名称的列表，还可以返回其他值，如果返回其他值（比如bool类型），
    那么需要在add_conditional_edges中指定第三个参数
    """
    # 示例
    # graph.add_conditional_edges("node_a", routing_function)
    # # routing_function返回True或False，第三个参数指定返回值与节点名称的映射关系
    # graph.add_conditional_edges("node_a", routing_function, {True: "node_b", False: "node_c"})


    def free_node(state: State):
        return {"calls": "10次/天调用"}

    def basic_vip_node(state: State):
        return {"calls": "100次/天调用"}

    def pro_vip_node(state: State):
        return {"calls": "5000次/天调用"}

    def ultra_vip_node(state: State):
        return {"calls": "无限次/天调用"}

    builder = StateGraph(state_schema=State)
    builder.add_node("free_node", free_node)
    builder.add_node("basic_vip_node", basic_vip_node)
    builder.add_node("pro_vip_node", pro_vip_node)
    builder.add_node("ultra_vip_node", ultra_vip_node)

    # 添加条件边，由指向函数vip_entry决定走到哪个节点
    builder.add_conditional_edges(START, vip_entry)
    graph = builder.compile()

    result = graph.invoke({"username": "张三"}, config={"configurable": {"vip_level": 3}})
    print(result)

    result2 = graph.invoke({"username": "李四"}, config={"configurable": {"vip_level": 0}})
    print(result2)

def send_demo():
    """
    有些节点和边，在定义之前没法完全确定，只有在运行过程中，根据用户输入才能动态决定，
    那么这种边可以通过Send函数来实现，Send函数接受两个参数，
    第一个参数是下一个节点的名称，第二个参数是该节点需要接受的参数。
    """
    class OverallState(BaseModel):
        subjects: list[str]
        jokes: Annotated[list[str], add]

    def generate_joke(arg: dict):
        #Send指定的结点不会接受state作为参数，Send是不能更新state中的参数, 适合执行临时任务。
        return {"jokes": [f"{arg['subject']}的笑话"]}

    def joke_generator(state: OverallState):
        # send是并发执行的，不是串行执行的
        return [Send("generate_joke", {"subject": subject}) for subject in state.subjects]

    bulider = StateGraph(state_schema=OverallState)
    bulider.add_node("joke_generator", joke_generator)
    bulider.add_node("generate_joke", generate_joke)

    bulider.add_conditional_edges(START, joke_generator)
    bulider.add_edge("generate_joke", END)
    graph = bulider.compile()

    print(graph.invoke({"subjects": ["牛马", "狗"]}))

def command_demo():
    """
    如果既想动态添加边，又想添加边的时候修改State的值，那么可以使用Command来实现。
    Command对象可以同时完成以下操作：
    ● update：更新State中的字段值
    ● goto：指定下一个要执行的节点
    ● resume：用于从interrupt恢复执行
    """

    class OutputState(BaseModel):
        summarization: str

    def free_node(state: State):
        return Command(goto="summarize_node")

    def basic_vip_node(state: State):
        return Command(update={"calls": "100次/天调用"}, goto="summarize_node")

    def pro_vip_node(state: State):
        return Command(update={"calls": "5000次/天调用"}, goto="summarize_node")

    def ultra_vip_node(state: State):
        return Command(update={"calls": "无限次/天调用"}, goto="summarize_node")

    def summarize_node(state: State) -> OutputState:
        return {"summarization": f"你好，{state.username}，你的调用次数为：{state.calls}"}

    builder = StateGraph(State, output_schema=OutputState)
    builder.add_node("free_node", free_node)
    builder.add_node("basic_vip_node", basic_vip_node)
    builder.add_node("pro_vip_node", pro_vip_node)
    builder.add_node("ultra_vip_node", ultra_vip_node)
    builder.add_node("summarize_node", summarize_node)

    builder.add_conditional_edges(START, vip_entry)
    builder.add_edge("summarize_node", END)
    graph = builder.compile()
    print(graph.invoke({"username": "张三"}, config={"configurable": {"vip_level": 0}}))


if __name__ == '__main__':
    # conditional_edge_demo()
    # send_demo()
    command_demo()