from pathlib import Path
import shutil,json,subprocess,sqlite3
O=Path(__file__).resolve().parent;R=O.parent/'repo'
rows=[]
for label in ['space','ls','ps']:
 src=O/label; home=O/(label+'-upgrade-memory');shutil.copytree(O/(label+'-memory'),home)
 db=next(home.rglob('memory.db'))
 def check():
  with sqlite3.connect(db) as c:
   return c.execute("select symbol,start_line,end_line,source_digest,index_generation from code_symbols where symbol='save'").fetchone()
 before=check();tail=['--project',str(src),'--memory-home',str(home)];cli=['python','-B',str(R/'tools/agent_memory.py')]
 p=subprocess.run(cli+['learn-path','--path','.','--json']+tail,capture_output=True,text=True);assert p.returncode==0,p.stderr
 (O/(label+'-upgrade-learn.json')).write_text(p.stdout)
 p=subprocess.run(cli+['context','--query','Locate DocumentStore.save source.','--compact','--json']+tail,capture_output=True,text=True);assert p.returncode==0,p.stderr
 (O/(label+'-upgrade-compact.json')).write_text(p.stdout)
 after=check(); assert after[1:3]==(3,5);assert before[3]==after[3];rows.append(dict(label=label,before=before,after=after))
(O/'upgrade-summary.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
