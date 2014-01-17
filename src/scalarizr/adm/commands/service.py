import sys

from scalarizr.bus import bus
from scalarizr.adm.command import Command
from scalarizr.adm.command import CommandError
from scalarizr.node import __node__
from scalarizr.util import initdv2
from scalarizr.api.apache import ApacheInitScript
from scalarizr.handlers.chef import ChefInitScript
from scalarizr.services.haproxy import HAProxyInitScript
from scalarizr.handlers.memcached import MemcachedInitScript
from scalarizr.services.mysql import MysqlInitScript
from scalarizr.api.nginx import NginxAPI
from scalarizr.services.postgresql import PgSQLInitScript
from scalarizr.services.rabbitmq import RabbitMQInitScript


service_apis = {
    'apache': ApacheInitScript,
    'chef': ChefInitScript,
    'haproxy': HAProxyInitScript,
    'mariadb': MysqlInitScript,
    'memcached': MemcachedInitScript,
    # 'mongodb',
    'mysql': MysqlInitScript,
    'nginx': NginxAPI,
    'percona': MysqlInitScript,
    'postgresql': PgSQLInitScript,
    'rabbitmq': RabbitMQInitScript,
    # 'redis',
    # 'tomcat': ,  # TODO: make ParametrizedInitScript subclass for tomcat, or api
}


class Service(Command):
    """
    Usage:
        service (start | stop | status) redis [(<index> | --port=<port>)]
        service (start | stop | status) mongodb [(mongos | mongod | 
            configsrv | configsrv-2 | configsrv-3 | arbiter)]
        service (start | stop | status) <service>
    """

    aliases = ['s']

    def _start_service(self, service, **kwds):
        api = service_apis[service]()
        try:
            api.start_service()
        except (BaseException, Exception), e:
            print 'Service start failed.\n%s' % e
            return int(CommandError())

    def _stop_service(self, service, **kwds):
        api = service_apis[service]()
        try:
            api.stop_service()
        except (BaseException, Exception), e:
            print 'Service stop failed.\n%s' % e
            return int(CommandError())

    def _display_service_status(self, service, **kwds):
        api = service_apis[service]()
        status = api.get_service_status()
        status_string = ' is stopped'
        code = 3
        if status == initdv2.Status.RUNNING:
            status_string = ' is running'
            code = 0
        elif status == initdv2.Status.UNKNOWN:
            status_string = ' has unknown status'
            code = 4
        print service + status_string
        return code

    def __call__(self, 
                 start=False,
                 stop=False,
                 status=False,
                 service=None,

                 redis=False,
                 index=None,
                 port=None,

                 mongodb=False,
                 mongos=False,
                 mongod=False,
                 configsrv=False,
                 configsrv_2=False,
                 configsrv_3=False,
                 arbiter=False,
                 ):
        if redis:
            service = 'redis'
        elif mongodb:
            mongo_component = ((mongos and 'mongos') or
                               (mongod and 'mongod') or
                               (configsrv and 'configsrv') or
                               (configsrv_2 and 'configsrv-2') or
                               (configsrv_3 and 'configsrv-3') or
                               (arbiter and 'arbiter'))
            # TODO: finish

        if service not in service_scripts:
            raise CommandError('Unknown service/behavior.')

        if start:
            return self._start_service(service, index=index, port=port)
        elif stop:
            return self._stop_service(service, index=index, port=port)
        elif status:
            return self._display_service_status(service, index=index, port=port)


commands = [Service]
