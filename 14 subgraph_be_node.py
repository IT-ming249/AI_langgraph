from datetime import datetime, timedelta
from typing import Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel


# Mock order database
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
    },
}


class Orderinfo(BaseModel):
    order_id: str
    user_id: str
    amount: float # 金额
    status: Literal["completed", "shipped", "cancelled"] # 订单状态
    create_time: datetime


class OrderqueryState(BaseModel):
    order_id: str
    orderinfo: Orderinfo | None = None


def query_order(state: OrderqueryState):
    order_id = state.order_id
    orderinfo = mock_db.get(order_id)
    if orderinfo:
        return {"orderinfo": Orderinfo(order_id=order_id, **orderinfo)}
    return {"orderinfo": None}


orderquery_builder = StateGraph(OrderqueryState)
orderquery_builder.add_node("query_order", query_order)
orderquery_builder.add_edge(START, "query_order")
orderquery_builder.add_edge("query_order", END)
orderquery_graph = orderquery_builder.compile()


class RefundState(BaseModel):
    order_id: str
    orderinfo: Orderinfo | None = None
    refund_status: Literal["rejected", "refunded"] | None = None
    refund_amount: float | None = None
    reason: str | None = None


def refund_order(state: RefundState):
    order = state.orderinfo
    if not order:
        return {
            "refund_status": "rejected",
            "refund_amount": 0.0,
            "reason": "订单不存在",
        }

    if order.create_time < datetime.now() - timedelta(days=7):
        return {
            "refund_status": "rejected",
            "refund_amount": 0.0,
            "reason": "超过7天无理由退款",
        }

    if order.status == "cancelled":
        return {
            "refund_status": "rejected",
            "refund_amount": 0.0,
            "reason": "订单已取消",
        }

    return {
        "refund_status": "refunded",
        "refund_amount": order.amount,
        "reason": "已退款",
    }

# 构建退款主图
refund_builder = StateGraph(RefundState)
# 将子图直接注册成父图节点
refund_builder.add_node("query_order", orderquery_graph)
refund_builder.add_node("refund_order", refund_order)
# 定义执行流：START → 子图节点 → 决策节点 → END
refund_builder.add_edge(START, "query_order")
refund_builder.add_edge("query_order", "refund_order")
refund_builder.add_edge("refund_order", END)
graph = refund_builder.compile()


if __name__ == "__main__":
    test_cases = [
        {"order_id": "ORD1001"},
        {"order_id": "ORD1002"},
        {"order_id": "ORD1003"},
        {"order_id": "ORD9999"},
    ]

    for i, inputs in enumerate(test_cases, 1):
        print(f"\nTest case {i}: order_id={inputs['order_id']}")
        print("-" * 70)

        for chunk in graph.stream(inputs, subgraphs=True):
            print(chunk)
