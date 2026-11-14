# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from pathlib import Path
import shutil
D=Path(__file__).resolve().parent
def install(rt):
    folder=Path(rt)/'tools/agent_memory_runtime';shutil.copy2(D/'consumer.py',folder/'listener_weak_consumer.py')
    p=folder/'query_hierarchical_localization.py';s=p.read_text();needle='        selected = select_diverse_callables(ranked, MAX_CALLABLES)';assert s.count(needle)==1
    s=s.replace(needle,needle+'\n        from .listener_weak_consumer import reorder\n        selected = reorder(selected, project, query)')
    needle='        "symbol_id": item.get("id"),';assert s.count(needle)==2
    s=s.replace(needle,'        **({"listener_relation_weak": True} if item.get("listener_relation_weak") else {}),\n'+needle);p.write_text(s)
    p=folder/'query_callable_evidence.py';s=p.read_text().replace('        "source_operation_match": item.get("source_operation_match"),','        **({"listener_relation_weak": True} if item.get("listener_relation_weak") else {}),\n        "source_operation_match": item.get("source_operation_match"),')
    needle='def certainty(primary: dict[str, Any], alternatives: list[dict[str, Any]]) -> str:';s=s.replace(needle,needle+'\n    if primary.get("listener_relation_weak") is True:\n        return "uncertain"');p.write_text(s)
