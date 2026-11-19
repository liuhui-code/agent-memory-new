"""Read-only request qualification experiment; no serving authority."""
import re,json
from pathlib import Path
O=Path(__file__).resolve().parent

def request(query):
 if not isinstance(query,str)or len(query)>300 or any(x in query for x in ['"',"'",'`','/','\\',':','：','\n','\r']):return False
 english=re.fullmatch(r'(?:(?P<context>[^.!?]{1,160})\.\s+)?(?:find|locate|return) (?:the )?reactive aggregation (?:owner|source)\.?',query.strip(),re.I|re.ASCII)
 if english:
  prefix=english['context']or''
  return re.search(r'\b(?:find|locate|return|show|only|except|rather|instead|compare|within|exclude|include|must)\b',prefix,re.I)is None
 chinese=re.fullmatch(r'(?:(?P<context>[\u4e00-\u9fff]{1,100})，)?(?:请)?(?:定位|查找|返回)状态聚合源码(?:，不要返回数据实体)?[。.]?',query.strip())
 if chinese:
  prefix=chinese['context']or''
  return not any(x in prefix for x in ['只','仅','不要','别','而','相比','比较','对比','限定','模块','组件','文件','方法','代码','实现','定位','查找','返回','必须','范围'])
 return False

if __name__=='__main__':
 controls=['Do not locate the reactive aggregation owner.','Compare the reactive aggregation owner.','Only within Billing. Locate the reactive aggregation owner.','Return the UI. Locate the reactive aggregation owner.','只在付款模块定位，请定位状态聚合源码，不要返回数据实体。','请不要定位状态聚合源码。','比较状态聚合源码。','请返回工具栏，请定位状态聚合源码。','不是状态聚合而是页面，请定位状态聚合源码。','"Locate the reactive aggregation owner."']
 result={q:request(q)for q in controls};assert not any(result.values())
 p=json.load(open(O/'protocol.json'));positives={q['query']:request(q['query'])for c in p['cases']for q in c['queries']}
 old=json.load(open(O/'original-before.json'));original={c['variant']:request(c['query'])for c in old}
 (O/'request-proof.json').write_text(json.dumps(dict(controls=result,frozen_public_queries=positives,original08=original),ensure_ascii=False,indent=2));print(original)
