from source_qualification import *
p=resolve_project(str(O/'Warehouse'),str(O/'Warehouse-memory'))
with connect(p)as c:rows=[dict(r)for r in c.execute("SELECT * FROM code_symbols WHERE project_id=? AND file_path='WarehouseAccumulator.ets'",(p.project_id,))]
row=next(r for r in rows if r['symbol']=='refresh');owner=next(r for r in rows if r['symbol']=='WarehouseAccumulator');methods=[r for r in rows if r['symbol_type']in {'method','function'}]
s=(O/'Warehouse/WarehouseAccumulator.ets').read_text()
# Fixed source-contract mutations, not public-query positives or benchmark outcomes.
controls={'ordinary_number':s.replace('@State total','total'),'wrong_field':s.replace('@State total','@State other'),'unknown_decorator':s.replace('@State total','@Observed total'),'comment_declaration':s.replace('@State total','// @State total'),'deferred_callback':s.replace('this.total += row.quantity','queueMicrotask(() => { this.total += row.quantity })'),'local_target':s.replace('this.total +=','total +='),'duplicate_declaration':s.replace('private rows: StockRow[] = []','@State total: number = 0')}
result={k:state_binding(v,row,owner,methods)for k,v in controls.items()};assert not any(result.values());result['valid_source']=state_binding(s,row,owner,methods);assert result['valid_source'];(O/'source-controls.json').write_text(json.dumps(dict(classification='read-only source qualification mutation controls',results=result),indent=2));print(result)
