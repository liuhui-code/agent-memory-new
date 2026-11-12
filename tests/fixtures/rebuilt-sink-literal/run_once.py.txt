import datetime, hashlib, json, os, pathlib, shlex, shutil, sqlite3, subprocess, time
W = pathlib.Path(__file__).resolve().parent
M = json.loads((W / 'manifest.json').read_text())
R = pathlib.Path(M['runtime_repo'])
OUT = W / 'outputs'
assert not OUT.exists(), 'One-pass run already started; do not rerun'
OUT.mkdir()
log = []
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def verify():
    assert sha(W/'manifest.json') == (W/'freeze.json').read_text() and False
# Frozen inputs are checked directly. No runtime calls precede freeze validation.
freeze = json.loads((W / 'freeze.json').read_text())
for rel, expected in freeze['files'].items():
    assert sha(W / rel) == expected, 'Frozen file changed: ' + rel
runtime_before = {str(p.relative_to(R)):sha(p) for p in sorted((R/'tools').rglob('*.py'))}
write_json(OUT/'runtime-python-hashes-before.json', runtime_before)
node = shutil.which('node')
python = shutil.which('python')
assert node and python
write_json(OUT/'environment.json', {'node':node, 'node_version':subprocess.check_output([node,'--version'],text=True).strip(), 'python':python, 'python_version':subprocess.check_output([python,'--version'],text=True).strip(), 'environment_overrides':{'PYTHONDONTWRITEBYTECODE':'1'}, 'cwd':str(W)})
def run(case, stage, argv):
    target = OUT / case['id']; target.mkdir(exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record = {'case_id':case['id'], 'stage':stage, 'argv':argv, 'shell_display':shlex.join(argv), 'cwd':str(W), 'started_at_utc':started, 'timeout_seconds':120, 'attempt':1}
    start = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=W, env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'}, text=True, capture_output=True, timeout=120)
        record.update(returncode=p.returncode, timed_out=False)
        stdout, stderr = p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        record.update(returncode=None, timed_out=True)
        stdout = exc.stdout or ''; stderr = exc.stderr or ''
        if isinstance(stdout, bytes): stdout=stdout.decode(errors='replace')
        if isinstance(stderr, bytes): stderr=stderr.decode(errors='replace')
    record['elapsed_seconds']=round(time.monotonic()-start,6)
    for name, value in [('stdout',stdout),('stderr',stderr)]:
        path=target/(stage+'.'+name+'.txt'); path.write_text(value)
        record[name+'_file']=str(path.relative_to(W)); record[name+'_sha256']=sha(path)
    log.append(record)
    write_json(OUT/'commands.json',log)
    print(case['id'],stage,record['returncode'], flush=True)
    return record
for case in M['cases']:
    source = W / case['source']; project=source.parent
    home = W / 'memory' / case['id']
    args=['--project',str(project),'--memory-home',str(home)]
    cli=[python,'-B',str(R/'tools/agent_memory.py')]
    run(case,'typescript',[node,str(source)])
    run(case,'init',cli+['init']+args)
    run(case,'wiki_index',cli+['wiki-index']+args)
    run(case,'raw',cli+['context']+args+['--query',case['query'],'--json'])
    run(case,'compact',cli+['context']+args+['--query',case['query'],'--compact','--json'])
    database=list(home.glob('projects/*/memory.db'))
    snapshot={'databases':[str(p) for p in database], 'read_only':True}
    if len(database)==1:
        with sqlite3.connect(database[0].as_uri()+'?mode=ro', uri=True) as conn:
            conn.row_factory=sqlite3.Row
            for table in ('code_log_statements','code_log_effects','code_symbols','memory_edges'):
                snapshot[table]=[dict(row) for row in conn.execute('SELECT * FROM '+table+' ORDER BY id')]
    write_json(OUT/case['id']/'sqlite-readonly-snapshot.json', snapshot)
runtime_after = {str(p.relative_to(R)):sha(p) for p in sorted((R/'tools').rglob('*.py'))}
write_json(OUT/'runtime-python-hashes-after.json',runtime_after)
checks={'finished_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'runtime_python_files_unchanged':runtime_before==runtime_after, 'frozen_files_unchanged':all(sha(W/rel)==expected for rel,expected in freeze['files'].items()), 'repo_head_after':subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(), 'repo_status_after':subprocess.check_output(['git','-C',str(R),'status','--porcelain=v1'],text=True).strip(), 'commands_executed':len(log), 'commands_nonzero_or_timeout':[{'case_id':r['case_id'],'stage':r['stage'],'returncode':r['returncode'],'timed_out':r['timed_out']} for r in log if r['returncode'] != 0]}
write_json(OUT/'integrity.json',checks)
print(json.dumps(checks,ensure_ascii=False,indent=2))
