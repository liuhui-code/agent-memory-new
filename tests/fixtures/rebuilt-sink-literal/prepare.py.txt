import datetime, hashlib, json, pathlib, subprocess
W = pathlib.Path(__file__).resolve().parent
R = W.parent / 'agent-memory-new'
assert not (W / 'manifest.json').exists(), 'Already frozen'
common_head = """const Logger = {
  info(message: string): void {
    process.stdout.write(message + '\\n')
  }
}

export class CatalogService {
"""
common_tail = """}

new CatalogService().run()
"""
specs = [
    ('fixed_sink', 'Fixed sink message and ordinary caller business argument', """  refresh(bucket: string): void {
    void bucket
    Logger.info('catalog refreshed')
  }

  run(): void {
    this.refresh('east-region')
  }
""", 'catalog refreshed', 'catalog refreshed', 'catalog refreshed'),
    ('template_sink', 'Sink template with ordinary caller business argument', """  refresh(bucket: string): void {
    Logger.info(`catalog refreshed: ${bucket}`)
  }

  run(): void {
    this.refresh('east-region')
  }
""", 'catalog refreshed: east-region', 'catalog refreshed: ${bucket}', 'catalog refreshed: ${bucket}'),
    ('first_message_parameter', 'First parameter reaches sink; second is ordinary business argument', """  refresh(message: string, bucket: string): void {
    void bucket
    Logger.info(message)
  }

  run(): void {
    this.refresh('catalog refreshed', 'east-region')
  }
""", 'catalog refreshed', '{message}', 'catalog refreshed'),
    ('second_message_parameter', 'Second parameter reaches sink; first is ordinary business argument', """  refresh(bucket: string, message: string): void {
    void bucket
    Logger.info(message)
  }

  run(): void {
    this.refresh('east-region', 'catalog refreshed')
  }
""", 'catalog refreshed', '{message}', 'catalog refreshed'),
    ('no_literal_caller', 'No literal in wrapper call, fixed sink control', """  refresh(bucket: string): void {
    void bucket
    Logger.info('catalog refreshed')
  }

  run(): void {
    const bucket: string = 'east-region'
    this.refresh(bucket)
  }
""", 'catalog refreshed', 'catalog refreshed', 'catalog refreshed'),
]
query = 'catalog refreshed east-region CatalogService run refresh Logger.info'
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git', '-C', str(R), *args], text=True).strip()
cases = []
for case_id, purpose, body, output, direct, effect in specs:
    p = W / 'projects' / case_id
    p.mkdir(parents=True)
    content = common_head + body + common_tail
    (p / 'CatalogService.ts').write_text(content)
    lines = content.splitlines()
    ranges = {}
    for name in ('refresh', 'run'):
        start = next(i for i, line in enumerate(lines, 1) if line.startswith('  ' + name + '('))
        end = next(i for i, line in enumerate(lines[start:], start + 1) if line == '  }')
        ranges[name] = {'start_line': start, 'end_line': end}
    cases.append({'id':case_id, 'purpose':purpose, 'source':'projects/' + case_id + '/CatalogService.ts', 'source_sha256':sha(content.encode()), 'query':query, 'query_sha256':sha(query.encode()), 'expected_stdout':output + '\n', 'expected_direct_static_template':direct, 'expected_effect_static_template':effect, 'acceptable_effect_templates': [effect, output] if effect != output else [effect], 'expected_static_call_path':['run','refresh','logger.info'], 'required_source_ranges':ranges})
manifest = {
 'schema_version':'independent-sink-development/v1',
 'classification':'development',
 'source_family':'new synthetic project-neutral TypeScript fixtures',
 'independence_basis':'New authored minimal projects outside restored repository. No consumed holdout, historical fixture, or historical result loaded. Five cases are independent workspaces testing the same known defect family, not independent external populations.',
 'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'runtime_repo':str(R), 'runtime_head':git('rev-parse','HEAD'), 'baseline_runtime_commit':'25ae6ba',
 'runtime_tools_tree':git('rev-parse','HEAD:tools'), 'baseline_tools_tree':git('rev-parse','25ae6ba:tools'),
 'repo_status_before':git('status','--porcelain=v1'),
 'query_rationale':'Frozen neutral token query includes actual sink event text, actual business argument, and caller/wrapper names. It does not claim east-region alone was a runtime log.',
 'run_policy':{'direct_typescript_executions_per_case':1, 'public_commands_per_case':{'init':1,'wiki-index':1,'context_raw':1,'context_compact':1}, 'timeout_seconds_per_command':120, 'retry_allowed':False, 'source_query_expectation_edits_after_freeze':False, 'runtime_edits':False, 'full_231_run':False, 'network_or_space_or_library':False},
 'interpretation':{'message_check':'Compare direct sink and wrapped public message fields separately with source-derived static contract and direct TypeScript output. Preserving symbolic template is valid; resolving simple interpolation fully is optional.', 'call_path_check':'Require static call path run -> refresh -> logger.info separately from message correctness. A static edge is not proof of arbitrary runtime execution.', 'sourcebody_check':'Verify source ranges/excerpts against exact frozen source, and report coverage of refresh and run method bodies independently of message/path.', 'promotion_eligible':False, 'historical_commit_restoration_claim':False, 'fresh_231_comparison':'Not run or inferred; parent supplied 157/74 baseline is background only.'},
 'cases':cases}
(W / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'cases':len(cases),'manifest_sha256':sha((W/'manifest.json').read_bytes()),'head':manifest['runtime_head'],'runtime_tools_unchanged_from_baseline':manifest['runtime_tools_tree']==manifest['baseline_tools_tree']}, indent=2))
