'''
Created on Nov 22, 2010

@author: spike
'''

from scalarizr.bus import bus
from scalarizr.handlers import HandlerError
from scalarizr.handlers import rebundle as rebundle_hdlr
from scalarizr.util import wait_until, system2

import time
import sys

from cloudservers import ImageManager
from cloudservers.exceptions import CloudServersException


LOG = rebundle_hdlr.LOG

def get_handlers ():
	return [RackspaceRebundleHandler()]


class RackspaceRebundleHandler(rebundle_hdlr.RebundleHandler):

	def rebundle(self):
		image_name = self._role_name + "-" + time.strftime("%Y%m%d%H%M%S")

		pl = bus.platform
		con = pl.new_cloudservers_conn()
		servers = con.servers.list()

		LOG.info('Lookup server %s on CloudServers', pl.get_public_ip())
		for server in servers:
			if server.public_ip == pl.get_public_ip():
				break
		else:
			raise HandlerError('Server %s not found in servers list' % pl.get_public_ip())
		
		LOG.debug('Found server %s. server id: %s', pl.get_public_ip(), server.id)

		image = None
		try:
			image_manager = ImageManager(con)
			system2("sync", shell=True)
			LOG.info("Creating server image. server id: %s, image name: '%s'", server.id, image_name)
			try:
				image = image_manager.create(image_name, server.id)
			except CloudServersException, e:
				if 'Cannot create a new backup request while saving a prior backup or migrating' in str(e):
					raise HandlerError('Another image is currently creating from this server. '
							'Rackspace allows to create only ONE image per server at a time. '
							'Try again later')
				raise
			LOG.debug('Image %s created', image.id)

			LOG.info('Checking that image %s is completed', image.id)
			
			start_time = time.time()
			def completed(image_id):
				try:
					image = image_manager.get(image_id)
					if time.time() - start_time > 191:
						globals()['start_time'] = time.time()
						LOG.info('Progress: %s', image.progress)
					return image.status in ('ACTIVE', 'FAILED')
				except:
					LOG.debug('Caught exception', exc_info=sys.exc_info())
			
			wait_until(completed, args=(image.id, ), sleep=30, logger=LOG, timeout=3600,
					error_text="Image %s wasn't completed in a reasonable time" % image.id)
			image = image_manager.get(image.id)
			if image.status == 'FAILED':
				raise HandlerError('Image %s becomes failed' % image.id)
			LOG.info('Image %s completed and available for use!', image.id)
		except:
			exc_type, exc_value, exc_trace = sys.exc_info()
			if image:
				try:
					image_manager.delete(image)
				except:
					pass
			raise exc_type, exc_value, exc_trace
		
		return image.id

			