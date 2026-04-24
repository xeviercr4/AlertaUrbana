from typing import TypedDict, List, Dict

class AgentState(TypedDict, total=False):
    task: str
    plan: str
    rules: str
    tickets: List[Dict]
    analysis: List[Dict]
    prioritized: str
    final: str