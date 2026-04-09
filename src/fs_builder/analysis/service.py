"""分析服务编排。"""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from ..errors import PlanValidationError
from ..models import AssemblyPlan, validate_plan_data
from ..settings import Settings
from .errors import AnalysisError
from .fallbacks import match_demo_fallback
from .parsing import parse_analysis_payload
from .provider import AnalysisRequester, request_analysis_content


@dataclass(frozen=True)
class RequirementAnalyzer:
    """需求分析入口。

    这里负责把 provider 调用、输出解析、schema 校验和 demo fallback 串成稳定流程，
    避免 CLI 或单个模块同时承担太多职责。
    """

    settings: Settings

    def analyze(
        self,
        requirement: str,
        *,
        client: OpenAI | None = None,
        requester: AnalysisRequester | None = None,
    ) -> AssemblyPlan:
        cleaned_requirement = requirement.strip()
        if not cleaned_requirement:
            raise AnalysisError("需求文本不能为空。")

        try:
            content = request_analysis_content(
                requirement=cleaned_requirement,
                settings=self.settings,
                client=client,
                requester=requester,
            )
            data = parse_analysis_payload(content)
            return validate_plan_data(data)
        except (AnalysisError, PlanValidationError):
            fallback_plan = match_demo_fallback(cleaned_requirement)
            if fallback_plan is not None:
                return fallback_plan
            raise


def analyze_requirement(
    requirement: str,
    settings: Settings,
    *,
    client: OpenAI | None = None,
    requester: AnalysisRequester | None = None,
) -> AssemblyPlan:
    return RequirementAnalyzer(settings).analyze(
        requirement,
        client=client,
        requester=requester,
    )
