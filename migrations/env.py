from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.core.config import get_settings
from backend.app.core.database import Base
from backend.app.domains.beneficiaries import models as beneficiaries_models
from backend.app.domains.identity import models as identity_models
from backend.app.domains.inheritance import models as inheritance_models
from backend.app.domains.legacy import models as legacy_models
from backend.app.domains.notifications import models as notifications_models
from backend.app.domains.security import models as security_models
from backend.app.domains.subscriptions import models as subscriptions_models
from backend.app.domains.succession import models as succession_models
from backend.app.domains.vault import models as vault_models
from backend.app.domains.verification import models as verification_models

_ = (
    identity_models,
    vault_models,
    beneficiaries_models,
    inheritance_models,
    security_models,
    notifications_models,
    subscriptions_models,
    verification_models,
    legacy_models,
    succession_models,
)

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

