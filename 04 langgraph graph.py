from langchain_core.runnables import RunnableConfig
from langgraph.graph import  START
from langgraph.graph import StateGraph
from pydantic import BaseModel


class State(BaseModel):
    username: str
    calls: str | None = None

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

    # 1. 以ASCII码的形式绘制graph 图
    graph.get_graph().print_ascii()

    # 2. PNG形式输出，看网络环境
    graph.get_graph().draw_mermaid_png(output_file_path="graph.png")


    # result = graph.invoke({"username": "张三"}, config={"configurable": {"vip_level": 3}})
    # print(result)





if __name__ == '__main__':
    conditional_edge_demo()
