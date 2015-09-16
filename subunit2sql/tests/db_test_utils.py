# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import tempfile

from alembic import command
from alembic import config as alembic_config
from oslo_config import cfg
import sqlalchemy

from subunit2sql.db import api as session

CONF = cfg.CONF
SQLITE_TEST_DATABASE_PATH = tempfile.mkstemp('subunit2sql.db')[1]

script_location = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'migrations')


def get_connect_string(backend,
                       user="openstack_citest",
                       passwd="openstack_citest",
                       database="openstack_citest"):
    """Generate a db uri for testing locally.

    Try to get a connection with a very specific set of values, if we get
    these then we'll run the tests, otherwise they are skipped
    """
    if backend == "mysql":
        backend = "mysql+mysqldb"
    elif backend == "postgres":
        backend = "postgresql+psycopg2"

    if backend == "sqlite":
        return "sqlite:///" + SQLITE_TEST_DATABASE_PATH

    return ("%(backend)s://%(user)s:%(passwd)s@localhost/%(database)s"
            % {'backend': backend, 'user': user, 'passwd': passwd,
               'database': database})


def is_backend_avail(backend,
                     user="openstack_citest",
                     passwd="openstack_citest",
                     database="openstack_citest"):
    try:
        if backend == "mysql":
            connect_uri = get_connect_string("mysql", user=user,
                                             passwd=passwd, database=database)
        elif backend == "postgres":
            connect_uri = get_connect_string("postgres", user=user,
                                             passwd=passwd, database=database)
        engine = sqlalchemy.create_engine(connect_uri)
        connection = engine.connect()
    except Exception:
        # intentionally catch all to handle exceptions even if we don't
        # have any backend code loaded.
        return False
    else:
        connection.close()
        engine.dispose()
        return True


def run_migration(target, engine=None):
    engine = engine or session.get_engine()
    engine.connect()
    config = alembic_config.Config(os.path.join(script_location,
                                                'alembic.ini'))
    config.set_main_option('script_location', 'subunit2sql:migrations')
    config.subunit2sql_config = CONF
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, target)
    engine.dispose()
