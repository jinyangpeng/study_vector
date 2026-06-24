"""配置模块：集中管理应用所有配置项。

提供 Settings 单例，支持多环境（dev/test/prod）配置，
通过 APP_ENV 环境变量切换。配置优先级：环境变量 > .env.{APP_ENV} > .env > 默认值。
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置类。

    Attributes:
        app_env: 运行环境 (dev/test/prod)
        app_name: 应用名称
        app_version: 应用版本
        debug: 是否启用调试模式
        host: 服务监听地址
        port: 服务端口
        milvus_host: Milvus 服务地址
        milvus_port: Milvus 服务端口
        milvus_user: Milvus 用户名
        milvus_password: Milvus 密码
        milvus_db_name: Milvus 数据库名称
        milvus_secure: 是否启用 TLS
        log_level: 日志级别
        log_json: 是否以 JSON 格式输出日志
    """

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # 环境标识
    app_env: Literal["dev", "test", "prod"] = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="study-vector", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")

    # 服务
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Milvus（首期）
    milvus_host: str = Field(default="localhost", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_user: str = Field(default="root", alias="MILVUS_USER")
    milvus_password: str = Field(default="Milvus", alias="MILVUS_PASSWORD")
    milvus_db_name: str = Field(default="default", alias="MILVUS_DB_NAME")
    milvus_secure: bool = Field(default=False, alias="MILVUS_SECURE")

    # 日志
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例（缓存）。

    在 main.py 中根据 APP_ENV 注入具体 env_file。
    """
    return Settings()
