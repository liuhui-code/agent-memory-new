# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass

from .query_language import positive_retrieval_query
from .text import query_tokens, terms_from_text, unique_list


@dataclass(frozen=True)
class BehaviorConcept:
    name: str
    trigger_groups: tuple[tuple[str, ...], ...]
    markers: tuple[str, ...]


BEHAVIOR_CONCEPTS = (
    BehaviorConcept(
        name="scroll_layout",
        trigger_groups=(
            ("scroll",), ("viewport", "layout"), ("list", "clip"),
            ("滚动",), ("滑动",), ("列表", "裁剪"),
        ),
        markers=("listdirection", "scroll", "height"),
    ),
    BehaviorConcept(
        name="horizontal_list_layout",
        trigger_groups=(
            ("horizontal", "list"), ("horizontally", "scroll"),
            ("横向", "列表"), ("水平", "列表"),
        ),
        markers=("horizontalaxis", "listdirection", "height"),
    ),
    BehaviorConcept(
        name="vertical_list_layout",
        trigger_groups=(
            ("vertical", "layout"), ("vertical", "list"),
            ("纵向", "列表"), ("垂直", "列表"),
        ),
        markers=("verticalaxis", "listdirection", "height"),
    ),
    BehaviorConcept(
        name="reactive_aggregate",
        trigger_groups=(
            ("total", "unchanged"), ("total", "refresh"),
            ("aggregate", "react"), ("总计", "不变"), ("汇总", "刷新"),
        ),
        markers=("foreach", "watch", "state", "observedproperty"),
    ),
    BehaviorConcept(
        name="visual_overlap",
        trigger_groups=(
            ("overlap",), ("layer", "cover"), ("control", "cover"),
            ("遮挡",), ("控件", "覆盖"), ("图层", "覆盖"),
        ),
        markers=("overlay", "backgroundcolor", "zindex", "stack", "position"),
    ),
    BehaviorConcept(
        name="reusable_spacing",
        trigger_groups=(
            ("reusable", "spacing"), ("breathing", "room"),
            ("shared", "spacing"), ("复用", "间距"), ("留白",),
        ),
        markers=("margin", "padding"),
    ),
    BehaviorConcept(
        name="reusable_toolbar_layout",
        trigger_groups=(
            ("keyboard", "toolbar"), ("shared", "toolbar"),
            ("navigation", "toolbar"), ("reusable", "toolbar"),
            ("键盘", "工具栏"), ("共享", "工具栏"), ("导航", "工具栏"),
        ),
        markers=("toolbarrole",),
    ),
    BehaviorConcept(
        name="archive_asset_refresh",
        trigger_groups=(
            ("temporary", "archive"), ("archive", "reused"),
            ("asset", "extraction"), ("bundle", "extraction"),
            ("临时", "归档"), ("归档", "复用"),
            ("资源", "解压"), ("压缩包", "复用"),
        ),
        markers=("archiveioboundary",),
    ),
    BehaviorConcept(
        name="collection_aggregation",
        trigger_groups=(
            ("multiple", "records"), ("shared", "records"),
            ("final", "item"), ("combine", "records"),
            ("多个", "记录"), ("共享", "记录"),
            ("最后", "条目"), ("聚合", "记录"),
        ),
        markers=("collectionfold",),
    ),
    BehaviorConcept(
        name="keyboard_focus_state",
        trigger_groups=(
            ("keyboard", "focus"), ("editor", "focus"),
            ("dismiss", "focus"), ("regaining", "focus"),
            ("键盘", "焦点"), ("编辑器", "焦点"),
            ("收起", "焦点"),
        ),
        markers=("keyboardvisibility", "focusstate"),
    ),
    BehaviorConcept(
        name="native_color_conversion",
        trigger_groups=(
            ("color", "conversion"), ("color", "parsing"),
            ("opaque", "value"), ("status", "bar", "color"),
            ("颜色", "转换"), ("颜色", "解析"),
            ("状态栏", "颜色"),
        ),
        markers=("colorparser",),
    ),
    BehaviorConcept(
        name="clipboard_content_read",
        trigger_groups=(
            ("clipboard", "content"), ("clipboard", "plain", "text"),
            ("pasting", "text"), ("pasteboard", "record"),
            ("剪贴板", "内容"), ("粘贴", "文本"),
        ),
        markers=("clipboardread",),
    ),
    BehaviorConcept(
        name="startup_permission_sequence",
        trigger_groups=(
            ("startup", "permission"), ("permission", "result"),
            ("permission", "before"), ("permission", "sequence"),
            ("启动", "权限"), ("权限", "结果"), ("权限", "顺序"),
        ),
        markers=("permissionrequest", "permissionguard"),
    ),
    BehaviorConcept(
        name="process_output_read",
        trigger_groups=(
            ("command", "output", "empty"), ("empty", "output"),
            ("line", "reader"), ("read", "loop"),
            ("命令", "输出", "为空"), ("读取", "循环"),
        ),
        markers=("outputreadloop",),
    ),
    BehaviorConcept(
        name="runtime_capability_probe",
        trigger_groups=(
            ("manifest", "capability"), ("runtime", "probe"),
            ("runtime", "capability"), ("capability", "unavailable"),
            ("清单", "能力"), ("运行时", "能力"), ("能力", "不可用"),
        ),
        markers=("runtimecapability",),
    ),
    BehaviorConcept(
        name="ui_callback_owner",
        trigger_groups=(
            ("confirmation", "button"), ("button", "callback"),
            ("click", "owner"), ("onclick",), ("tapped", "dismiss"),
            ("确认", "按钮"), ("点击", "调用方"), ("点击", "所有者"),
        ),
        markers=("uicallbackbinding",),
    ),
    BehaviorConcept(
        name="persistence_restore_contract",
        trigger_groups=(
            ("restore", "empty"), ("restores", "empty"),
            ("startup", "wrong", "key"), ("lifecycle", "read"),
            ("preference", "restore"), ("恢复", "为空"),
            ("生命周期", "读取"), ("读取键", "契约"),
        ),
        markers=("persistenceread", "lifecycleboundary", "persistencewrite"),
    ),
    BehaviorConcept(
        name="platform_sensitive_ui",
        trigger_groups=(
            ("unsupported", "platform"), ("cross-platform", "control"),
            ("platform", "gating"), ("platform-specific",),
            ("runtime", "api", "unavailable"), ("跨平台", "控件"),
            ("平台", "能力"), ("不支持", "能力"),
        ),
        markers=("platformsensitiveui",),
    ),
    BehaviorConcept(
        name="serialized_persistence",
        trigger_groups=(
            ("incremental", "checkpoint"), ("checkpoint", "final"),
            ("queued", "write"), ("partial", "write", "completed"),
            ("write", "tail"), ("final", "barrier"),
            ("增量", "检查点"), ("串行", "写入"), ("最终", "等待"),
        ),
        markers=("serializedwrite", "writebarrier"),
    ),
    BehaviorConcept(
        name="timeout_cancellation",
        trigger_groups=(
            ("initialization", "timeout"), ("timeout", "late"),
            ("background", "bootstrap"), ("deadline", "cancelled"),
            ("初始化", "超时"), ("后台", "继续"), ("超时", "取消"),
        ),
        markers=("timeoutboundary", "cancellationguard"),
    ),
    BehaviorConcept(
        name="webview_navigation_policy",
        trigger_groups=(
            ("webview", "scheme"), ("embedded", "webview"),
            ("browser", "javascript"), ("file", "url"),
            ("in-app", "browser"), ("内嵌", "浏览器"),
            ("文件", "协议"), ("危险", "协议"),
        ),
        markers=("webaccesspolicy", "urlschemeguard"),
    ),
    BehaviorConcept(
        name="bounded_cache_eviction",
        trigger_groups=(
            ("cache", "oldest"), ("cache", "evict"),
            ("capacity", "exceeded"), ("entry", "limit"),
            ("缓存", "最旧"), ("缓存", "淘汰"), ("超过", "容量"),
        ),
        markers=("cacheeviction",),
    ),
    BehaviorConcept(
        name="fallback_recovery",
        trigger_groups=(
            ("fallback", "never"), ("fallback", "reconnect"),
            ("offline", "reconnect"), ("mock", "upgrade"),
            ("降级", "恢复"), ("离线", "恢复"), ("模拟", "真实"),
        ),
        markers=(
            "fallbackbranch", "repositoryboundary", "lifecyclesync", "statewrite",
        ),
    ),
    BehaviorConcept(
        name="callback_containment",
        trigger_groups=(
            ("malformed", "payload"), ("callback", "throws"),
            ("responses", "stop"), ("malformed", "json"),
            ("畸形", "回调"), ("非法", "载荷"), ("响应", "中断"),
        ),
        markers=("callbackboundary", "deserialization", "asyncboundary"),
    ),
    BehaviorConcept(
        name="post_action_refresh",
        trigger_groups=(
            ("action", "unchanged"), ("action", "stale"),
            ("command", "unchanged"), ("command", "stale"),
            ("completes", "unchanged"),
            ("操作", "未刷新"), ("操作", "不变"), ("命令", "陈旧"),
        ),
        markers=(
            "actiondispatch", "lifecyclesync", "statewrite", "repositoryboundary",
        ),
    ),
    BehaviorConcept(
        name="event_state_handoff",
        trigger_groups=(
            ("previously", "selected"), ("previous", "item"),
            ("wrong", "row"), ("state", "handoff"),
            ("上一个", "条目"), ("错误", "行"), ("状态", "交接"),
        ),
        markers=("eventboundary", "statehandoff", "statewrite"),
    ),
    BehaviorConcept(
        name="gesture_state_transition",
        trigger_groups=(
            ("gesture",), ("swipe",), ("drag", "board"),
            ("拖动",), ("手势",), ("滑动", "状态"),
        ),
        markers=("gestureboundary",),
    ),
    BehaviorConcept(
        name="touch_state_arbitration",
        trigger_groups=(
            ("touch", "conflict"), ("touch", "arbitration"),
            ("gesture", "conflict"), ("handlers", "resizing"),
            ("gesture", "state"), ("multiple", "fingers"),
            ("触摸", "冲突"), ("手势", "冲突"), ("交互", "竞争"),
        ),
        markers=("gestureboundary", "statewrite"),
    ),
    BehaviorConcept(
        name="touch_access_safety",
        trigger_groups=(
            ("touch", "empty"), ("finger", "missing"),
            ("pointer", "missing"), ("first", "finger"),
            ("触摸", "为空"), ("手指", "缺失"), ("指针", "缺失"),
        ),
        markers=("touchboundary", "indexedread"),
    ),
    BehaviorConcept(
        name="adjacent_collection_mutation",
        trigger_groups=(
            ("adjacent",), ("neighbor", "toggle"),
            ("propagate", "selection"), ("propagate", "click"),
            ("相邻",), ("邻接",), ("传播", "选择"),
        ),
        markers=("eventboundary", "collectionwrite"),
    ),
    BehaviorConcept(
        name="validation_stop",
        trigger_groups=(
            ("required", "still"), ("error", "still"),
            ("invalid", "submit"), ("empty", "submit"),
            ("invalid", "dispatch"), ("validation", "dispatch"),
            ("校验", "仍"),
            ("必填", "提交"), ("错误", "提交"),
        ),
        markers=("validationguard", "actiondispatch"),
    ),
    BehaviorConcept(
        name="persistence_boundary",
        trigger_groups=(
            ("persistence",), ("dispatch", "storage"),
            ("write", "storage"), ("not", "persisted"),
            ("未持久化",), ("持久化",), ("写入", "存储"),
        ),
        markers=("persistencewrite",),
    ),
    BehaviorConcept(
        name="counter_timestamp_commit",
        trigger_groups=(
            ("counter", "restart"), ("last-used", "restart"),
            ("usage", "persist"), ("counter", "timestamp"),
            ("计数", "重启"), ("时间", "重启"),
        ),
        markers=("persistencewrite", "countertimestampwrite"),
    ),
    BehaviorConcept(
        name="lifecycle_persistence",
        trigger_groups=(
            ("saved", "relaunch"), ("restore", "lifecycle"),
            ("resets", "relaunch"), ("restart", "restore"),
            ("重启", "恢复"), ("重启", "保存"), ("生命周期", "持久化"),
        ),
        markers=("lifecyclesync", "statewrite", "persistencewrite"),
    ),
    BehaviorConcept(
        name="conditional_data_loading",
        trigger_groups=(
            ("folder", "empty"), ("nested", "load"),
            ("recursive", "load"), ("collection", "empty"),
            ("文件夹", "为空"), ("嵌套", "加载"), ("递归", "加载"),
        ),
        markers=("conditionalbranch", "datasourceboundary"),
    ),
    BehaviorConcept(
        name="lifecycle_callback_cleanup",
        trigger_groups=(
            ("context", "destroy"), ("window", "cleanup"),
            ("listener", "unregister"), ("shutdown", "callback"),
            ("上下文", "销毁"), ("窗口", "清理"), ("监听", "注销"),
        ),
        markers=("lifecycleboundary", "callbackcleanup"),
    ),
    BehaviorConcept(
        name="media_resource_shutdown",
        trigger_groups=(
            ("recording", "stops"), ("capture", "stops"),
            ("media", "release"), ("audio", "release"),
            ("resource", "release"), ("resource", "destroy"),
            ("recorder", "shutdown"), ("capturer", "shutdown"),
            ("录音", "停止"), ("采集", "停止"), ("媒体", "释放"),
            ("资源", "释放"), ("资源", "销毁"),
        ),
        markers=("resourcerelease",),
    ),
    BehaviorConcept(
        name="keyboard_back_event",
        trigger_groups=(
            ("keyboard", "back"), ("back", "key"),
            ("key", "search", "conflict"), ("physical", "keyboard", "back"),
            ("返回键",), ("按键", "搜索", "冲突"),
        ),
        markers=("keyboundary", "backkeyguard"),
    ),
    BehaviorConcept(
        name="async_state_ordering",
        trigger_groups=(
            ("rapid", "navigation"), ("repeated", "stale"),
            ("async", "stale"), ("out-of-order",), ("out", "order"),
            ("older", "asynchronous"), ("loading", "state", "assignment"),
            ("快速", "跳转"), ("连续", "陈旧"), ("异步", "竞态"),
        ),
        markers=("asyncboundary", "orderingguard", "statewrite"),
    ),
    BehaviorConcept(
        name="guarded_async_action",
        trigger_groups=(
            ("submitted", "twice"), ("repeat", "click"),
            ("guards", "pending"), ("pending", "state"),
            ("resets", "finally"), ("restores", "pending"),
            ("重复", "提交"), ("pending", "防重"), ("finally", "复位"),
        ),
        markers=("conditionalbranch", "statewrite", "asyncboundary"),
    ),
    BehaviorConcept(
        name="ui_command_binding",
        trigger_groups=(
            ("menu", "command"), ("menu", "entry", "invokes"),
            ("ui", "action", "dispatch"), ("action-to-method",),
            ("菜单", "命令"), ("菜单项", "方法"), ("命令", "绑定"),
        ),
        markers=("commandbinding",),
    ),
    BehaviorConcept(
        name="disclosure_state_binding",
        trigger_groups=(
            ("details", "chevron"), ("expanded", "indicator"),
            ("disclosure", "state"), ("rotation", "toggle"),
            ("详情", "箭头"), ("展开", "方向"), ("rotate", "展开"),
        ),
        markers=("disclosurestate",),
    ),
    BehaviorConcept(
        name="error_handoff_contract",
        trigger_groups=(
            ("raw", "error", "value"), ("failure", "details"),
            ("producer", "consumer", "handling"),
            ("service", "return", "ui"),
            ("错误对象",), ("服务层", "页面层"), ("catch", "返回值"),
        ),
        markers=("errorreturnboundary", "errorpresentationboundary"),
    ),
)

def behavior_marker_terms(query: str) -> list[str]:
    positive_query = positive_retrieval_query(query)
    lowered = positive_query.casefold()
    indexed_terms = set(query_tokens(positive_query))
    return unique_list([
        marker
        for concept in BEHAVIOR_CONCEPTS
        if any(
            all(trigger_present(trigger, lowered, indexed_terms) for trigger in group)
            for group in concept.trigger_groups
        )
        for marker in concept.markers
    ])


def trigger_present(trigger: str, lowered: str, indexed_terms: set[str]) -> bool:
    normalized = trigger.casefold()
    if normalized.isascii() and normalized.isalnum():
        return normalized in indexed_terms or any(
            (
                term.startswith(normalized)
                and term[len(normalized):] in {"s", "ed", "ing"}
            ) or term == f"{normalized}{normalized[-1]}ing"
            for term in indexed_terms
        )
    return normalized in lowered


def matching_behavior_markers(index_text: str, query: str) -> list[str]:
    indexed = {term.casefold() for term in terms_from_text(index_text)}
    return [marker for marker in behavior_marker_terms(query) if marker in indexed]
