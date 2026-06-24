"""日志配置模块：基于 loguru 初始化结构化日志。

dev 环境使用彩色控制台输出便于调试，
prod 环境切换为 JSON 格式便于对接 ELK / Loki 等日志系统。
"""
import sys

from loguru import logger

from study_vector.core.settings import get_settings


def setup_logging() -> None:
    """根据 settings 初始化 loguru。

    全局只保留一个 handler（移除默认），避免重复输出。
    """
    settings = get_settings()
    logger.remove()

    if settings.log_json:
        # 生产可对接 ELK / Loki
        logger.add(
            sys.stdout,
            serialize=True,
            level=settings.log_level,
            enqueue=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
            enqueue=False,
        )
    logger.info(
        f"日志初始化完成 env={settings.app_env} level={settings.log_level} json={settings.log_json}"
    )


__all__ = ["logger", "setup_logging"]
