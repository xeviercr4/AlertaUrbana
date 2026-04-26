from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict, total=False):
    task: str
    plan: str
    rules: str
    tickets: List[Dict]
    analysis: List[Dict]
    prioritized: Any
    final: str
    verification: Dict[str, str]
    attempts: int