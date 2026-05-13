from typing import Literal
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from datetime import datetime, timedelta
# 子图调用方式1： 子图作为节点


# 模拟订单数据库
mock_db = {
    "ORD1001": {
        "user_id": "U123",
        "amount": 299.0,
        "status": "completed",
        "create_time": datetime.now() - timedelta(days=8),
    },
    "ORD1002": {
        "user_id": "U456",
        "amount": 899.0,
        "status": "shipped",
        "create_time": datetime.now() - timedelta(days=1),
    },
    "ORD1003": {
        "user_id": "U789",
        "amount": 50.0,
        "status": "cancelled",
        "create_time": datetime.now() - timedelta(days=1),
    }
}

class Orderinfo(BaseModel):
    order_id: str
    user_id: str
    amount: float # 金额
    status: Literal["completed", "shipped", "cancelled"] # 订单状态
    create_time: datetime

# ================子图：订单查询===============================

class OrderqueryState(BaseModel):
    order_id: str
    orderinfo: Orderinfo | None

def query_order(state: OrderqueryState):
    order_id = state.order_id
    orderinfo = mock_db.get(order_id)
    if orderinfo:
        return {"orderinfo": orderinfo}
    return {"orderinfo": None}

# demo中子图只有一个节点，正式项目中子图可以有多个节点的
subgrap_builder = StateGraph(OrderqueryState)
subgrap_builder.add_node("query_order", query_order)
subgrap_builder.add_edge(START, "query_order")
subgrap_builder.add_edge("query_order", END)
orderquery_graph = subgrap_builder.compile()


# =================父图：订单退款===============================
class RefundState(BaseModel):
    # 子图输入/输出字段（必须与子图状态字段名一致）
    order_id: str
    orderinfo: Orderinfo | None

    # 父图字段
    refund_status: Literal["rejected", "refunded"] | None = None
    refund_amount: float | None = None
    reason: str | None = None

def refund_order(state: RefundState):
    order = state.orderinfo
    if not order:
        return {"refund_status": "rejected", "refund_amount": 0.0, "reason": "订单不存在"}
    order_time = order.get("create_time")
    if order_time < datetime.now() - timedelta(days=7):
        return {"refund_status": "rejected", "refund_amount": 0.0, "reason": "超过7天无理由退款时间"}

    if order.get("status") == "cancelled":
        return {"refund_status": "rejected", "refund_amount": 0.0, "reason": "订单已取消"}

    return {"refund_status": "refunded", "refund_amount": order.get("amount"), "reason": "同意退款"}


# 构建退款主图
refund_builder = StateGraph(RefundState)
# 将子图直接注册成父图节点
refund_builder.add_node("query_order", orderquery_graph)
refund_builder.add_node("refund_order", refund_order)

refund_builder.add_edge(START, "query_order")
refund_builder.add_edge("query_order", "refund_order")
refund_builder.add_edge("refund_order", END)
graph = refund_builder.compile()

if __name__ == "__main__":
    test_cases = [
        {"order_id": "ORD1001", },  # 可退款订单
        {"order_id": "ORD1002"},  # 已发货不可退款
        {"order_id": "ORD1003"},  # 已取消订单
        {"order_id": "ORD9999"},  # 不存在的订单
    ]

    for i, inputs in enumerate(test_cases, 1):
        print(f"\n【测试案例 {i}】订单号: {inputs['order_id']}")
        print("-" * 70)

        # 使用 stream
        for chunk in graph.stream(inputs, subgraphs=True):
            print(chunk)