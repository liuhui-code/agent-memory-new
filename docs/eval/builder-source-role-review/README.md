# Builder source-role: bounded design review

Base `a829b1d`. Read-only code and saved public evidence review. No new queries,
fixtures, tests, production changes or original oracle changes.

## Actual failure and source mapping

`docs/eval/builder-role-current/{README.md,independent.json,contract-observations.json}`
records the independently frozen query “Locate the reusable Builder that sets row
height and alignment.” RibbonCanvas.renderStrip is already recalled with actual
range 4–11. LayoutGuide.build wins 29.9 versus renderStrip19.29 and ordinary
PanelViewport.build20.29. All three are owner_kind=component and receive
 target_owner_kind_match=true. Four fixed controls retain explicit renderStrip,
ordinary build, both components and the exact instructional text. They must stay
unchanged. This is not a missing method/range, import edge or projection identity.
The original group remains historically2/3; no fresh score is claimed here.

The original source `docs/eval/fixtures/system-capability/src/views/WorkGalleryPage.ets`
has @Builder on line11 preceding renderWorkGallery on line12. Existing named method
parsing can locate the method independently of that decorator. The generic inline
header parser also skips @Builder, @Styles or other decorator prefixes to locate
a declaration; tests/test_ecma_callable_headers.py explicitly tests those ranges.
This generic prefix handling is not a Builder semantics certificate.

`ecma_callable_headers.CallableHeader` records name, parameters, return type,
visibility and body/header positions, not decorator identity. In semantic_ecma,
parse_container_members forms source from the recognized declaration line through
its body end and passes it to callable_roles. A preceding standalone decorator is
outside that slice; inline decorators can be inside it but their meaning is not
exported. Member owner_kind comes from the containing component. Top-level
functions are module-owned and need a distinct binding check, not an assumption
that every Builder belongs to a component.

`semantic_callable_profile.callable_roles` records existing async/lifecycle/guard/
state/persistence/navigation and source-operation facts, not Builder decoration.
OWNER_KIND_QUERY_ALIASES deliberately maps builder to component. Thus no existing
Builder-specific role is produced and then accidentally discarded by a consumer.
The current distinction is unrepresented, not a violated existing fine-grained role.
The accepted named-import alias correction preserves original callee names; it
supplies no missing Builder role and is not a second defect of this role contract.

## Substantive scope decision: local role is not automatically architecture

A source-bound Builder decoration fact can plausibly reuse the existing
callable_roles/adapter metadata channel without a new persistent schema, generic
relation graph or new proof framework. That bounded adapter enhancement is not
inherently an architecture change and does NOT require two independent defect
classes merely because its role value is new. The independent public competition
above provides a concrete reason to investigate it.

Conversely, a general decorator resolver, cross-file alias/import semantics,
framework effect system or private cross-owner certificate would be a new
abstraction and requires its own evidence and review. Existing generic inline
prefix recognition must not be sold as already implementing those semantics.

There is therefore a viable bounded next step; this review does not declare the
category architecturally blocked. It also does not approve a ranking patch:
producing a source fact and deciding how a request uses it are separate changes.

## Minimal producer proposal to freeze before implementation

Represent only an actual supported ArkTS @Builder declaration bound to the exact
already-indexed callable, preserving its current name, owner, key, method range and
digest. Keep decorator source position separately available if needed for audit;
do not silently expand the callable body range to encompass other declarations.
Reuse existing typed metadata, not a boolean derived from file text or owner name.

The first subset should have a precise accepted decorator syntax and adjacency
rule. A preceding standalone decorator and same-line decorator must attach to the
same immediately following supported callable, not the nearest arbitrary method.
Only supported lexical input and unambiguous scope may produce the fact. Comments,
strings/templates, @BuilderParam fields, property references, unrelated decorators,
decorator arguments, malformed/unsupported stacked declarations, duplicate/overload
identities, method-versus-top-level forms and legacy/unknown adapters need explicit
outcomes. Unsupported cases may remain unknown; they are not absence proofs.

In particular, the existing header helper accepts generic decorator arguments for
locating methods. That does not mean @Builder(arguments) is supported Builder syntax.
Do not use a broad substring such as Builder inside BuilderParam or a comment.
Old indexes have no new fact until ordinary merge relearns identical source bytes.
No file-wide fact may be copied onto every component method.

## Minimal consumer proposal: needs its own reviewed boundary

Keep component owner_kind and ordinary component/build behavior unchanged. A new
callable role is more specific than the owner's coarse kind; it must not rename
components to Builder or redefine all existing owner-kind matches.

An affirmative request for a declared Builder callable could use the fact only
under a specified request contract. Literal/instructional text requests, explicit
other identifiers, ordinary component/build requests, mixed/multiple targets and
unknown intent retain their current protections. The frozen text control already
contains Builder and component target matches, so token presence alone is unsafe.
Similarly, a user could request an implementation returning Builder source or a
wrapper calling a Builder; absence of decoration does not establish irrelevance.
Reuse existing identity vetoes but do not assume absence of veto proves intent,
as the separate literal-intent-shadow HTML counterexample demonstrated.

Do not set source_operation_match: that is not a Builder-declaration role and its
current supported operations and unknown guards are unrelated. A local role also
does not prove row-height/alignment ownership, runtime rendering, causality or
unique global implementation. Multiple real Builders must not collapse by fiat.

## Smallest falsifiable next stage

1. Freeze a tiny source-to-existing-symbol binding protocol using the already saved
   independent Builder source and fixed queries. Add source identity negative
   controls for actual versus commented/string Builder, BuilderParam, inline versus
   preceding decoration, same-file ordinary methods, top-level/member distinction
   and unsupported/duplicate cases. Do not execute until acceptance is specified.
2. Test producer feasibility separately through formal learned-symbol output and
   same-bytes install-only versus ordinary merge. Require stable identity/ranges
   and no false role on ordinary or unknown methods. Producer green alone is not
   owner-selection improvement.
3. Before any consumer edit, freeze the exact request-to-role rule plus actual
   operation/text/artifact/explicit/multiple/unknown controls. If that rule cannot
   safely admit the existing generic Builder query without treating instructional
   or generated-artifact requests as executable-only, stop that consumer design.
4. Only a reviewed local consumer may be tried against the unchanged independent
   red and four positives, checking actual source, primary and existing budget.
   If public red remains or a control regresses, reject without new words/scores.
   Do not weaken the original oracle or claim producer-only metadata as a fix.

No extra independent defect class is demanded for step2's bounded reuse of an
existing metadata channel. No serving implementation, generic architecture or
new source-reading permission is granted by this document. This is a concrete
finite next action, not another open-ended marker investigation.
