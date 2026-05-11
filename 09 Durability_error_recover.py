import os

from pycparser.c_ast import While
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.func import task
from langgraph.checkpoint.postgres import PostgresSaver
from llm import model


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
    # result = False # 手都改了，这里模拟失败
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
    # 只用 InMemorySaver 无法跨进程恢复，必须使用数据库等持久化手段
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
                "thread_id": "111",
            }
        }
        # 如果想要从上一次出现异常的地方开始重新执行， input需要传None, 并解决掉异常
        result = graph.invoke(None, config=config, durability="sync")
        # result = graph.invoke({}, config=config, durability="sync")

        while True:
            if "__interrupt__" in result:
                graph_message = result["__interrupt__"][0].value
                print(graph_message)
                user_input = input("请输入：")
                # 恢复执行，把用户输入的内容通过Command(resume=...)传回去
                result = graph.invoke(Command(resume=user_input), config=config, durability="sync")
            else:
                print(result.get("joke"))
                break


if __name__ == '__main__':
    main()