# Fresh original05 paired result: no new original gain

Fresh f0c7d45 baseline and fixed4907222 each pass1/3. Earlier retained2/3 observations
are historical, not the current baseline. In both fresh runs generic precision is
0.3333 with AccountSettingsPage, NotificationDetailsPage and ArticleMarkupView;
en-paraphrase passes with only ArticleMarkupView; Chinese variant fails precision
and span with GalleryListViewModel, ArticleMarkupView and QuotedMessagePreview.
Observed paths and mandatory check results are unchanged, not a new regression or
new repair. The pair JSON retains all values without reconstructing a total score.

The exact original generic query was traced once on fixed490. bind_render_context
returns baseline at its protected-context guard, before any source scan. The
baseline includes a log-emitter AccountUpdateService.dispatchUpdate anchor and log
context. This trips the frozen log-preservation guard. The actual ArticleMarkupView
source itself satisfies the already-fixed parser (build7–12/helper14–18); changing
the parser cannot resolve this first rejection. The log guard is NOT weakened and
no competitor/logger is deleted merely to satisfy the original precision oracle.

Independent Development13 compatibility/target results remain valid engineering
results, but do not imply original05 fixed. No full suite or global score inferred.
Final review must decide integration scope with this limitation explicit.
