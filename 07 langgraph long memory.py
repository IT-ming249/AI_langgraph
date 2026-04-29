from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore
from llm import model
import uuid
from langchain_core.messages import HumanMessage, SystemMessage


DB_URI = "postgresql://postgres:123456@127.0.0.1:5432/agent_chat_history"

with (
    PostgresSaver.from_conn_string(DB_URI) as checkpointer,
    PostgresStore.from_conn_string(DB_URI) as store,
):
    # 初始化数据库(表),第一次运行的时候运行，只会建表/索引，不会自动创建数据库本身。
    store.setup()
    checkpointer.setup()

    def call_model(
        state: MessagesState,
        config: RunnableConfig,
        *, # *后面的参数必须以关键词形式传入
        store: BaseStore,
    ):
        user_id = config["configurable"]["user_id"]
        # 定义命名空间
        namespace = (user_id, "memories")
        # 在命名空间中搜索与当前消息最相似的记忆
        memories = store.search(namespace, query=str(state["messages"][-1].content))
        info = "\n".join([d.value["data"] for d in memories])
        system_msg = f"你是一个得力的聊天助手. 用户信息为: {info}"

        last_message = state["messages"][-1]
        if "记住" in last_message.content:
            memory = last_message.content
            store.put(namespace, str(uuid.uuid4()), {"data": memory})

        response = model.invoke([SystemMessage(content=system_msg)] + state["messages"])
        return {"messages": response}

    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_edge(START, "call_model")

    graph = builder.compile(
        checkpointer=checkpointer,
        store=store,
    )

    config = {
        "configurable": {
            "thread_id": "1",
            "user_id": "1",
        }
    }
    graph.invoke(
        {"messages": [HumanMessage(content="你好！记住我的名字叫：mmg")]},
        config
    )

    # 开启新的对话，同一用户
    config = {
        "configurable": {
            "thread_id": "2",
            "user_id": "1",
        }
    }

    response = graph.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？")]},
        config
    )
    for message in response["messages"]:
        message.pretty_print()
