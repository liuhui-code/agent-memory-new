# Typed named-import alias: frozen public before

Fixed baseline17ad3ae. No runtime candidate in this freeze.

Original independent fixture: importing ActualStore as LocalStore and declaring
store:LocalStore loses the known calls edge when the module has two classes with
read methods. Direct ActualStore and direct OtherStore controls bind correctly.
The index uses unique lookup tables; ambiguity does not arbitrarily choose either.

Supplemental independent controls freeze same class names in distinct modules,
missing qualified method, generic type-parameter shadow, receiver-parameter shadow,
duplicate imports, absent/dynamic field types and awaited field calls. The initial
supplemental public snapshot is kept separately; then AwaitConsumer was added and
observed before any implementation. Original source/query expectations are unchanged.

An additional actual false edge is demonstrated: MissingStores.ActualStore lacks
read but another OtherStore.read exists in that module. The old fallback connects
MissingConsumer.collect to OtherStore.read. Thus merely mapping local type name to
imported original name is not sufficient: typed resolution must respect both module
and exact qualified class.method and abstain on missing/ambiguous targets.

The pending design may reuse the separate bare-import stage's alias-name metadata,
but it must have its own typed-target contract. Bare-function detail/proof may not
be reused. Only independently justified this.field accesses, with class generic and
nested/unknown shadow cases guarded, are candidates for new binding. Calls and
awaits must agree. This is one alias-binding problem with multiple controls, not a
new architecture claim. Parent review/new integrated base precedes implementation.
