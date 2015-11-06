=================
Target Extensions
=================

Subunit2SQL is meant to be generic. But while processing subunit streams,
you may have some site-specific behavior you'd like to enable, such as
loading attachments into a storage location that can be extracted later.

To do this, you must create a plugin in the `subunit2sql.target` entry
point namespace, and it will be invoked along with the other targets
that subunit2sql invokes normally to store tests in a SQL database.

The plugin's entry point should be a class that extends
`testtools.StreamResult`.  It should also add a class method, `enabled`,
which returns False if the plugin has no chance of functioning. The
`enabled` method can also do any configuration file preparation if you
are using oslo.config. The constructor will not be executed until after
all config options are loaded.
