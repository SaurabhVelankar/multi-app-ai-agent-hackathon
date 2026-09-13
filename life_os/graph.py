"""Life OS LangGraph — wires all nodes. Agent 2 stubs are swappable imports."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from life_os.state import LifeState
from life_os.agents.intake import intake_node
from life_os.agents.priority import priority_node
from life_os.agents.planner import planner_node
from life_os.agents.critic import critic_node

# Agent 2 nodes — imported from connectors when live; stubs until then
try:
    from life_os.agents.scheduler import scheduler_node
except ImportError:
    def scheduler_node(state: LifeState) -> dict:
        return {}  # pass-through stub

try:
    from life_os.agents.executor import executor_node
except ImportError:
    def executor_node(state: LifeState) -> dict:
        return {}  # pass-through stub

try:
    from life_os.agents.auditor import auditor_node
except ImportError:
    def auditor_node(state: LifeState) -> dict:
        return {"audit_ref": "stub"}  # pass-through stub


def _route_after_critic(state: LifeState) -> str:
    if state.get("needs_approval"):
        return "hitl_interrupt"
    if state.get("status") == "abort":
        return "auditor"
    return "auditor"


def _hitl_interrupt_node(state: LifeState) -> dict:
    """Pause point — graph stays here until /approve is called."""
    return {}


def build_graph() -> StateGraph:
    builder = StateGraph(LifeState)

    builder.add_node("intake", intake_node)
    builder.add_node("priority", priority_node)
    builder.add_node("planner", planner_node)
    builder.add_node("scheduler", scheduler_node)
    builder.add_node("executor", executor_node)
    builder.add_node("critic", critic_node)
    builder.add_node("hitl_interrupt", _hitl_interrupt_node)
    builder.add_node("auditor", auditor_node)

    builder.set_entry_point("intake")
    builder.add_edge("intake", "priority")
    builder.add_edge("priority", "planner")
    builder.add_edge("planner", "scheduler")
    builder.add_edge("scheduler", "executor")
    builder.add_edge("executor", "critic")

    builder.add_conditional_edges(
        "critic",
        _route_after_critic,
        {"hitl_interrupt": "hitl_interrupt", "auditor": "auditor"},
    )

    # After HITL approval resumes from hitl_interrupt → auditor
    builder.add_edge("hitl_interrupt", "auditor")
    builder.add_edge("auditor", END)

    checkpointer = MemorySaver()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["hitl_interrupt"],  # pause before HITL node
    )


# Singleton graph instance
graph = build_graph()
