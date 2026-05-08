import os

from pycparser.c_ast import While
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.func import task
from langgraph.checkpoint.postgres import PostgresSaver
from llm import model


"""
知识点1
由于恢复时会发生“回放/重放”（后文解释），如果你的代码里有：
● 随机数、当前时间
● 文件写入、数据库写入
● HTTP 请求、扣费、下单
这些都属于非确定性或有副作用的操作。为了让恢复更安全、结果可重放，你需要把这些操作包进 @task，让 LangGraph 能从持久化层取回“上次已完成的结果”，从而避免重复执行。

知识点2
node_a -> node_b(写文件、interrrupt)
● StateGraph（Graph API）：恢复的起点是“上次停止所在的那个 node 的开头”，通过知识点1可以规避重新写（或其它操作）
● Functional API：恢复的起点是“entrypoint 的开头”
● 子图：如果 node 内部调用了 subgraph，停止点在 subgraph 中时，父图可能从“调用 subgraph 的父 node”开始重放
因此：node 开头到 interrupt/异常之前的代码，可能会在恢复时再次执行。如果这些代码包含副作用，就会造成重复写入/重复扣费/重复请求等风险。

知识点3
调用任意执行方法（如 invoke/stream）时都可以指定：
graph.stream({"input": "test"}, durability="sync")
三种模式：
● "exit"：只在图执行结束（成功/失败/interrupt）时写 checkpoint。中间过程不存盘，进程中途崩溃无法恢复到中间状态。
● "async"：异步写 checkpoint，性能较好，但进程瞬间崩溃时可能来不及写最后一步。
● "sync"：每一步都同步写完再继续，最稳但开销更大。
在生产环境下看性能与可靠性权衡；关键链路建议 sync

"""

class State(TypedDict):
    """图的状态（在 node 之间流转）"""
    topic: str
    joke: str



@task
def write_joke(content: str):
    try:
        with open("joke.txt", "a", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        return False


def topic_joke_node(state: State):
    """
    模拟人机交互节点：暂停，等待人类给出最终文本。
    注意：恢复后会从该函数开头重放，所以把副作用放到 task 更安全。
    """

    # 1. 用户输入笑话主题
    topic = interrupt(f"我现在需要你输入一个笑话主题。")
    t = write_joke(topic)
    result = t.result()
    if not result:
        raise RuntimeError("笑话主题写入失败")

    # 2. 获取笑话，并交给用户审核后写入文件
    while True:
        joke = model.invoke(f"请生成一个关于“{topic}”的笑话。")
        option = interrupt(f"请审核并确认以下笑话是否正确：\n{joke.content}\n 审核通过输入1，不通过输入2")
        if option == "1":
            t = write_joke(joke.content)
            result = t.result()
            if not result:
                raise RuntimeError("笑话写入失败")
            break

    return {"topic": topic, "joke": joke}


def main():
    DB_URI = "postgresql://postgres:123456@127.0.0.1:5432/agent_chat_history"
    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        builder = StateGraph(State)
        builder.add_node("topic_joke_node", topic_joke_node)
        builder.add_edge(START, "topic_joke_node")
        builder.add_edge("topic_joke_node", END)
        graph = builder.compile(checkpointer=checkpointer)

        # 同一个 thread_id才能续跑同一个执行实例
        # thread_id；生产请用业务ID或 uuid
        config = {
            "configurable": {
                "thread_id": "11",
            }
        }
        result = graph.invoke({}, config=config, durability="sync")

        while True:
            if "__interrupt__" in result:
                graph_message = result["__interrupt__"][0].value
                print(graph_message)
                user_input = input("请输入：")
                # 恢复执行，把用户输入的内容通过Command(resume=...)传回去
                result = graph.invoke(Command(resume=user_input), config=config, durability="sync")
            else:
                print(result)
                break


if __name__ == '__main__':
    main()