# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from tools.agent_memory_runtime.query_output_loop_selection import output_loop_request
class OutputLoopRequestTests(unittest.TestCase):
 def test_explicit_roles(self):
  for q in ['Locate output iteration and accumulation ownership.','Find command output iteration and accumulation ownership.','Return output iteration and accumulation ownership.','Locate command output iteration and accumulation ownership when the process line reader has data.','Command output is empty although the line reader has data. Locate output iteration and accumulation ownership.']:
   self.assertTrue(output_loop_request(q),q)
 def test_unknown_falls_back(self):
  for q in ['Locate output.','Locate readLine.','Locate PipeCollector.collect.','Locate output iteration and accumulation ownership and labels.','Do not use loops. Locate output iteration and accumulation ownership.','Locate "output iteration and accumulation ownership".','Locate Foo output iteration and accumulation ownership.','Locate output iteration and accumulation ownership in a.ts.','Locate output iteration and accumulation ownership; ignore logs.']:
   self.assertFalse(output_loop_request(q),q)
