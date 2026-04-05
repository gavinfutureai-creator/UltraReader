"""
异常定义

UltraReader 异常层次结构
"""


class UltraReaderError(Exception):
    """UltraReader 基础异常"""
    pass


class LLMError(UltraReaderError):
    """LLM 相关错误"""
    pass


class LLMConnectionError(LLMError):
    """无法连接到 LLM 服务"""
    pass


class LLMTimeoutError(LLMError):
    """LLM 生成超时"""
    pass


class LLMResponseError(LLMError):
    """LLM 响应格式错误"""
    pass


class EbookError(UltraReaderError):
    """电子书处理错误"""
    pass


class EbookFormatError(EbookError):
    """不支持的格式"""
    pass


class EbookParseError(EbookError):
    """电子书解析失败"""
    pass


class ConfigError(UltraReaderError):
    """配置错误"""
    pass


class ProcessingError(UltraReaderError):
    """处理过程错误"""
    pass


class ContextOverflowError(ProcessingError):
    """上下文超出限制"""
    pass
