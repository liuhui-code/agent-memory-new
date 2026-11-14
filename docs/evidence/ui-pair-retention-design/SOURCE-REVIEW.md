# Initial source review and correction

2bd507b's private identity binding passed local tests but the consumer bypassed
all callable focus whenever eligible. Independent review correctly rejected this
as broader than refusing actual pair erasure: valid focus that keeps both owners
while reducing redundant intervals must still work. No public after was run on
that candidate. Preserve its code and35-test log as intermediate evidence only.

Revision runs existing focus normally. It accepts focused output when each bound
owner remains represented by at least one complete already-bound interval (not
merely the same file). Only actual loss returns the original anchors. New controls
cover legitimate focused removal of an extra interval and same-file two-owner
loss. Source reads additionally verify byte count after read, not only pre-read
stat, to fail closed on a file growing beyond2MiB.
