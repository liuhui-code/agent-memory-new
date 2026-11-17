"""Request-bound protection for SQL source views; no source or serving authority."""
import math
import re

CANDIDATE_KEYS = {'file_path','symbol','owner_name','owner_kind','target_owner_kind_match',
                  'file_structural_coverage','callable_roles','reasons','score','evidence_score','source_range'}
TEXT_KEYS = {'file_path','symbol','owner_name','owner_kind'}
TOP_KEYS = {'schema_version','certainty','primary','alternatives','boundary'}
RANGE_KEYS = {'start_line','end_line','selection_reason'}


def _range(value):
    return (type(value) is dict and set(value) <= RANGE_KEYS
            and type(value.get('start_line')) is int and type(value.get('end_line')) is int
            and 0 < value['start_line'] <= value['end_line']
            and ('selection_reason' not in value or type(value['selection_reason']) is str))


def _candidate(value):
    if type(value) is not dict or not set(value) <= CANDIDATE_KEYS:
        return False
    for key, item in value.items():
        if key in TEXT_KEYS and type(item) is not str: return False
        if key in {'score','evidence_score'} and (type(item) not in (int,float) or not math.isfinite(item)): return False
        if key == 'target_owner_kind_match' and type(item) is not bool: return False
        if key == 'file_structural_coverage' and (type(item) is not int or item < 0): return False
        if key in {'callable_roles','reasons'} and (type(item) is not list or any(type(x) is not str for x in item)): return False
        if key == 'source_range' and not _range(item): return False
    return bool(value.get('file_path') and value.get('symbol'))


def ordinary_callable(value):
    """Strict compact-only disposable code schema; unknown descendants decline."""
    if type(value) is not dict or set(value) != TOP_KEYS: return False
    if (value['schema_version'] != 'agent-callable-evidence/v1'
            or value['certainty'] not in ('bounded','uncertain','unavailable')
            or type(value['boundary']) is not str): return False
    if value['primary'] is not None and not _candidate(value['primary']): return False
    alternatives = value['alternatives']
    if value['certainty'] == 'unavailable' and (value['primary'] is not None or alternatives): return False
    return type(alternatives) is list and len(alternatives) <= 2 and all(_candidate(x) for x in alternatives)


def _reparse_request(query):
    # Import remains lazy during parallel implementation; unavailable parser grants nothing.
    try:
        from .query_sql_slot_request import sql_slot_request
        return sql_slot_request(query)
    except ImportError:
        return None


def _projection(query, descriptor):
    parsed = _reparse_request(query)
    if type(parsed) is not dict or type(descriptor) is not dict or parsed != descriptor:
        return None
    if parsed.get('query') != query: return None
    spans = []
    for name, key in [('method','method_span'),('state','state_span')]:
        span = parsed.get(key)
        if (not isinstance(span,(tuple,list)) or len(span)!=2
                or any(type(x) is not int for x in span)
                or not 0 <= span[0] < span[1] <= len(query)
                or query[span[0]:span[1]] != parsed.get(name)): return None
        spans.append(span)
    negative = parsed.get('negative_span')
    if negative is not None:
        if (not isinstance(negative,(tuple,list)) or len(negative)!=2
                or any(type(x) is not int for x in negative)
                or not 0 <= negative[0] < negative[1] <= len(query)
                or query[negative[0]:negative[1]] != '，不要返回 '+str(parsed.get('excluded_owner'))): return None
        spans.append(negative)
    elif parsed.get('excluded_owner') is not None: return None
    observation = parsed.get('observation_span')
    if observation is not None:
        if (not isinstance(observation,(tuple,list)) or len(observation)!=2
                or any(type(x) is not int for x in observation)
                or not 0 == observation[0] < observation[1] <= len(query)):
            return None
        spans.append(observation)
    chars = list(query)
    for lo, hi in spans: chars[lo:hi] = ' ' * (hi-lo)
    return ''.join(chars)


def _raw_callable_safe(value):
    """Raw may carry a portfolio; do not require compact schema before compaction."""
    allowed = (TOP_KEYS | CANDIDATE_KEYS | RANGE_KEYS | {'passage_portfolio','mode','state',
        'target_scope','members','selection_basis','candidate_recall_changed','support_reasons',
        'callable_start_line','callable_end_line'})
    def walk(v):
        if isinstance(v,dict):
            return all(type(k) is str and k in allowed and walk(x) for k,x in v.items())
        if isinstance(v,list): return all(walk(x) for x in v)
        return v is None or type(v) in (str,bool,int) or (type(v) is float and math.isfinite(v))
    return isinstance(value,dict) and walk(value)


def _named(item, projection, method, state, excluded):
    if item.get('log_identity_match'): return True
    excluded_owner = excluded is not None and (item.get('owner_name') == excluded or item.get('symbol') == excluded)
    if item.get('identity_match') and item.get('symbol') not in (method,state) and not excluded_owner: return True
    for key in ('file_path','symbol','qualified_name','owner_name','function'):
        name = item.get(key)
        if isinstance(name,str) and name and re.search(r'(?<![\w$])'+re.escape(name)+r'(?![\w$])',projection,re.I):
            return True
    return False


def protected_sql_slot(data, query, pool, descriptor, *, pending=False):
    """True means decline. Descriptor is reparsed, never trusted as a bare grant."""
    from .log_event_identity import event_match
    from .query_log_owner_admission import independently_named_log_owner
    try:
        projection = _projection(query,descriptor)
        if projection is None or not isinstance(data,dict) or type(pool) is not list: return True
        if data.get('query',query) != query: return True
        handoff = data.get('query_handoff')
        if not isinstance(handoff,dict): return True
        if handoff.get('input_query',query) != query: return True
        path = handoff.get('path_context')
        if pending and path is None: path = {'activated':False,'path_candidates':[]}
        if (type(path) is not dict or type(path.get('activated')) is not bool
                or type(path.get('path_candidates')) is not list): return True
        if any(path.get(k) for k in ('activated','wrapped_log_evidence','path_candidates','seeds')): return True
        evidence = handoff.get('callable_evidence')
        if not _raw_callable_safe(evidence): return True
        items = list(pool)
        for key in ('code_anchors','log_anchors'):
            if type(handoff.get(key)) is not list: return True
            items.extend(handoff[key])
        for log in handoff['log_anchors']:
            if not isinstance(log,dict): return True
            # Never project negative or method/state spans for event identity.
            if event_match(log,query)['priority'] > 0 or independently_named_log_owner(log,query): return True
        def candidates(v):
            if isinstance(v,dict):
                yield v
                for x in v.values(): yield from candidates(x)
            elif isinstance(v,list):
                for x in v: yield from candidates(x)
        items.extend(candidates(evidence))
        return any(not isinstance(x,dict) or _named(x,projection,descriptor['method'],descriptor['state'],descriptor.get('excluded_owner')) for x in items)
    except (KeyError,TypeError,ValueError,OverflowError,RecursionError):
        return True
