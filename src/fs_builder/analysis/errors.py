"""分析链路专用异常。"""

from __future__ import annotations

from ..errors import FSBuilderError


class AnalysisError(FSBuilderError):
    """分析阶段的基类异常。"""


class AnalysisRequestError(AnalysisError):
    """调用分析模型或兼容接口失败。"""


class AnalysisEmptyResponseError(AnalysisError):
    """分析模型返回空内容。"""


class AnalysisOutputParseError(AnalysisError):
    """分析模型返回了无法解析的内容。"""
