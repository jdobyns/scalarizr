# pylint: disable=R0924

import urllib2
import json
import logging
import re
import os
import sys
import posixpath
import glob
import operator
from multiprocessing import pool as process_pool

from scalarizr import linux


LOG = logging.getLogger(__name__)


class Error(Exception):
    pass

class NoProviderError(Error):
    pass

class NoUserDataError(Error):
    pass


class Userdata(dict):
    @classmethod
    def from_string(cls, data):
        return Userdata(re.findall("([^=]+)=([^;]*);?", data))


class VoteCapabilityDict(dict):
    def incr_each(self, value=1):
        for key in self:
            self[key] += value

    def decr_each(self, value=1):
        for key in self:
            self[key] -= value


class VoteDict(dict):
    def __getitem__(self, key):
        try:
            return super(VoteDict, self).__getitem__(key)
        except KeyError:
            for cls, value in self.iteritems():
                if cls.__class__.__name__ == key:
                    return value
            raise


class Metadata(object):

    class NoDataPvd(object):
        def __init__(self, metadata):
            self.metadata = metadata

        def instance_id(self):
            return self.metadata['user_data']['serverid']

        def user_data(self):
            raise NoUserDataError()


    def __init__(self, providers=None, capabilities=None):
        self._cache = {}
        self._provider_for_capability = {}
        self._nodata_pvd = self.NoDataPvd(self)
        self._providers_resolved = False
        if not providers:
            if linux.os.windows:
                providers = [
                    Ec2Pvd(),
                    OpenStackQueryPvd(),
                    FileDataPvd('C:\\Program Files\\Scalarizr\\etc\\private.d\\.user-data')
                ]
            else:
                providers = [
                    Ec2Pvd(),
                    GcePvd(),
                    OpenStackQueryPvd(),
                    OpenStackXenStorePvd(),
                    CloudStackPvd(),
                    FileDataPvd('/etc/.scalr-user-data'),
                    FileDataPvd('/etc/scalr/private.d/.user-data')
                ]
        self.providers = providers
        self.capabilities = capabilities or ['instance_id', 'user_data']


    def _resolve_once_providers(self):
        if self._providers_resolved:
            return  
        votes = VoteDict()
        for pvd in self.providers:
            votes[pvd] = VoteCapabilityDict.fromkeys(self.capabilities, 0)
        def vote(pvd):
            try:
                pvd.vote(votes)
            except:
                LOG.debug('{0}.vote raised: {1}'.format(
                        pvd.__class__.__name__, sys.exc_info()[1]))
        pool = process_pool.ThreadPool(processes=len(self.providers))
        try:
            pool.map(vote, self.providers)
        finally:
            pool.close()
        for cap in self.capabilities:
            cap_votes = ((pvd, votes[pvd][cap]) for pvd in votes)
            cap_votes = sorted(cap_votes, key=operator.itemgetter(1))
            pvd, vote = cap_votes[-1]
            if not vote:
                pvd = self._nodata_pvd
            self._provider_for_capability[cap] = pvd
        self._providers_resolved = True

    def __getitem__(self, capability):
        self._resolve_once_providers()
        if not capability in self._cache:
            try:
                pvd = self._provider_for_capability[capability]
            except KeyError:
                msg = "Can't find a provider for '{0}'".format(capability)
                raise NoProviderError(msg)
            else:
                self._cache[capability] = getattr(pvd, capability)()
        return self._cache[capability]


class Provider(object):
    HTTP_TIMEOUT = 5
    EC2_BASE_URL = 'http://169.254.169.254/latest'
    base_url = None

    def vote(self, votes):
        raise NotImplementedError()

    def try_url(self, url):
        try:
            return self.get_url(url)
        except:
            return False

    def get_url(self, url=None, rel=None, headers=None):
        if rel:
            url = posixpath.join(url or self.base_url, rel)
        return urllib2.urlopen(urllib2.Request(url, headers=headers), 
                timeout=self.HTTP_TIMEOUT).read().strip()

    def try_ec2_url(self):
        return self.try_url(self.EC2_BASE_URL)

    def try_file(self, path):
        return os.access(path, os.R_OK)

    def get_file(self, path):
        with open(path) as fp:
            return fp.read().strip() 


class Ec2Pvd(Provider):
    def __init__(self):
        self.base_url = Provider.EC2_BASE_URL

    def vote(self, votes):
        if self.try_ec2_url():
            votes[self].incr_each()

    def instance_id(self):
        return self.get_url(rel='meta-data/instance-id')

    def user_data(self):
        return Userdata.from_string(
                self.get_url(rel='user-data'))
           

class GcePvd(Provider):
    def __init__(self):
        self.base_url = 'http://metadata/computeMetadata/v1'    

    def get_url(self, url=None, rel=None):
        return super(GcePvd, self).get_url(url, rel, 
                headers={'X-Google-Metadata-Request': 'True'})

    def vote(self, votes):
        if self.try_url(self.base_url):
            votes[self].incr_each()

    def instance_id(self):
        return self.get_url(rel='instance/id')

    def user_data(self):
        return Userdata.from_string(
                self.get_url(rel='instance/attributes/scalr'))
        

class OpenStackQueryPvd(Provider):

    def __init__(self, 
            metadata_json_url='http://169.254.169.254/openstack/latest/meta_data.json'):
        self.metadata_json_url = metadata_json_url
        self._cache = {}

    def vote(self, votes):
        meta = self.try_url(self.metadata_json_url)
        if meta:
            self._cache = json.loads(meta)
            votes[self]['instance_id'] += 1
            votes['Ec2Pvd'].decr_each()
        if 'meta' in self._cache:
            votes[self]['user_data'] += 1

    def instance_id(self):
        return self._cache['instance_id']

    def user_data(self):
        return self._cache['meta']


class OpenStackXenStorePvd(Provider):
    def vote(self, votes):
        if self.try_file('/proc/xen/xenbus') and linux.which('xenstore-ls') \
                and linux.which('nova-agent'):
            votes[self]['user_data'] += 2
            votes['OpenStackQueryPvd']['user_data'] -= 1

    def user_data(self):
        keyvalue_re = re.compile(r'([^\s]+)\s+=\s+\"{2}([^\"]+)\"{2}')
        ret = []
        out = linux.system((linux.which('xenstore-ls'), 'vm-data/user-metadata'))[0]
        for line in out.splitlines():
            m = keyvalue_re.search(line)
            if m:
                ret.append(m.groups())
        return dict(ret)


class CloudStackPvd(Provider):
    def __init__(self, 
            dhcp_server=None, 
            dhcp_leases_pattern='/var/lib/dhc*/dhclient*.leases'):
        self.dhcp_server = dhcp_server
        self.dhcp_leases_pattern = dhcp_leases_pattern

    @property
    def base_url(self):
        if not self.dhcp_server:
            self.dhcp_server = self.get_dhcp_server(self.dhcp_leases_pattern)
            LOG.debug('Use DHCP server: %s', self.dhcp_server)
        return 'http://{0}/latest'.format(self.dhcp_server)

    @classmethod
    def get_dhcp_server(cls, leases_pattern=None):
        router = None
        try:
            leases_file = glob.glob(leases_pattern)[0]
            LOG.debug('Use DHCP leases file: %s', leases_file)
        except IndexError:
            msg = "Pattern {0} doesn't matches any leases files".format(leases_pattern)
            raise Error(msg)
        for line in open(leases_file):
            if 'dhcp-server-identifier' in line:
                router = filter(None, line.split(';')[0].split(' '))[2]
        return router

    def vote(self, votes):
        if self.try_url(self.base_url):
            votes[self].incr_each()
            if self.try_ec2_url():
                votes['Ec2Pvd'].decr_each()

    def instance_id(self):
        value = self.get_url(rel='instance-id')
        if len(value) == 36:
            # uuid-like (CloudStack 3)
            return value
        else:
            # CloudStack 2 / IDCF
            return value.split('-')[2]

    def user_data(self):
        return Userdata.from_string(self.get_url(rel='user-data'))


class FileDataPvd(Provider):
    def __init__(self, filename):
        self.filename = filename

    def vote(self, votes):
        if self.try_file(self.filename):
            votes[self]['user_data'] += 1

    def __repr__(self):
        return '<FileDataPvd at {0} filename={1}>'.format(
                hex(id(self)), self.filename)

    def user_data(self):
        return Userdata.from_string(self.get_file(self.filename))
