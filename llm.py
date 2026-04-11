from langchain_openai import ChatOpenAI
from constant import DASHSCOPE_API_KEY

api_key = DASHSCOPE_API_KEY
model = ChatOpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=api_key,
    model="qwen3-max"
)