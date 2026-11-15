# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,pathlib,sys
repo=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo))
from tests.test_direct_sink_binding import DirectSinkBindingTests,source
out=pathlib.Path(sys.argv[1]);assert not out.exists()
case=DirectSinkBindingTests()
base=source('text: string, business: string','void business\n    Logger.info(text)',"'real message', 'business value'")
result={}
for name,text in [('extra_method',base.replace('export class Courier {','export class Courier {\n  unrelated(): void {}')),('extra_field',base.replace('export class Courier {','export class Courier {\n  private counter: number = 0'))]:
 result[name]={'source':text,'expected':'real message','actual':case.public_case(text)}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
