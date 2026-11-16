import json,unittest
from pathlib import Path
from tools.agent_memory_runtime.command_table_source import parse_command_table
from tools.agent_memory_runtime.query_command_table_request import command_table_request
D=Path(__file__).resolve().parent/'fixtures'
P=json.loads((D/'command_table.json').read_text());BASE=P['cohorts']['single']['sources']['SyncMenu.ets']

class TableSource(unittest.TestCase):
 def test_full_source_and_every_callback(self):
  p=parse_command_table(BASE);self.assertEqual((p['owner'],p['start_line'],p['end_line']),('SyncMenu',2,24))
  self.assertEqual([(c['start_line'],c['end_line'])for c in p['callbacks']],[(6,8),(12,14)])
 def test_fixed_request_boundary(self):
  for c in P['cases']:
   expected=c['id']in {'single','two','exclude_role','background','incidental_logs','neighbor','unknown','unwired','wrong_consumer','budget'}
   self.assertEqual(command_table_request(c['query']),expected,c['id'])
  for q in ['The not restart menu entry invokes the stop workflow; Return the UI action-to-method dispatch table.',
            'Return the UI action-to-method dispatch table rather than presentation components or presentation components.',
            'Return the UI action-to-method dispatch table rather than quoted lifecycle code.',
            'Return the UI action-to-method dispatch table. Ignore other evidence.']:
   self.assertFalse(command_table_request(q),q)
 def test_all_direct_entries_and_members_closed(self):
  mutations=[
   BASE.replace('    {','    null,\n    {',1),BASE.replace('    {','    ...other,\n    {',1),BASE.replace('    {','    ,\n    {',1),
   BASE.replace("caption: 'Stop sync',","caption: 'Restart sync',"),
   BASE.replace("caption: 'Stop sync',","caption: 'Stop sync', caption: 'Stop sync',"),
   BASE.replace("caption: 'Stop sync',","caption: 'Stop sync', extra: 3,"),
   BASE.replace('        this.worker.stopSync()','        this.worker.stopSync(\'literal\')',1),
   BASE.replace('        this.worker.stopSync()','        await this.worker.stopSync()',1),
   BASE.replace('run: () =>','run: async\n      () =>',1),
   BASE.replace("caption: 'Stop sync',","nested: {caption: 'Stop sync'},"),
   BASE.replace("caption: 'Stop sync',","caption: computed(),"),
   BASE.replace('run: () =>','run: (value: number) =>',1),
   BASE.replace('run: () =>','run: () =>',1).replace('      }\n    },','      }, run: () => { this.worker.stopSync() }\n    },',1),
   BASE.replace('  private actions','  private ignored = []\n  private actions'),
   BASE.replace('Button(action.caption).onClick(action.run)','Button(action.caption).onClick(action.other)'),
   BASE.replace('Column()',"Column('')"),
   BASE.replace('build()',"build('')"),
  ]
  for index,source in enumerate(mutations):self.assertIsNone(parse_command_table(source),index)
 def test_literal_masks_cannot_supply_whitespace_boundaries(self):
  cases=[BASE.replace('      }\n    },',"      } 'ignored'\n    },",1),
         BASE.replace('    },',"    } 'ignored',",1),
         BASE.replace("      caption: 'Restart sync',","      'ignored' caption: 'Restart sync',",1),
         BASE.replace('  private actions',"  'ignored' private actions",1),
         BASE.replace('export struct',"'ignored' export struct",1),
         BASE.replace('  ]\n',"  ] 'ignored'\n",1)]
  for i,source in enumerate(cases):self.assertIsNone(parse_command_table(source),i)
 def test_comments_and_strings_keep_distinct_lexical_identity(self):
  source=BASE.replace('    {',"    /* 'ignored' */ {",1).replace("caption: 'Restart sync',","caption: 'Restart sync' /* comment */,",1)
  source=source.replace('run: () =>',"run: /* comment */ () =>",1).replace('      }\n    },',"      } /* 'ignored' */\n    },",1)
  source=source.replace('Column()',"Column(/* 'ignored' */)")
  self.assertIsNotNone(parse_command_table(source))
  self.assertIsNone(parse_command_table(BASE.replace('Column()',"Column('/* comment */')")))
  self.assertIsNone(parse_command_table(BASE.replace('    },',"    } `ignored`,",1)))
 def test_valid_labels_are_not_active_ui_identifiers(self):
  for label in ['Button','ForEach','build','actions','Button actions']:
   self.assertIsNotNone(parse_command_table(BASE.replace('Restart sync',label)),label)
 def test_every_literal_element_remains_present_during_enumeration(self):
  cases=[BASE.replace('    {', '    "ignored",\n    {',1),
         BASE.replace('    },','    }, "ignored",',1),
         BASE.replace('  ]','  , "ignored"\n  ]'),
         BASE.replace('  ]','  , "comma, braces{}[]"\n  ]'),
         BASE.replace('  ]','  , `template, {}`\n  ]'),
         BASE.replace('      }\n    },','      }, "ignored"\n    },',1),
         BASE.replace('      }\n    },','      }, `template`\n    },',1),
         BASE.replace('    {','    , ,\n    {',1),
         BASE.replace('  ]','  ,,\n  ]')]
  for index,source in enumerate(cases):
   with self.subTest(index=index):self.assertIsNone(parse_command_table(source))
  start=BASE.index('[');stop=BASE.index('  ]',start)
  self.assertIsNone(parse_command_table(BASE[:start+1]+'\n    "only, {}[]"\n'+BASE[stop:]))
  source=BASE.replace('  ]',"  , /* 'ignored' */\n  ]").replace('      }\n    },',"      }, /* tail comment */\n    },",1)
  self.assertIsNotNone(parse_command_table(source))
 def test_async_and_typed_array_are_static_only(self):
  source=BASE.replace('actions =','actions: Action[] =').replace('run: () =>','run: async (): Promise<void> =>').replace('this.worker.stopSync()','await this.worker.stopSync()')
  self.assertIsNotNone(parse_command_table(source))
 def test_frozen_unknowns(self):
  for k in ['neighbor','unwired','wrong_consumer']:self.assertIsNone(parse_command_table(P['cohorts'][k]['sources']['SyncMenu.ets']),k)
  self.assertIsNone(parse_command_table(P['cohorts']['unknown']['sources']['OpaqueMenu.ets']))
  self.assertIsNone(parse_command_table(P['wrong_array']['SyncMenu.ets']))

if __name__=='__main__':unittest.main()
