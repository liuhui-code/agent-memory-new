"""Whole finite request; observation never supplies source or safety facts."""
import re

_PATTERN = re.compile(
    r'(?:(?:触摸事件为空时第一个手指缺失并导致交互异常|触摸输入没有首个触点时界面操作异常)，)?'
    r'(?:请定位|请查找|请只返回)'
    r'(?:触摸回调和索引读取所在源码|触摸回调中按字面量索引读取触点的源码)'
    r'。?')


def touch_index_request(query):
    return True if type(query) is str and len(query) <= 120 and _PATTERN.fullmatch(query) else None
