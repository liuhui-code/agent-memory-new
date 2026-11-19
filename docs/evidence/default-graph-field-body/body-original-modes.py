exec(open('/tmp/run-body-controls-v2.py').read().split('for n,c in')[0].replace("recall-audit13/body-controls-v2","recall-audit13/body-original-modes"))
q=json.loads((b/'recall-audit13/default.json').read_text())['query']
for mode,flags in [('default',['--compact']),('preserve1500',['--compact','--compact-token-budget','1500','--preserve-selected-source-anchors']),('plain2000',['--compact','--compact-token-budget','2000']),('preserve2000',['--compact','--compact-token-budget','2000','--preserve-selected-source-anchors']),('raw',[])]:
 for arm in ['before','after']:
  tag=f'{mode}-{arm}';home=o/(tag+'-memory');shutil.copytree(b/'original13/memory',home)
  cmd=([sys.executable,'-c',runner,str(b/'repo')] if arm=='before' else [sys.executable,str(b/'repo/tools/agent_memory.py')])+['context','--query',q,'--project',str(b/'original13/source'),'--memory-home',str(home),'--json',*flags]
  p=subprocess.run(cmd,capture_output=True,text=True);(o/(tag+'.json')).write_text(p.stdout);(o/(tag+'.stderr')).write_text(p.stderr);results.append(dict(tag=tag,cmd=cmd,rc=p.returncode))
(o/'commands.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print([(x['tag'],x['rc'])for x in results])
