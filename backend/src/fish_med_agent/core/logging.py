import logging
import sys
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any

from loguru import logger as _logger

from fish_med_agent.core.config import settings

DEFAULT_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "request_id={extra[request_id]} | "
    "<cyan>{extra[source_name]}</cyan>:<cyan>{extra[source_function]}</cyan>:"
    "<cyan>{extra[source_line]}</cyan> - "
    "<level>{message}</level>{exception}"
)

STANDARD_LOGGER_NAMES = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "alembic",
)

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="system")
_configured = False


def _to_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "on"}


def _patch_record(record: dict[str, Any]) -> None:
    record["extra"].setdefault("request_id", _request_id_ctx.get())
    record["extra"].setdefault("logger_name", record["name"])
    record["extra"].setdefault("source_name", record["extra"]["logger_name"])
    record["extra"].setdefault("source_function", record["function"])
    record["extra"].setdefault("source_line", record["line"])


class _InterceptHandler(logging.Handler):
    """
    将标准库 logging 记录转发到 loguru。
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        _logger.bind(
            logger_name=record.name,
            source_name=record.name,
            source_function=record.funcName,
            source_line=record.lineno,
        ).opt(exception=record.exc_info).log(level, record.getMessage())


def _configure_standard_logging(level: str, logger_names: tuple[str, ...]) -> None:
    intercept_handler = _InterceptHandler()

    logging.basicConfig(handlers=[intercept_handler], level=level, force=True)

    for logger_name in _iter_logger_names(logger_names):
        std_logger = logging.getLogger(logger_name)
        std_logger.handlers.clear()
        std_logger.setLevel(level)
        std_logger.propagate = True


def _iter_logger_names(logger_names: tuple[str, ...]) -> set[str]:
    names = set(logger_names)
    prefixes = tuple(f"{logger_name}." for logger_name in logger_names)

    for logger_name in logging.root.manager.loggerDict:
        if logger_name in names or logger_name.startswith(prefixes):
            names.add(logger_name)

    return names


def configure_logging(
    *,
    level: str | None = None,
    json_logs: bool | None = None,
    log_file: str | Path | None = None,
    rotation: str = "100 MB",
    retention: str = "14 days",
    standard_logger_names: tuple[str, ...] = STANDARD_LOGGER_NAMES,
) -> None:
    """
    配置应用日志。

    环境变量:
        LOG_LEVEL: 日志级别, 默认 INFO
        LOG_JSON: 是否输出 JSON 日志, 默认 false
        ENV: prod 时关闭 diagnose, 避免输出过多调试信息
    """
    global _configured

    log_level = (level or settings.LOG_LEVEL or "INFO").upper()
    serialize = _to_bool(json_logs, _to_bool(settings.LOG_JSON))
    diagnose = settings.ENV != "prod"

    _logger.remove()
    _logger.configure(patcher=_patch_record)
    _logger.add(
        sys.stderr,
        level=log_level,
        format=DEFAULT_LOG_FORMAT,
        colorize=not serialize,
        serialize=serialize,
        backtrace=True,
        diagnose=diagnose,
        enqueue=True,
    )

    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _logger.add(
            log_path,
            level=log_level,
            format=DEFAULT_LOG_FORMAT,
            rotation=rotation,
            retention=retention,
            backtrace=True,
            diagnose=diagnose,
            enqueue=True,
        )

    _configure_standard_logging(log_level, standard_logger_names)
    _configured = True


def get_logger(name: str | None = None, **context: Any):
    """
    获取带业务上下文的 logger。

    Args:
        name: 日志记录器名称, 推荐传入 __name__
        context: 需要绑定到日志 extra 的上下文字段
    """
    if not _configured:
        configure_logging()

    logger = _logger.bind(logger_name=name or "fish_med_agent")
    if context:
        logger = logger.bind(**context)
    return logger


def set_request_id(request_id: str) -> Token[str]:
    """
    设置当前上下文的请求 ID。
    """
    return _request_id_ctx.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    """
    重置当前上下文的请求 ID。
    """
    _request_id_ctx.reset(token)


def get_request_id() -> str:
    """
    获取当前上下文的请求 ID。
    """
    return _request_id_ctx.get()


logger = get_logger()
