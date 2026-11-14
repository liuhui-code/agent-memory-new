# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite original-query lexical projection, never source/role authority."""
from dataclasses import dataclass
import re
from .query_language import positive_retrieval_query
from .query_method_evidence import method_evidence_focus_terms, METHOD_EVIDENCE_QUERY_TERM_LIMIT
from .text import identifier_tokens, score_weighted_fields, unique_list, weighted_token_matches, tokenize

ATTRS = {'宽度':'width','width':'width','高度':'height','height':'height',
         '内边距':'padding','padding':'padding','外边距':'margin','margin':'margin',
         '背景颜色':'backgroundColor','背景色':'backgroundColor','backgroundColor':'backgroundColor',
         '列表排列方向':'listDirection','列表方向':'listDirection','listDirection':'listDirection'}
ROLES = {'数据模型':'model','卡片':'card'}
ORIENTATIONS = '横向 纵向 水平 垂直'.split()
TOPICS = '作品 消息 商品 任务 设置 详情 内容 数据 条目 项目 图像 视频 文本'.split()
CONTAINERS = '列表 网格 视图 面板 页面 区域 窗口 容器 画布 工具栏'.split()
OBJECTS = '卡片 元素 内容 文本 图像 图标 按钮 条目 控件 组件'.split()
EVENTS = '裁剪 截断 遮挡 隐藏 覆盖 挤压 拉伸 压缩 移位 重叠'.split()
SPACE = r'[ \t]{0,8}'
def alternatives(values):
    return '(?:'+'|'.join(re.escape(x) for x in sorted(values,key=len,reverse=True))+')'
def terminal(values):
    return alternatives(values)+SPACE
OBSERVATION = ('(?:'+terminal(ORIENTATIONS)+')?(?:'+terminal(TOPICS)+')?'
               +terminal(CONTAINERS)+terminal(['中的'])+terminal(OBJECTS)
               +terminal(['被'])+terminal(EVENTS))
HEAD = terminal(['请返回'])+terminal(['设置','配置'])
PATTERN = re.compile(r'[ \t]{0,16}(?:(?P<observation>'+OBSERVATION+')'+terminal(['，',','])+')?'
    +HEAD+'(?P<attributes>'+terminal(ATTRS)+'(?:'+terminal(['和'])+terminal(ATTRS)+'){0,5})'
    +terminal(['的'])+terminal(['Builder'])+terminal(['源码'])
    +'(?:'+terminal(['，',','])+terminal(['不要返回'])+'(?P<roles>'+terminal(ROLES)
    +'(?:'+terminal(['或'])+terminal(ROLES)+')?))?(?:。)?[ \t]{0,16}')

@dataclass(frozen=True)
class BuilderRequest:
    original: str
    observation: str
    requirements: tuple[str,...]
    exclusions: tuple[str,...]


def parse_builder_request(query):
    if not isinstance(query,str) or len(query)>256 or '\n' in query or '\r' in query:
        return None
    if len(query)-len(query.lstrip(' \t'))>16 or len(query)-len(query.rstrip(' \t'))>16:
        return None
    match=PATTERN.fullmatch(query.strip(' \t'))
    if match is None:
        return None
    attrs=tuple(ATTRS[x.strip(' \t')] for x in re.split(r'[ \t]*和[ \t]*',match['attributes'].strip(' \t')))
    roles=tuple(ROLES[x.strip(' \t')] for x in re.split(r'[ \t]*或[ \t]*',(match['roles'] or '').strip(' \t')) if x)
    if len(set(attrs))!=len(attrs) or len(set(roles))!=len(roles):
        return None
    return BuilderRequest(query,match['observation'] or '',attrs,roles)

_ISSUER=object()
@dataclass(frozen=True)
class PropertyRecall:
    request: BuilderRequest
    retrieval: str
    terms: tuple[str,...]
    issuer: object

    def valid_for(self,query):
        return (self.issuer is _ISSUER and query==self.retrieval
                and parse_builder_request(self.request.original)==self.request
                and positive_retrieval_query(self.request.original)==query
                and self.terms==tuple(x.casefold() for x in self.request.requirements)
                and len(self.terms)>=2)

    def excludes(self,row):
        names=' '.join(str(row.get(k) or '') for k in ('file_path','owner_name','qualified_name'))
        return bool(set([*identifier_tokens(names), *tokenize(names)]) & set(self.request.exclusions))


def recall_projection(query,custom_port=None):
    if custom_port is not None:
        return None
    request=parse_builder_request(query)
    if request is None or len(request.requirements)<2:
        return None
    retrieval=positive_retrieval_query(query)
    terms=tuple(x.casefold() for x in request.requirements)
    if len(unique_list([*method_evidence_focus_terms(retrieval),*terms]))>METHOD_EVIDENCE_QUERY_TERM_LIMIT:
        return None
    return PropertyRecall(request,retrieval,terms,_ISSUER)


def projected_method_terms(query,projection):
    original=method_evidence_focus_terms(query)
    if not isinstance(projection,PropertyRecall) or not projection.valid_for(query):
        return original
    merged=unique_list([*original,*projection.terms])
    return merged if len(merged)<=METHOD_EVIDENCE_QUERY_TERM_LIMIT else original


def score_projected_code(projection,row,query,tokens,expanded,fields,exact):
    active=(isinstance(projection,PropertyRecall) and projection.valid_for(query)
            and not projection.excludes(dict(row)))
    added=[x for x in projection.terms if x not in tokens] if active else []
    score,reasons=score_weighted_fields(query,[*tokens,*added],expanded|set(added),fields,exact)
    matched=[term for term in added if any(weighted_token_matches(term,str(value).lower())
                                         for _,value,_ in fields)]
    if matched:
        reasons=unique_list([*reasons,*['expanded_builder_property:'+term for term in matched]])
    return score,reasons


def filter_projected_method_ids(conn,project,ids,query,projection):
    if not isinstance(projection,PropertyRecall) or not projection.valid_for(query) or not ids:
        return ids
    from .query_method_evidence import method_evidence_term_coverage
    rows=conn.execute('SELECT id,file_path,qualified_name,method_evidence FROM code_symbols '
                      'WHERE project_id=? AND id IN ('+','.join('?' for _ in ids)+')',
                      [project.project_id,*ids]).fetchall()
    old=method_evidence_focus_terms(query)
    keep={row['id'] for row in rows if not projection.excludes(dict(row))
          or (len(old)>=2 and method_evidence_term_coverage(row['method_evidence'] or '',old)>=2)}
    return [i for i in ids if i in keep]
