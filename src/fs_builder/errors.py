"""项目级异常定义。"""


class FSBuilderError(Exception):
    """所有面向用户的业务异常都应继承自这里。"""


class ConfigError(FSBuilderError):
    """配置缺失或配置值非法。"""


class CLIError(FSBuilderError):
    """参数在 argparse 通过后仍然不满足业务约束。"""


class PlanValidationError(FSBuilderError):
    """Plan 无法解析或不满足 schema 约束。"""
