"""应用配置：全部通过环境变量 / .env 注入，生产环境可覆盖。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（app 的父目录）
APP_ROOT = Path(__file__).resolve().parent.parent


def _resolve_sqlite_url(url: str, data_dir: Path) -> str:
    """将相对路径的 sqlite url 解析为绝对路径，兼容 SQLite 的 file: 写法。"""
    if url.startswith("sqlite+aiosqlite:///"):
        rest = url[len("sqlite+aiosqlite:///"):]
        if rest and not rest.startswith("/"):
            return f"sqlite+aiosqlite:///{data_dir / rest}"
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "云核软件资产治理平台"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 2
    log_level: str = "info"

    # 数据存储
    data_dir: str = "data"
    database_url: str = ""  # 留空则使用 <data_dir>/app.db

    # DeepSeek LLM（OpenAI 兼容协议）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"
    llm_timeout: int = 180
    llm_max_retries: int = 2
    llm_concurrency: int = 2
    llm_temperature: float = 0.3

    # 代码仓约束
    max_repo_size_mb: int = 200
    clone_timeout: int = 300

    # 单页生成允许的最大源码字符数（token 预算保护）
    max_page_source_chars: int = 90000

    cors_origins: str = "*"

    @property
    def resolved_data_dir(self) -> Path:
        d = Path(self.data_dir)
        if not d.is_absolute():
            d = APP_ROOT / d
        return d

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return _resolve_sqlite_url(self.database_url, self.resolved_data_dir)
        return f"sqlite+aiosqlite:///{self.resolved_data_dir / 'app.db'}"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def repos_root(self) -> Path:
        return self.resolved_data_dir / "repos"

    def repo_source_dir(self, repo_id: str) -> Path:
        return self.repos_root / repo_id / "source"


@lru_cache
def get_settings() -> Settings:
    return Settings()
