# Explicit negative caller intent: narrow Development repair

Original42 investigation found an independent public defect in the existing ModalBridge/ConfirmPanel/ResetPanel Development fixture. Public context('Find ModalBridge implementation.') anchors ModalBridge first. Appending 'Do not return actual caller context.' or ', not the actual caller context.' instead focused ResetPanel.onClick first. Actual callable evidence still retained ModalBridge; this was false caller-query activation, not a real new caller target. Five input requests were frozen before implementation; raw before outputs0–4 retained.

caller_owner_query used substring scanning of the full request. Now only existing clearly delimited result-negative/comparison spans are masked before checking markers. Retrieval text, score, graph, source and exclusion algorithms are not changed. Search's positive_retrieval_query cannot be reused here: it intentionally retains negative identifiers and falls back to original text if empty. Pure negative caller therefore gets no caller intent. Qualified negative onClick is not a positive role.

Unknown quotes, mixed conjunction/contrast and non-exclusive not only/just/merely/solely/exclusively (including don't return forms) preserve legacy interpretation. This is NOT a general natural-language discourse resolver. Existing marker semantics outside the narrow clauses remain unchanged, including known quote/substring limitations.

Public raw+compact outputs after the first minimal candidate show the two negative requests no longer force caller-only selection; ModalBridge first, real callers still preserved as ordinary evidence. Positive caller controls stay ConfirmPanel first. Final persistent tests repeat natural public requests raw+compact under the final implementation.

Independent review caught unsafe not only, but/and also, identifier-boundary and don't return qualifiers; final explicit controls retain positive/unknown cases. Initial boundary implementation failed2 of24 tests because a preceding word incorrectly blocked comma-boundary recognition. Failure logtests.txt preserved. Final24 focused invocations pass (no full gate). Original42 selected3-variant Development gate stays1/3; original/English precision fail, Chinese passes. This patch does not claim to close42 or improve original precision.

No budget or score/oracle changes. Production diff only caller-intent gate and tests. Read-only32/13 reallocation assessment separately documented; rejected lossy/default/encoding proposals not shipped.
