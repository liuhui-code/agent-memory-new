# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,pathlib,sys
repo=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo))
from tests.test_direct_sink_binding import DirectSinkBindingTests,source
text=source('text: string, business: string','void business\n    Logger.info(text)',"'real message', computeBusiness()")
out=pathlib.Path(sys.argv[1]);assert not out.exists()
r={'source':text,'expected':'real message','actual':DirectSinkBindingTests().public_case(text)}
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
