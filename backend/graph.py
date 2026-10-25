"""Safe, deterministic LangGraph workflow scaffold. No external side effects."""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class JobState(TypedDict, total=False):
    job_id: str
    campaign: str
    source_url: str
    status: str
    notes: list[str]
    approved: bool

def inspect(state: JobState) -> JobState:
    return {"status": "review_required", "notes": ["Source rights and campaign rules must be verified manually.", "No publishing integration configured."]}

def route(state: JobState) -> str:
    return "ready" if state.get("approved", False) else "hold"

def ready(state: JobState) -> JobState:
    return {"status": "approved_for_future_processing"}

def hold(state: JobState) -> JobState:
    return {"status": "awaiting_approval"}

builder = StateGraph(JobState)
builder.add_node("inspect", inspect)
builder.add_node("ready", ready)
builder.add_node("hold", hold)
builder.add_edge(START, "inspect")
builder.add_conditional_edges("inspect", route, {"ready": "ready", "hold": "hold"})
builder.add_edge("ready", END)
builder.add_edge("hold", END)
graph = builder.compile()
