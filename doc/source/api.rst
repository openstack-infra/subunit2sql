=================================
Guide to subunit2sql's Python API
=================================


DB API Guide
------------
   .. include:: db_api.rst

Example usage patterns
----------------------

Initializing subunit2sql
`````````````````````````

The first step to using subunit2sql inside your program is to initialize the db
layer client. This can be accomplished just by loading the config followed by
setting the necessary values::

    from subunit2sql import shell


    # Load default config
    shell.parse_args([])
    # Set database connection
    db_uri = 'mysql://subunit:subunit@localhost/subunit'
    shell.CONF.set_override('connection', db_uri, group='database')

However, if your already using oslo.config in your program you should just use
the options from subunit2sql instead of this step. See the oslo.config
documentation on how to do this. These steps are provided to avoid using
oslo.config in any consumers of subunit2sql.

Additionally you can use a separate subunit2sql config file in your program to
specify these options and just pass that config file into subunit2sql::

    from subunit2sql import shell

    subunit2sql_conf_path = './subunit2sql.conf'
    # Initialize subunit2sql config
    shell.parse_args([], [subunit2sql_conf_path])

The tradeoff here is that you have to have a file available to configure
subunit2sql.


Another alternative is to initialize a sqlalchemy engine to create a session
with the appropriate db url. This session can then be passed to all API calls
without having to deal with oslo.config::

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create engine with db url for session generation
    engine=create_engine('mysql://subunit:subunit@localhost/subunit')
    Session = sessionmaker(bind=engine)

    # Create a new session to pass to API calls
    # EX: api.get_run_metadata(session=session)
    session = Session()


Parsing subunit stream and storing it in a DB
`````````````````````````````````````````````

If your program is generating a subunit stream or reading one from somewhere
and you'd like to integrate storing it into a subunit2sql db inline this can
easily be accomplished by first parsing the file object and then writing that to the
db.::

    from subunit2sql import shell
    from subunit2sql import read_subunit


    subunit_file = open('subunit_file', 'r')
    # Load default config
    shell.cli_opts()
    shell.parse_args([])
    # Set database connection
    db_uri = 'mysql://subunit:subunit@localhost/subunit'
    shell.CONF.set_override('connection', db_uri, group='database')
    # Parse results and write to DB
    stream = read_subunit.ReadSubunit(subunit_file)
    shell.process_results(stream.get_results())

If you'd like to set additional metadata for the runs you are adding to the DB
you can do this by overriding the conf variables. However, you'll need to load
the options (which would normally be set on the cli todo this, which looks
like::

    from subunit2sql import shell
    from subunit2sql import read_subunit


    subunit_file = open('subunit_file', 'r')
    # Load default config
    shell.cli_opts()
    shell.parse_args([])
    # Set database connection
    db_uri = 'mysql://subunit:subunit@localhost/subunit'
    shell.CONF.set_override('connection', db_uri, group='database')
    # Set run metadata and artifact path
    artifacts = 'http://fake_url.com'
    metadata = {
        'job_type': 'full-run',
        'job_queue': 'gate',
        'build_id': 'fun_hash'
    }
    shell.CONF.set_override('artifacts', artifacts)
    shell.CONF.set_override('run_meta', metadata)
    # Parse results and write to DB
    stream = read_subunit.ReadSubunit(subunit_file)
    shell.process_results(stream.get_results())

keep in mind that oslo.config uses a global object to store options so if you're
considering doing this in parallel somehow that may be something to consider.
