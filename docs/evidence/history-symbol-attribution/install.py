# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from pathlib import Path
import shutil
D=Path(__file__).resolve().parent
def install(target):
    rt=Path(target)/'tools/agent_memory_runtime';assert(Path(target)/'EXPERIMENTAL_DISPOSABLE_RUNTIME').exists();shutil.copy2(D/'candidate.py',rt/'history_symbol_experiment.py')
    p=rt/'query_hierarchical_localization.py';s=p.read_text();s=s.replace('rank_callables(candidates, ranking_query, use_direct_score)','rank_callables(candidates, ranking_query, use_direct_score, query)').replace('rank_callables([*candidates, *owners], ranking_query, use_direct_score)','rank_callables([*candidates, *owners], ranking_query, use_direct_score, query)')
    s=s.replace('    use_direct_score: bool = True,\n','    use_direct_score: bool = True,\n    identity_query: str | None = None,\n')
    old='            [("exact_symbol", str(item.get("symbol") or ""), 12.0)],';assert s.count(old)==1
    s=s.replace(old,'            [] if history_only(str(item.get("symbol") or ""), identity_query) else [("exact_symbol", str(item.get("symbol") or ""), 12.0)],')
    s=s.replace('    terms = query_tokens(query)\n','    from .history_symbol_experiment import history_only\n    terms = query_tokens(query)\n');p.write_text(s)
