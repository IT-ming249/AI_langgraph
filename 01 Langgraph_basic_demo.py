from typing import Annotated, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from pydantic import BaseModel
from llm import model


class State(BaseModel):
    # Annotated 指的是为数据添加元数据，add_messages保证后续的messages被加进列表，而不是覆盖
    messages: Annotated[List[BaseMessage], add_messages]

def chatbot(state:State):
    print(f"当前对话历史长度: {len(state.messages)}")  # 每次都是1, 所以当前demo中的对话机器人是没有记忆的
    print(f"当前对话历史: {state.messages}")
    messages: AIMessage = model.invoke(state.messages)
    return {"messages": [messages]}

# 创建图
graph_builder = StateGraph(state_schema=State)

# 添加节点
graph_builder.add_node("chatbot", chatbot)
# 添加边
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

# 编译
graph = graph_builder.compile()


if __name__ == '__main__':
    while True:
        user_input = input("User: ")
        if user_input == "exit":
            break
        response = graph.invoke({"messages": [HumanMessage(content=user_input)]})
        print("Bot: ", response["messages"][-1].content)
