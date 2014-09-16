name "scalarizr-deps"

default_version   "0.1"

if linux?
  dependency "rsync"
  dependency "sqlite3"
  dependency "bzip2"
end
dependency "python"
dependency "pip"
dependency "python-prettytable"
dependency "python-pymysql"
dependency "python-simplejson"
dependency "python-pychef"
dependency "python-pexpect"
dependency "python-pysnmp"
dependency "python-pysnmp-mibs"
dependency "python-boto"
dependency "python-novaclient"
dependency "python-rackspace-novaclient"
dependency "python-cinderclient"
dependency "python-swiftclient"
dependency "python-keystoneclient"
dependency "google-api-python-client"
dependency "python-cloudfiles"
dependency "python-cloudservers"
dependency "python-pyyaml"
dependency "cloudstack-python-client"
dependency "python-pymongo"
dependency "python-docopt"
dependency "python-openssl"

if linux?
    dependency "python-m2crypto"
end