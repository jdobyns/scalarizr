'''
Created on 29.02.2012

@author: marat
@author: sam
'''

from scalarizr.util import disttool	
from scalarizr.util import system2

import logging
import re
import string
import sys, os
import imp
import ConfigParser as configparser

LOG = logging.getLogger(__name__)

'''----------------------------------
# Package managers
----------------------------------'''
class PackageMgr(object):
	def __init__(self):
		self.proc = None

	def install(self, name, version, *args):
		''' Installs a `version` of package `name` '''
		raise NotImplemented()

	def _join_packages_str(self, sep, name, version, *args):
		packages = [(name, version)]
		if args:
			for i in xrange(0, len(args), 2):
				packages.append(args[i:i+2])
		format = '%s' + sep +'%s'
		return ' '.join(format % p for p in packages)		

	def check_update(self, name):
		''' Returns info for package `name` '''
		raise NotImplemented()

	def candidates(self, name):
		''' Returns all available installation candidates for `name` '''
		raise NotImplemented()


class AptPackageMgr(PackageMgr):
	def apt_get_command(self, command, **kwds):
		kwds.update(env={
			'DEBIAN_FRONTEND': 'noninteractive', 
			'DEBIAN_PRIORITY': 'critical',
			'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/'\
					'sbin:/bin:/usr/games'
		})
		LOG.debug('apt_get_command `%s`', ' '.join(('apt-get', '-q', '-y') + 
				tuple(filter(None, command.split()))))
		return system2(('apt-get', '-q', '-y') + \
				tuple(filter(None, command.split())), **kwds)

	def apt_cache_command(self, command, **kwds):
		return system2(('apt-cache',) + tuple(filter(None, command.split())), **kwds)

	def candidates(self, name):
		version_available_re = re.compile(r'^\s{5}([^\s]+)\s{1}')
		version_installed_re = re.compile(r'^\s{1}\*\*\*|s{1}([^\s]+)\s{1}')
		
		self.apt_get_command('update')
		
		versions = []
		
		for line in self.apt_cache_command('policy %s' % name)[0].splitlines():
			m = version_available_re.match(line)
			if m:
				versions.append(m.group(1))
			m = version_installed_re.match(line)
			if m:
				break

		versions.reverse()
		return versions

	def check_update(self, name):
		installed_re = re.compile(r'^\s{2}Installed: (.+)$')
		candidate_re = re.compile(r'^\s{2}Candidate: (.+)$')
		installed = candidate = None

		self.apt_get_command('update')
		
		for line in self.apt_cache_command('policy %s' % name)[0].splitlines():
			m = installed_re.match(line)
			if m:
				installed = m.group(1)
				if installed == '(none)':
					installed = None
				continue

			m = candidate_re.match(line)
			if m:
				candidate = m.group(1)
				continue
			
		if candidate and installed:
			if not system2(('dpkg', '--compare-versions', candidate, 'gt',
											installed), raise_exc = False)[2]:
				return candidate
	
	def install(self, name, version, *args):
		self.apt_get_command('install %s' % self._join_packages_str('=', name,
											version, *args), raise_exc=True)


class RpmVersion(object):
	
	def __init__(self, version):
		self.version = version
		self._re_not_alphanum = re.compile(r'^[^a-zA-Z0-9]+')
		self._re_digits = re.compile(r'^(\d+)')
		self._re_alpha = re.compile(r'^([a-zA-Z]+)')
	
	def __iter__(self):
		ver = self.version
		while ver:
			ver = self._re_not_alphanum.sub('', ver)
			if not ver:
				break

			if ver and ver[0].isdigit():
				token = self._re_digits.match(ver).group(1)
			else:
				token = self._re_alpha.match(ver).group(1)
			
			yield token
			ver = ver[len(token):]
			
		raise StopIteration()
	
	def __cmp__(self, other):
		iter2 = iter(other)
		
		for tok1 in self:
			try:
				tok2 = iter2.next()
			except StopIteration:
				return 1
		
			if tok1.isdigit() and tok2.isdigit():
				c = cmp(int(tok1), int(tok2))
				if c != 0:
					return c
			elif tok1.isdigit() or tok2.isdigit():
				return 1 if tok1.isdigit() else -1
			else:
				c = cmp(tok1, tok2)
				if c != 0:
					return c
			
		try:
			iter2.next()
			return -1
		except StopIteration:
			return 0


class YumPackageMgr(PackageMgr):

	def yum_command(self, command, **kwds):
		return system2((('yum', '-d0', '-y') + tuple(filter(None,
												 command.split()))), **kwds)
	def rpm_ver_cmp(self, v1, v2):
		return cmp(RpmVersion(v1), RpmVersion(v2))
	
	def candidates(self, name):
		self.yum_command('clean expire-cache')
		out = self.yum_command('list --showduplicates %s' % name)[0].strip()
		
		version_re = re.compile(r'[^\s]+\s+([^\s]+)')
		lines = map(string.strip, out.splitlines())
		
		try:
			line = lines[lines.index('Installed Packages')+1]
			installed = version_re.match(line).group(1)
		except ValueError:
			installed = None

		versions = [version_re.match(line).group(1) for line in lines[
										lines.index('Available Packages')+1:]]
		if installed:
			versions = [v for v in versions if self.rpm_ver_cmp(v, installed) > 0]

		return versions


	def check_update(self, name):
		self.yum_command('clean expire-cache')
		out, _, code = self.yum_command('check-update %s' % name)
		if code == 100:
			return filter(None, out.strip().split(' '))[1]

	def install(self, name, version, *args):
		self.yum_command('install %s' %  self._join_packages_str('-', name, 
											version, *args), raise_exc=True)

'''---------------------------------
# path to manifest
---------------------------------'''
class Manifest(object):
	_instance = None
	_MANIFEST = '../import.manifest'
	path = None

	def __init__(self, path=None):
		if not self.path:
			self.path = os.path.join(os.path.dirname(__file__), self._MANIFEST)
			if not os.path.exists(self.path):
				self.path = None
				LOG.error('Path to manifest fail - import manifest didn`t found')
		if path:
			if os.path.exists(path):
				self.path = path
			else:
				LOG.debug('Path `%s` not exist try standard`%s`', path, self.path)

	def __new__(cls, *args, **kwargs):
		if not cls._instance:
			cls._instance = super(Manifest, cls).__new__(cls, *args, **kwargs)
		return cls._instance

def setup(path=None):
	Manifest(path)

'''---------------------------------
# extension for import 
---------------------------------'''
class ImpImport(object):
	'''Extension for standard import'''

	def __init__(self, manifest_path=None):
		#available package managers:
		self.pkg_mgrs = {'apt': AptPackageMgr,	'yum': YumPackageMgr}
		if disttool.is_debian_based():
			self.mgr = self.pkg_mgrs['apt']()
		elif disttool.is_redhat_based():
			self.mgr = self.pkg_mgrs['yum']()

		self.conf = configparser.ConfigParser()
		self.conf.read(Manifest(path=manifest_path).path)

		self.sections_to_look = ['apt' if disttool.is_debian_based() else 'yum']
		#['apt', 'apt:ubuntu', 'apt:ubuntu11', 'apt:ubuntu11.10']
		#['yum', 'yum:el', 'yum:el5', 'yum:centos5.7']
		dist = disttool.linux_dist()
		if disttool.is_redhat_based():
			self.sections_to_look += [
				self.sections_to_look[0] + ':' + 'el',
				self.sections_to_look[0] + ':' + 'el' + dist[1].split('.')[0]]
		else:
			self.sections_to_look += [
				self.sections_to_look[0] + ':' + dist[0].lower(),
				self.sections_to_look[0] + ':' + dist[0].lower() + \
					dist[1].split('.')[0]]
		self.sections_to_look.append(self.sections_to_look[0] + ':' + \
				dist[0].lower() + dist[1])
		LOG.debug('expected manifest sections: `%s`', self.sections_to_look)

	def install_pypackage(self, package):
		package = package.lower()
		LOG.debug('install_package %s', package)
		dist_names = self.sections_to_look[0:]
		while len(dist_names) > 0:
			dist_name = dist_names.pop()
			if dist_name in self.conf.sections() and \
						package in self.conf.options(dist_name):
				full_package_name = self.conf.get(dist_name, package)
				LOG.debug('dist_name:%s, package:%s, full_package_name:%s',
						dist_name, package, full_package_name)
				if not self.mgr:
					raise Exception('Can`t install`%s`,pckg manager is unknown'
						% full_package_name)
				version = self.mgr.candidates(full_package_name)
				LOG.debug('ImpImport.install_pypackage: version: %s', version)
				if version:
					self.mgr.install(full_package_name, version[-1])
				else:
					raise Exception, 'Pckg mgr didn`t found actual version'\
						' of `%s`, nothing to do' % full_package_name
				LOG.debug('Package `%s` successfully installed', package)
			else:
				LOG.debug('Didn`t found `%s` in section `%s` import.manifest',
					package, dist_name)

	def find_module(self, full_name, path=None):
		if full_name in sys.modules:
			return self
		name = full_name.split('.')[-1]
		pkg_name = full_name.split('.')[0]
		#LOG.debug('ImpImport.find_modul. name=`%s`, path=`%s`', name, path or '')
		try:
			self.file, self.filename, self.etc = imp.find_module(name, path)
			return self
		except:
			try:
				#LOG.debug('pkg_name=`%s` didn`t found yet', pkg_name)
				if pkg_name not in sys.modules:
					LOG.debug('Pckg or modul`%s`didn`t found. Checking in'\
						' manifest...', full_name)
					self.install_pypackage(pkg_name)
				self.file, self.filename, self.etc = imp.find_module(name, path)
				return self
			except:
				raise ImportError, 'Exception in installing package`%s`. %s' %\
					(full_name, sys.exc_info()[1])

	def load_module(self, full_name):
		if full_name in sys.modules:
			return sys.modules[full_name]
		LOG.debug('ImpImport.load_module: %s', full_name)
		return imp.load_module(full_name, self.file, self.filename, self.etc)

sys.meta_path = [ImpImport()]
