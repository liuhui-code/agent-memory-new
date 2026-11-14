# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Creates experimental files only in an explicitly disposable runtime directory."""
from pathlib import Path
import shutil,sys
D=Path(__file__).resolve().parent
ROOT=D.parents[2]

def install(target):
    target=Path(target)
    if not (target/'EXPERIMENTAL_DISPOSABLE_RUNTIME').exists():raise ValueError('not disposable')
    rt=target/'tools/agent_memory_runtime'
    models=rt/'semantic_models.py';s=models.read_text()
    s=s.replace('SEMANTIC_SCHEMA = "semantic-index/v1"','SEMANTIC_SCHEMA = "semantic-index/listener-experiment-v1"')
    start=s.index('class SemanticMechanism:');end=s.index('\n\n@dataclass\nclass SemanticBatch:',start)
    segment=s[start:end].replace('    def to_dict(self)', '    typed_invocation_witness: dict[str, Any] | None = None\n\n    def to_dict(self)')
    segment=segment.replace('        return asdict(self)','        value = asdict(self)\n        if value["typed_invocation_witness"] is None:\n            value.pop("typed_invocation_witness")\n        return value')
    s=s[:start]+segment+s[end:]
    s=s.replace('        if not isinstance(value, dict) or value.get("schema_version") != SEMANTIC_SCHEMA:', '        if isinstance(value, dict) and value.get("schema_version") == "semantic-index/v1":\n            value = {**value, "schema_version": SEMANTIC_SCHEMA}\n        if not isinstance(value, dict) or value.get("schema_version") != SEMANTIC_SCHEMA:')
    s=s.replace('    if mechanism.kind not in MECHANISM_KINDS:', '    if mechanism.typed_invocation_witness is not None:\n        from .listener_experiment_support import validate\n        validate(mechanism.typed_invocation_witness, entity)\n    if mechanism.kind not in MECHANISM_KINDS:')
    s=s.replace('        self.capabilities = sorted(set(self.capabilities))','        for mechanism in self.mechanisms:\n            witness = mechanism.typed_invocation_witness\n            if witness is not None and witness["source"]["source_digest"] != self.source_digests.get(witness["source"]["file_path"]):\n                raise ValueError("experiment witness snapshot mismatch")\n        self.capabilities = sorted(set(self.capabilities))')
    models.write_text(s)
    path=rt/'semantic_ecma.py';s=path.read_text().replace('adapter_version=adapter.adapter_version,','adapter_version=adapter.adapter_version + "+listener-experiment",')
    s=s.replace('    gaps.extend(operation_gaps)','    from .listener_experiment_support import attach\n    mechanisms = attach(text, rel_path, entities, mechanisms)\n    gaps.extend(operation_gaps)');path.write_text(s)
    shutil.copy2(D/'overlay_support.py',rt/'listener_experiment_support.py')
    s=(ROOT/'docs/evidence/listener-producer-feasibility/prototype.py').read_text()
    s=s.replace("sys.path.insert(0, str(D.parents[2]))",'')
    (rt/'listener_experiment_prototype.py').write_text(s)

if __name__=='__main__':install(sys.argv[1])
