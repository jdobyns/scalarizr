import sys
import inspect

from scalarizr.node import __node__
from scalarizr.bus import bus
from scalarizr.adm.command import Command
from scalarizr.adm.command import CommandError
from scalarizr.adm.util import new_queryenv
from scalarizr.api.service import ServiceAPI
from scalarizr.api import operation


class Reconfigure(Command):
    """
    Usage:
        reconfigure [<behavior>]
    """

    def __call__(self, behavior=None):

        if behavior not in behavior_apis:
            raise CommandError('Unknown behavior.')

        api = ServiceAPI()
        # api.init_service()

        try:
            api.reconfigure(async=False)
        except (BaseException, Exception), e:
            print 'Reconfigure failed.\n%s' % e
            return int(CommandError())

        return 0


commands = [Reconfigure]
