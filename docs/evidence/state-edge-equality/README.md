# Equality is a state read, not assignment

Separate stage based on lexical fix871071c. Public red9541b94 freezes fresh
learn/list code_symbol edges: `this.count == 2` and `this.count === 2` each produced
writes_state and no reads_state. Five genuine writes (=,+=,-=,++,--) were controls.

Only the naked '=' alternative in both state-reference regexes now rejects a
following '='. Thus equality stops matching the write arm and is admitted by the
read arm. No additional operator family or implicit read for compound writes is
introduced. Existing source/target identity, relation metadata, scope and lexical
fallback remain unchanged. Unknown lexical bodies use the unchanged unmasked-body
path, with this corrected operator predicate, not a claim of absence.

- Public red:1 test,2 failed equality subcases. Candidate before/after in JSON.
-55 lexical/operator/semantic/typed-reference related tests pass,0 expected failures.
- Final2 operator tests pass after adding unchanged !=/!==/<= read controls.
  Empty/space/newline separation is covered, and if(this.count===2){this.count=3}
  emits both read and write. Five compound/direct write controls retain old behavior.
- One initial related command used a nonexistent test module name; its ImportError
  is preserved in related-wrong-module.txt. Corrected real module run passes55.
- This stage independently reindexes the SAME source/memory from871071c. Code-only
  still has7 old state edges; normal learn-path merge retains7 total but replaces
  the2 false equality writes with2 reads, preserving all5 genuine writes. This is
  separate from lexical stage13→7 and is not inferred from that earlier result.
- Original comparison group remains2/3, unchanged from both623981f and871071c.
  No original failure closed; no full-suite or overall precision gain is claimed.
- Independent read-only review found no blocker;12 extra copy controls passed.

Nested `this` binding, unsupported syntax and other operator semantics remain
outside this patch. No execution ordering, causality or owner uniqueness is inferred.
