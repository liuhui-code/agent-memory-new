# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Fresh unit cohorts, not replay of frozen before or original evaluation."""
from copy import copy, deepcopy
import json
import tempfile
import unittest
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tools.agent_memory_runtime.storage import connect
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_validation_field_selection import (
    ValidationContext, bind_validation_field_context, validation_field_receipt,
    compact_validation_field, enrich_validation_field, accounting_validation_field)

Q = 'Locate the invoice validation-stop and dispatch source.'
SOURCE = '''export class InvoiceEntry {
  customerCode: string = '';
  submitDraft(): void {
    if (this.customerCode.trim().length === 0) {
      promptAction.showToast({ message: 'Missing value' });
      return;
    }
    this.dispatchPayload(this.customerCode);
  }
  dispatchPayload(value: string): void {}
}
'''
OTHER = SOURCE.replace('InvoiceEntry', 'EntryReview').replace('submitDraft', 'submitInvoice')
NEUTRAL = 'export class InvoiceNotes {\n  describe(): string { return "notes"; }\n}\n'


def ordinary(project):
    pools = []
    def capture(_project, _query, baseline, pool, collection=None):
        pools.append(deepcopy(pool)); return baseline
    with patch('tools.agent_memory_runtime.query_validation_field_selection.bind_validation_field_context', side_effect=capture):
        raw = build_context_facade(project).execute(Q)
    assert len(pools) == 1
    return deepcopy(dict(raw)), compact_context(dict(raw)), pools[0]


def empty_collection(project, pool):
    from tools.agent_memory_runtime.query_collect import CollectedMatches
    from tools.agent_memory_runtime.query_language import positive_retrieval_query
    from tools.agent_memory_runtime.query_validation_no_logs import capture_validation_no_logs
    collection = CollectedMatches({'wiki_matches': deepcopy(pool), 'code_log_matches': []}, {})
    capture_validation_no_logs(project, Q, positive_retrieval_query(Q), collection, [], [])
    return collection


class ValidationSelection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = prepare(self.tmp.name, sources={'Entry.ts': SOURCE, 'Review.ts': OTHER, 'Notes.ts': NEUTRAL})
        self.base, self.compact, self.pool = ordinary(self.project)
        self.collection = empty_collection(self.project, self.pool)
    def tearDown(self): self.tmp.cleanup()
    def bind(self, base=None, pool=None):
        return bind_validation_field_context(self.project, Q, self.base if base is None else base,
                                             self.pool if pool is None else pool, self.collection)
    def test_missing_capture_and_unissued_collection_fallback(self):
        from tools.agent_memory_runtime.query_collect import CollectedMatches
        for collection in (None, CollectedMatches({}, {})):
            self.assertIs(bind_validation_field_context(self.project, Q, self.base, self.pool, collection), self.base)
    def test_cross_pass_collection_and_capture_replacement_rejected(self):
        from tools.agent_memory_runtime.query_validation_field_selection import binding
        from tools.agent_memory_runtime.query_validation_no_logs import validation_no_logs
        other = empty_collection(self.project, self.pool)
        for replacement in ('collection', 'capture', 'both'):
            with self.subTest(replacement=replacement):
                bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
                if replacement in ('collection', 'both'):
                    bound._collection = other
                if replacement in ('capture', 'both'):
                    bound._no_logs = validation_no_logs(self.project, Q, other)
                bound._binding = binding(bound)
                self.assertIsNone(validation_field_receipt(bound))
    def test_collection_mutation_after_issuance_rejected(self):
        from tools.agent_memory_runtime.query_validation_field_selection import binding
        bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
        bound._collection.matches['changed_after_issuance'] = []
        bound._binding = binding(bound)
        self.assertIsNone(validation_field_receipt(bound))
    def test_positive_complete_view_and_raw_unchanged(self):
        bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
        self.assertEqual(dict(bound), self.base)
        out = compact_validation_field(bound, self.compact)
        self.assertIsNot(out, self.compact)
        self.assertEqual(restore_whitelist(out, self.compact), self.compact)
        self.assertEqual({a['symbol'] for a in out['query_handoff']['code_anchors']}, {'submitDraft', 'submitInvoice'})
        self.assertTrue(all(a['source_excerpts'][0]['content'].endswith('  }') for a in out['query_handoff']['code_anchors']))
        self.assertIsNone(out['query_handoff']['callable_evidence']['primary'])
        self.assertLessEqual(out['output_budget']['estimated_tokens'], 1500)
    def test_scope_uses_one_explicit_read_snapshot(self):
        from tools.agent_memory_runtime.query_validation_field_scope import connect as real_connect
        statements = []
        def traced(project):
            db = real_connect(project)
            db.set_trace_callback(statements.append)
            return db
        with patch('tools.agent_memory_runtime.query_validation_field_scope.connect', side_effect=traced):
            bound = self.bind()
        self.assertIsInstance(bound, ValidationContext)
        first_select = next(i for i, sql in enumerate(statements) if sql.startswith('SELECT'))
        begins = [i for i, sql in enumerate(statements) if sql == 'BEGIN']
        self.assertEqual(len(begins), 1)
        self.assertLess(begins[0], first_select)
        self.assertFalse(any(sql in ('COMMIT', 'ROLLBACK') for sql in statements[first_select:-1]))
    def test_three_real_positive_roots_and_four_atomic_fallback(self):
        for count in (3, 4):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                sources = {name+'.ts': SOURCE.replace('InvoiceEntry', 'Invoice'+name)
                           for name in ('North', 'South', 'West', 'East')[:count]}
                project = prepare(directory, sources=sources)
                base, compact, pool = ordinary(project)
                self.assertEqual(sum(r.get('symbol') == 'submitDraft' for r in pool), count)
                bound = bind_validation_field_context(project, Q, base, pool, empty_collection(project, pool))
                if count == 4:
                    self.assertIs(bound, base)
                else:
                    self.assertIsInstance(bound, ValidationContext)
                    result = compact_validation_field(bound, compact)
                    self.assertIsNot(result, compact)
                    self.assertEqual(len(result['query_handoff']['code_anchors']), 3)
                    self.assertEqual(restore_whitelist(result, compact), compact)
    def test_real_full_body_budget_overflow_is_atomic(self):
        from tools.agent_memory_runtime.context_record_loop_transaction import valid_anchors
        from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens
        with tempfile.TemporaryDirectory() as directory:
            # Legal escaped literal; source limits stay valid, JSON serialization costs exceed budget.
            large = SOURCE.replace('Missing value', '\\\\'*280)
            sources = {name+'.ts': large.replace('InvoiceEntry', 'Invoice'+name)
                       for name in ('North', 'South', 'West')}
            project = prepare(directory, sources=sources)
            base, compact, pool = ordinary(project)
            self.assertEqual(sum(r.get('symbol') == 'submitDraft' for r in pool), 3)
            bound = bind_validation_field_context(project, Q, base, pool, empty_collection(project, pool))
            self.assertIsInstance(bound, ValidationContext)
            self.assertTrue(valid_anchors(bound._anchors))
            observed = []
            def estimate(payload):
                result = estimate_payload_tokens(payload); observed.append(result); return result
            with patch('tools.agent_memory_runtime.context_record_loop_transaction.estimate_payload_tokens', side_effect=estimate):
                result = compact_validation_field(bound, compact)
            self.assertTrue(any(n > 1500 for n in observed), observed)
            self.assertIs(result, compact)
            self.assertEqual(len(bound._anchors), 3)
    def test_missing_root_whole_fallback(self):
        removed = [r for r in self.pool if r.get('symbol') != 'submitInvoice']
        self.assertLess(len(removed), len(self.pool)); self.assertIs(self.bind(pool=removed), self.base)
    def test_db_only_owner_allowed_not_new_method(self):
        removed = [r for r in self.pool if r.get('symbol') not in {'InvoiceEntry', 'EntryReview'}]
        self.assertIsInstance(self.bind(pool=removed), ValidationContext)
    def test_other_project_baseline_is_not_authorized(self):
        for key, value in [('project_id', 'other-project'), ('project_path', str(self.project.root/'other'))]:
            base = deepcopy(self.base); base[key] = value
            self.assertIs(self.bind(base=base), base)
    def test_identity_mutation(self):
        for key, value in [('id', True), ('symbol_key', ''), ('start_line', 1), ('owner_name', 'Wrong'),
                           ('index_generation', True), ('source_digest', '0'*64), ('signature', 'fake')]:
            pool = deepcopy(self.pool)
            next(r for r in pool if r.get('symbol') == 'submitDraft')[key] = value
            self.assertIs(self.bind(pool=pool), self.base, key)
    def test_receipt_copy_forgery_and_mutation(self):
        bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
        fake = ValidationContext(bound); fake.__dict__.update(bound.__dict__)
        for item in (dict(bound), copy(bound), deepcopy(bound), json.loads(json.dumps(bound)), fake):
            self.assertIsNone(validation_field_receipt(item))
        bound._pool[0]['score'] = -100
        self.assertIsNone(validation_field_receipt(bound))
        bound = self.bind(); bound['query_audit']['changed'] = True
        self.assertIsNone(validation_field_receipt(bound))
    def test_recomputed_binding_cannot_replace_issuance_seal(self):
        from tools.agent_memory_runtime.query_validation_field_selection import binding
        for mutation in ('query', 'pool', 'public'):
            with self.subTest(mutation=mutation):
                bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
                if mutation == 'query':
                    bound['query'] = 'Locate the customer code validation-stop and dispatch source.'
                elif mutation == 'pool':
                    next(r for r in bound._pool if r['file_path'] == 'Notes.ts')['score'] = -100
                else:
                    bound['query_audit']['tampered'] = True
                bound._binding = binding(bound)
                self.assertIsNone(validation_field_receipt(bound))
    def test_db_generation_and_nonmatching_source_drift(self):
        bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
        with connect(self.project) as db:
            db.execute('UPDATE code_index_state SET generation=generation+1 WHERE project_id=?', (self.project.project_id,))
        self.assertIsNone(validation_field_receipt(bound))
        with connect(self.project) as db:
            db.execute('UPDATE code_index_state SET generation=generation-1 WHERE project_id=?', (self.project.project_id,))
        bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
        (self.project.root/'Notes.ts').write_text(NEUTRAL+'\n')
        self.assertIsNone(validation_field_receipt(bound))
    def test_unrecalled_alias_blocks(self):
        with connect(self.project) as db:
            row = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='submitDraft'").fetchone())
            row.pop('id'); row['file_path'] = 'Hidden.ts'
            db.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')', list(row.values()))
        self.assertIs(self.bind(), self.base)
    def test_source_missing_overlimit_and_unsafe_pool(self):
        path = self.project.root/'Notes.ts'
        path.write_text('x'*(2*1024*1024+1))
        self.assertIs(self.bind(), self.base)
        path.unlink()
        self.assertIs(self.bind(), self.base)
        for unsafe in ('../Entry.ts', '/Entry.ts', './Entry.ts'):
            pool = deepcopy(self.pool); pool[0]['file_path'] = unsafe
            self.assertIs(self.bind(pool=pool), self.base)
        pool = deepcopy(self.pool)
        pool.extend(dict(kind='file', file_path='extra'+str(i)+'.ts') for i in range(13))
        self.assertIs(self.bind(pool=pool), self.base)
    def test_db_missing_owner_and_file_witness(self):
        with connect(self.project) as db:
            db.execute("DELETE FROM code_symbols WHERE symbol='InvoiceEntry'")
        pool = [r for r in self.pool if r.get('symbol') != 'InvoiceEntry']
        self.assertIs(self.bind(pool=pool), self.base)
    def test_unknown_scope_is_not_absent(self):
        with patch('tools.agent_memory_runtime.validation_field_source.parse_validation_field_file', return_value=None):
            self.assertIs(self.bind(), self.base)
    def test_protection_no_log_permission(self):
        for key in ('identity_match', 'graph_neighbor', 'graph_relation', 'log_identity_match'):
            pool = deepcopy(self.pool); pool[0][key] = True
            self.assertIs(self.bind(pool=pool), self.base)
        base = deepcopy(self.base); base['query_handoff']['log_anchors'] = [{'message_template': 'unrelated'}]
        self.assertIs(self.bind(base=base), base)
        base = deepcopy(self.base); base['query_audit']['candidate_recall']['tables']['code_log_statements']['candidate_count'] = 1
        self.assertIs(self.bind(base=base), base)
        base = deepcopy(self.base); base['query_handoff']['path_context']['activated'] = True
        self.assertIs(self.bind(base=base), base)
    def test_full_baseline_and_budget_bound(self):
        bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
        wrong = deepcopy(self.compact); wrong['output_budget']['target_tokens'] = 1
        self.assertIs(compact_validation_field(bound, wrong), wrong)
        wrong = deepcopy(self.compact); wrong['query_handoff']['other'] = True
        self.assertIs(compact_validation_field(bound, wrong), wrong)
    def test_enrich_issues_new_identity_and_accounting(self):
        bound = self.bind(); self.assertIsInstance(bound, ValidationContext)
        enriched = enrich_validation_field(bound, Q, self.base['query_handoff']['path_context'], self.base['source_freshness'])
        self.assertIsInstance(enriched, ValidationContext)
        self.assertIsNot(enriched, bound); self.assertIsNotNone(validation_field_receipt(enriched))
        self.assertNotIsInstance(enrich_validation_field(bound, Q+'!', {}, self.base['source_freshness']), ValidationContext)
        view = accounting_validation_field(enriched)
        self.assertEqual({r['symbol'] for r in view['wiki_matches']}, {'submitDraft', 'submitInvoice'})
        self.assertEqual(dict(bound), self.base)

if __name__ == '__main__': unittest.main()
