# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement
from alembic import context
from logging.config import fileConfig  # noqa

from subunit2sql.db import api as db_api


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
subunit2sql_config = config.subunit2sql_config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    kwargs = dict()
    if subunit2sql_config.database.connection:
        kwargs['url'] = subunit2sql_config.database.connection
    elif subunit2sql_config.database.engine:
        kwargs['dialect_name'] = subunit2sql_config.database.engine
    else:
        kwargs['url'] = config.get_main_option("sqlalchemy.url")
    kwargs['target_metadata'] = target_metadata
    kwargs['render_as_batch'] = True
    context.configure(**kwargs)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    facade = db_api._create_facade_lazily()
    engine = facade.get_engine()
    connection = engine.connect()
    facade._session_maker.configure(bind=connection)

    context.configure(connection=connection,
                      target_metadata=target_metadata,
                      render_as_batch=True)

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()
        facade._session_maker.configure(bind=engine)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
