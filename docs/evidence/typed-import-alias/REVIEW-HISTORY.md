# Freeze and candidate corrections

- Original independent public inputs were frozen at92bbae2 on17ad3ae. They were
  cherry-picked unchanged as e859bfb on new implementation base0f0beb6. The original
  five red subcases were reproduced on that integrated baseline.
- e76f0b0 adds whole-container unknown, nested/body and awaits reviewer negatives;
  6a9b06d adds composite/generic/qualified field types and root-receiver suffix.
  These are supplemental freezes, not edits to the original positive expectations.
- During review the candidate falsely authorized explicit `this: OtherReceiver`
  methods. Formal public failures for calls and awaited access are retained in
  explicit-this-candidate-red.txt. New guards reject explicit this/static methods.
- Next, a class under a generic outer function showed a false binding. The formal
  public outer-generic-candidate-red.txt is retained. The accepted scope was
  reduced to module-top-level owners, rather than resolving enclosing generics.
- Brace depth alone still accepted generic-arrow class expressions, parenthesized
  and bare. arrow-class-candidate-red.txt preserves both failing subcases. The final
  subset rejects ANY full-file arrow and uses the complete()[]{} stack for top-level
  admission. It is not a general TypeScript scope parser.
- Duplicate owner names are conservatively rejected; this has a formal helper
  control and independent reviewer public namespace control. It is not claimed as
  another original frozen red or a solved namespace resolver.

The latest review-negative-protocol.json includes these added candidate negatives;
it is NOT byte-identical to its first version. protocol.json and its initial
positive expectations remain unchanged. No original pack oracle/query was edited.
This candidate required corrections; the history must not imply it passed first try.
