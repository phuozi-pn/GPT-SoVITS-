"""
Alembic 迁移环境配置 — 从 voice_platform.config.Settings 读取数据库 URL。

Usage:
    cd GPT
    alembic -c infra/docker/alembic.ini upgrade head       # 执行所有迁移
    alembic -c infra/docker/alembic.ini revision --autogenerate -m "desc"
    alembic -c infra/docker/alembic.ini stamp head          # 标记当前状态（已有 DB 时）
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from voice_platform.config import get_settings

# Alembic Config 对象
config = context.config

# 设置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 从项目配置读取数据库 URL（不使用 alembic.ini 中的硬编码值）
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# 暂不使用 ORM MetaData autogenerate（项目使用原始 SQL 迁移）
target_metadata = None


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本而非连接数据库。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库并执行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
