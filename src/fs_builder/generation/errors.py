"""生成链路异常。"""

from __future__ import annotations

from ..errors import FSBuilderError


class GenerationError(FSBuilderError):
    """生成阶段基类异常。"""


class PartRenderError(GenerationError):
    """某个零件无法按模板渲染。"""
