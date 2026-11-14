# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from pathlib import Path
import shutil,sys
D=Path(__file__).resolve().parent;ROOT=D.parents[2]
def install(target):
    target=Path(target);assert(target/'EXPERIMENTAL_DISPOSABLE_RUNTIME').exists()
    rt=target/'tools/agent_memory_runtime';p=rt/'semantic_models.py';s=p.read_text()
    s=s.replace('SEMANTIC_SCHEMA = "semantic-index/v1"','SEMANTIC_SCHEMA = "semantic-index/listener-experiment-v2"')
    s=s.replace('    schema_version: str = SEMANTIC_SCHEMA','    schema_version: str = SEMANTIC_SCHEMA\n    typed_invocation_witnesses: list[dict[str, Any]] = field(default_factory=list)')
    s=s.replace('        self.capabilities = sorted(set(self.capabilities))','        from .listener_experiment_support import validate\n        for witness in self.typed_invocation_witnesses:\n            entity = entities_by_key.get(witness.get("source", {}).get("symbol_key"))\n            if entity is None:\n                raise ValueError("unknown witness entity")\n            validate(witness, entity, self.source_digests)\n        self.capabilities = sorted(set(self.capabilities))')
    s=s.replace('            "gaps": self.gaps,','            "gaps": self.gaps,\n            "typed_invocation_witnesses": self.typed_invocation_witnesses,')
    s=s.replace('        if not isinstance(value, dict) or value.get("schema_version") != SEMANTIC_SCHEMA:', '        if isinstance(value, dict) and value.get("schema_version") == "semantic-index/v1":\n            from .listener_experiment_support import legacy_guard\n            legacy_guard(value)\n            value = {**value, "schema_version": SEMANTIC_SCHEMA}\n        if not isinstance(value, dict) or value.get("schema_version") != SEMANTIC_SCHEMA:')
    s=s.replace('            gaps=require_object_list(value.get("gaps"), "gaps"),','            gaps=require_object_list(value.get("gaps"), "gaps"),\n            typed_invocation_witnesses=optional_object_list(value.get("typed_invocation_witnesses"), "typed_invocation_witnesses"),');p.write_text(s)
    p=rt/'semantic_ecma.py';s=p.read_text().replace('    gaps: list[dict[str, str]]\n','    gaps: list[dict[str, str]]\n    typed_invocation_witnesses: list[dict[str, Any]]\n')
    s=s.replace('adapter_version=adapter.adapter_version,','adapter_version=adapter.adapter_version + "+listener-experiment-v2",')
    s=s.replace('        mechanisms=[mechanism for item in parsed for mechanism in item.mechanisms],','        mechanisms=[mechanism for item in parsed for mechanism in item.mechanisms],\n        typed_invocation_witnesses=[w for item in parsed for w in item.typed_invocation_witnesses],')
    s=s.replace('    gaps.extend(operation_gaps)','    from .listener_experiment_support import extract\n    witnesses = extract(text, rel_path, entities, digest)\n    gaps.extend(operation_gaps)')
    s=s.replace('        mechanisms=mechanisms,','        mechanisms=mechanisms,\n        typed_invocation_witnesses=witnesses,');p.write_text(s)
    p=rt/'semantic_index.py';s=p.read_text();needle='    paths = sorted(batch.source_digests)';assert s.count(needle)==1
    s=s.replace(needle,'    from .listener_experiment_support import pack\n    if "typed_invocation_witnesses" not in {r[1] for r in conn.execute("PRAGMA table_info(code_symbols)")}:\n        conn.execute("ALTER TABLE code_symbols ADD COLUMN typed_invocation_witnesses TEXT")\n'+needle)
    needle='    return enriched';assert s.count(needle)==1
    s=s.replace(needle,'        witnesses = [w for w in batch.typed_invocation_witnesses if w["source"]["symbol_key"] == entity.key]\n        conn.execute("UPDATE code_symbols SET typed_invocation_witnesses=? WHERE project_id=? AND id=?", (pack(mechanism_evidence, witnesses), project.project_id, int(target["id"])))\n'+needle);p.write_text(s)
    shutil.copy2(D/'support.py',rt/'listener_experiment_support.py')
    text=(ROOT/'docs/evidence/listener-producer-feasibility/prototype.py').read_text().replace("sys.path.insert(0, str(D.parents[2]))",'').replace('from tools.agent_memory_runtime.','from .')
    (rt/'listener_experiment_prototype.py').write_text(text)
if __name__=='__main__':install(sys.argv[1])
