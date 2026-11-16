# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Same-read source validation for metadata-qualified component frames."""
import re
from .command_table_source import comment_only_mask, parse_command_table, NAME
from .ecma_callback_mask import callback_mask_lines, quoted_end, template_end, comment_end
from .ecma_callable_ranges import property_callback_ranges, member_callback_ranges, named_callable_ranges
from .context_callback_binding import _pairs


def source_key(row):return row['symbol'],row['start_line'],row['end_line']


def known_frame_quotes(source):
    """Stricter local negative-certificate lexer; never repair unknown syntax."""
    i=0
    while i<len(source):
        if source[i]in "'\"":
            end=quoted_end(source,i,source[i],len(source))
            if end is None or any(c in source[i:end]for c in ('\n','\r')):return False
            i=end
        elif source[i]=='`':
            i=template_end(source,i,len(source))
        elif source.startswith(('//','/*'),i):
            i=comment_end(source,i,len(source))
        else:i+=1
        if i is None:return False
    return True


def certify_frame(source,frame):
    """False=unknown; None=finite-template nonmatch; dict=closed positive."""
    if not known_frame_quotes(source):return False
    lines=source.splitlines();masked=callback_mask_lines(lines)
    if masked is None:return False
    mask='\n'.join(masked);syntax=comment_only_mask('\n'.join(lines));pairs=_pairs(mask)
    if syntax is None or pairs is None or '\\'in mask:return False
    owner=frame['owner'];lo,hi=owner['start_line'],owner['end_line']
    if not 0<lo<hi<=len(lines):return False
    declaration=re.fullmatch(rf'\s*(?:export\s+)?struct\s+({NAME})\s*\{{\s*',syntax.split('\n')[lo-1])
    if declaration is None or declaration[1]!=owner['symbol']:return False
    opening=sum(len(line)+1 for line in lines[:lo-1])+masked[lo-1].index('{')
    closing=pairs.get(opening)
    if closing is None or mask.count('\n',0,closing)+1!=hi:return False
    # An actual direct build and actual callback ranges, not signature strings.
    named=[r for r in named_callable_ranges(lines)if source_key(r)==source_key(frame['build'])]
    if len(named)!=1:return False
    build=frame['build'];offset=sum(len(line)+1 for line in lines[:build['start_line']-1])
    ancestors=[a for a,b in pairs.items()if mask[a]=='{'and a<offset<b]
    if not ancestors or max(ancestors)!=opening:return False
    callbacks=[*property_callback_ranges(lines),*member_callback_ranges(lines)]
    for row in frame['callbacks']:
        if len([c for c in callbacks if source_key(c)==source_key(row)])!=1:return False
    # This only rejects membership in our finite ForEach template. It says
    # nothing about other runtime dispatch mechanisms or uninspected sources.
    if re.search(r'\bForEach\b',mask)is None:return None
    parsed=parse_command_table(source)
    if parsed is None:return False
    if (parsed['owner'],parsed['start_line'],parsed['end_line'])!=(owner['symbol'],lo,hi):return False
    if source_key(parsed['build'])!=source_key(build):return False
    for callback in parsed['callbacks']:
        if len([r for r in frame['callbacks']if source_key(r)==source_key(callback)])!=1:return False
    return parsed
