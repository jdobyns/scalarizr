'''
Created on Nov 24, 2010

@author: marat
@author: Dmytro Korsakov
'''

from scalarizr.bus import bus
from scalarizr.storage import Storage, Volume, VolumeProvider, StorageError, _check_devname_presence
from scalarizr.storage.transfer import TransferProvider, TransferError
from scalarizr.platform.ec2 import ebstool

import os
import logging
from urlparse import urlparse

from boto import connect_ec2, connect_s3
from boto.s3.key import Key
from boto.exception import BotoServerError, S3ResponseError
from scalarizr.util import get_free_devname, wait_until

class EbsVolume(Volume):
	volume_id = None
	def __init__(self,  devname, mpoint=None, fstype=None, type=None, volume_id=None, **kwargs):
		Volume.__init__(self, devname, mpoint, fstype, type)
		self.volume_id = volume_id
		

class EbsVolumeProvider(VolumeProvider):
	type = 'ebs'
	vol_class = EbsVolume
	
	_logger = None
	
	def __init__(self):
		self._logger = logging.getLogger(__name__)
	
	def _create(self, **kwargs):
		'''
		@param id: EBS volume id
		@param size: Size in GB
		@param avail_zone: Availability zone
		@param snapshot_id: Snapshot id
		'''
		ebs_vol = None
		# TODO: check credentials
		conn = connect_ec2()
		pl = bus.platform
		device = kwargs.get('device')
		device = device if (device and not os.path.exists(device)) else get_free_devname()
		attached = False
		
		volume_id = kwargs.get('id')
		try:
			if volume_id:
				''' EBS volume has been already created '''
				
				try:
					ebs_vol = conn.get_all_volumes([volume_id])[0]
				except IndexError:
					raise StorageError("Volume '%s' doesn't exist." % volume_id)
				
				if 'available' != ebs_vol.volume_state():
					self._logger.warning("Volume %s is not available.", ebs_vol.id)
					if ebs_vol.attach_data.instance_id != pl.get_instance_id():
						''' Volume attached to another instance '''
						
						self._logger.debug('Force detaching volume from instance.')
						ebs_vol.detach(True)
						self._logger.debug('Checking that volume %s is available', ebs_vol.id)
						wait_until(lambda: ebs_vol.update() == "available", logger=self._logger)
					else:
						'''Volume attached to this instance'''
						attached = True
						device = kwargs['device'] = ebs_vol.attach_data.device
			else:
				''' Create new EBS '''
				
				ebs_vol = ebstool.create_volume(conn, kwargs['size'], kwargs['zone'], 
					kwargs.get('snapshot_id'), logger=self._logger)
			
			if not attached:
				ebstool.attach_volume(conn, ebs_vol, pl.get_instance_id(), device, 
					to_me=True, logger=self._logger)
			
			
			self._logger.debug("Checking that volume %s is attached", ebs_vol.id)
			wait_until(lambda: ebs_vol.update() and ebs_vol.attachment_state() == "attached", logger=self._logger)
			self._logger.debug("Volume %s attached",  ebs_vol.id)
				
			''' Wait when device will be added '''
			self._logger.debug("Checking that device %s is available", device)
			wait_until(lambda: os.access(device, os.F_OK | os.R_OK), logger=self._logger)
			self._logger.debug("Device %s is available", device)
		except (Exception, BaseException), e:
			if ebs_vol:
				# detach volume
				if (ebs_vol.update() and ebs_vol.attachment_state() != 'attached'):
					ebs_vol.detach(force=True)
					wait_until(lambda: ebs_vol.update() and ebs_vol.attachment_state() == 'available',
							   logger = self._logger)				
				if not volume_id:
					ebs_vol.delete()
					
			raise StorageError('Volume creating failed: %s' % e)		
		kwargs['volume_id'] = ebs_vol.id
		return super(EbsVolumeProvider, self).create(**kwargs)

	create = _create
	
	def create_from_snapshot(self, **kwargs):
		'''
		@param size: Size in GB
		@param avail_zone: Availability zone
		@param id: Snapshot id
		'''
		kwargs['snapshot_id'] = kwargs['id']
		return self._create(**kwargs)

	def create_snapshot(self, vol, snap):
		conn = connect_ec2()
		ebs_snap = conn.create_snapshot(vol.volume_id, snap.description)
		snap.id = dict(type=self.type, id=ebs_snap.id)
		return snap

	def destroy(self, vol):
		'''
		@type vol: EbsVolume
		'''
		super(EbsVolumeProvider, self).destroy(vol)
		conn = connect_ec2()
		conn.delete_volume(vol.volume_id)
	
	@_check_devname_presence		
	def detach(self, vol, force=False):
		super(EbsVolumeProvider, self).detach(vol)
		try:
			key_id 	   = os.environ['AWS_ACCESS_KEY_ID']
			secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
		except KeyError:
			raise Exception("Can't get AWS credentials from OS environment variables.")
		
		con = connect_ec2(key_id, secret_key)
		try:
			result = con.detach_volume(vol.volume_id)
			if not result:
				raise Exception("Can't detach volume %s." % vol.volume_id)
		except:
			if force:
				con.detach_volume(vol.volume_id, force=True)
			else:
				raise
		vol.devname = None


Storage.explore_provider(EbsVolumeProvider, default_for_snap=True)


class S3TransferProvider(TransferProvider):
	
	schema	= 's3'
	acl		= None
	
	def __init__(self, acl=None):
		self._logger = logging.getLogger(__name__)
		self.acl = acl

	def configure(self, remote_path, force=False):
		o = urlparse(remote_path)

		if o.scheme != self.schema:
			raise TransferError('Wrong schema.')		
		try:
			s3_key_id = os.environ["AWS_ACCESS_KEY_ID"]
			s3_secret_key = os.environ["AWS_SECRET_ACCESS_KEY"]
		except KeyError:
			raise TransferError("Can't get S3 credentials from environment variables.")
		
		s3_con = connect_s3(s3_key_id, s3_secret_key)
		try:
			self.bucket = s3_con.get_bucket(o.hostname)
		except S3ResponseError, e:
			if 'NoSuchBucket' in str(e) and force:
				self.bucket = s3_con.create_bucket(o.hostname)
			else:
				raise
			
		self.prefix = o.path

	
	def put(self, local_path, remote_path):
		self._logger.info("Uploading '%s' to S3 bucket '%s'", local_path, self.bucket.name)
		file = None
		base_name = os.path.basename(local_path)
		obj_path = os.path.join(self.prefix, base_name) if self.prefix else base_name
		try:
			key = Key(self.bucket)
			key.name = obj_path
			file = open(local_path, "rb")			
			key.set_contents_from_file(file, policy=self.acl)
			
		except (BotoServerError, OSError), e:
			raise TransferError, e
		finally:
			if file:
				file.close()
		
		return os.path.join(self.bucket.name, key.name)

	
	def get(self, filename, dest):
		dest_path = os.path.join(dest, os.path.basename(filename))
		try:
			key = self.bucket.get_key(filename)
			key.get_contents_to_filename(dest_path)
		except (BotoServerError, OSError), e:
			raise TransferError, e
		return os.path.join(self.bucket.name, dest_path)
	
	def list(self, url=None):
		prefix = urlparse(url).path[1:] if url else self.prefix
		if not prefix:
			prefix = ''
		files = [key.name for key in self.bucket.list(prefix=prefix)] 
		return files
	
def location_from_region(region):
	if region == 'us-east-1' or not region:
		return ''
	elif region == 'eu-west-1':
		return 'EU'
	else: 
		return region
