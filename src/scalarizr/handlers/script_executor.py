'''
Created on Dec 24, 2009

@author: marat
'''

from scalarizr.bus import bus
from scalarizr.handlers import Handler
from scalarizr.messaging import Queues, Messages
import scalarizr.util as zrutil
import threading
from scalarizr.util import configtool
try:
	import time
except ImportError:
	import timemodule as time
import subprocess
import os
import shutil
import stat
import logging
import binascii



def get_handlers ():
	return [ScriptExecutor()]

class ScriptExecutor(Handler):
	name = "script_executor"
	
	OPT_EXEC_DIR_PREFIX = "exec_dir_prefix"
	OPT_LOGS_DIR_PREFIX = "logs_dir_prefix"
	OPT_LOGS_TRUNCATE_OVER = "logs_truncate_over"	
	
	_logger = None
	_queryenv = None
	_msg_service = None
	_platform = None
	
	_event_name = None
	
	_exec_dir_prefix = None
	_exec_dir = None
	_logs_dir_prefix = None
	_logs_dir = None
	_logs_truncate_over = None
	
	_wait_async = False
	
	def __init__(self, wait_async=False):
		self._logger = logging.getLogger(__name__)		
		self._wait_async = wait_async
		
		self._queryenv = bus.queryenv_service
		self._msg_service = bus.messaging_service
		self._platform = bus.platfrom
		
		producer = self._msg_service.get_producer()
		producer.on("before_send", self.on_before_message_send)
		
		config = bus.config
		sect_name = configtool.get_handler_section_name(self.name)
		if not config.has_section(sect_name):
			raise Exception("Script executor handler is not configured. "
						    + "Config has no section '%s'" % sect_name)
		
		# read exec_dir_prefix
		self._exec_dir_prefix = config.get(sect_name, self.OPT_EXEC_DIR_PREFIX)
		if not os.path.isabs(self._exec_dir_prefix):
			self._exec_dir_prefix = bus.base_path + os.sep + self._exec_dir_prefix
			
		# read logs_dir_prefix
		self._logs_dir_prefix = config.get(sect_name, self.OPT_LOGS_DIR_PREFIX)
		if not os.path.isabs(self._logs_dir_prefix):
			self._logs_dir_prefix = bus.base_path + os.sep + self._logs_dir_prefix
		
		# logs_truncate_over
		self._logs_truncate_over = zrutil.parse_size(config.get(sect_name, self.OPT_LOGS_TRUNCATE_OVER))
	
	
	def on_before_message_send(self, queue, message):
		self.exec_scripts_on_event(message.name)
		
	
	def exec_scripts_on_event (self, event_name, internal_ip=None):
		self._logger.debug("Fetching scripts for event %s", event_name)	
		scripts = self._queryenv.list_scripts(event_name)
		self._logger.debug("Fetched %d scripts", len(scripts))
		
		if len(scripts) > 0:
			if not internal_ip is None:
				self._logger.info("Executing %d script(s) on event %s fired on host %s", 
						len(scripts), event_name, internal_ip)
			else:
				self._logger.info("Executing %d script(s) on event %s", len(scripts), event_name)
			
			self._exec_dir = self._exec_dir_prefix + str(time.time())
			self._logger.debug("Create temp exec dir %s", self._exec_dir)
			os.makedirs(self._exec_dir)
			
			self._logs_dir = self._logs_dir_prefix + str(time.time())
			self._logger.debug("Create temp logs dir %s", self._logs_dir)
			os.makedirs(self._logs_dir) 

			if self._wait_async:
				async_threads = []

			for script in scripts:
				self._logger.debug("Execute script '%s' in %s mode; exec timeout: %d", 
								script.name, "async" if script.asynchronous else "sync", script.exec_timeout)
				if script.asynchronous:
					# Start new thread
					t = threading.Thread(target=self._execute_script, args=[script])
					t.start()
					if self._wait_async:
						async_threads.append(t)
				else:
					try:
						self._execute_script(script)
					except (Exception, BaseException), e:
						self._logger.error("Caught exception while execute script '%s'", script.name)
						self._logger.exception(e)

			# Wait
			if self._wait_async:
				for t in async_threads:
					t.join()
			shutil.rmtree(self._exec_dir)

		
	def on_EventNotice(self, message):
		# TODO: remove event notice. 
		
		self._logger.debug("Entering on_EventNotice")
		
		internal_ip = message.body["InternalIP"]
		role_name = message.body["RoleName"]
		event_name = message.body["EventName"]
		self._logger.info("Received event notice (event_name: %s, role_name: %s, ip: %s)", 
						event_name, role_name, internal_ip)
		self._event_name = event_name
		
		if self._platform.get_private_ip() == internal_ip:
			self._logger.info("Ignore event with the same ip as mine")
			return 
		
		if internal_ip == "0.0.0.0":
			self._logger.info("Custom event %s fired", event_name)
		else:
			self._logger.info("Scalr notified me that %s (role: %s) fired event %s", 
							internal_ip, role_name, event_name)
		
		self.exec_scripts_on_event(event_name, internal_ip)
		
			
	def _execute_script(self, script):
		# Create script file in local fs
		script_path = self._exec_dir + os.sep + script.name
		self._logger.debug("Put script contents into file %s", script_path)
		f = open(script_path, "w")
		f.write(script.body)
		f.close()
		os.chmod(script_path, stat.S_IREAD | stat.S_IEXEC)

		self._logger.info("Starting '%s' ...", script.name)
		
		# Create stdout and stderr log files
		stdout = open(self._logs_dir + os.sep + script.name + "-out", "w")
		stderr = open(self._logs_dir + os.sep + script.name + "-err", "w")
		self._logger.info("Redirect stdout > %s stderr > %s", stdout.name, stderr.name)		
		
		# Start process
		try:
			proc = subprocess.Popen(script_path, stdout=stdout, stderr=stderr)
		except OSError:
			self._logger.error("Cannot execute script '%s' (script path: %s)", script.name, script_path)
			raise
		
		# Communicate with process
		self._logger.debug("Communicate with '%s'", script.name)
		start_time = time.time()		
		while time.time() - start_time < script.exec_timeout:
			if proc.poll() is None:
				time.sleep(0.5)
			else:
				# Process terminated
				self._logger.debug("Script '%s' terminated", script.name)
				break
		else:
			# Process timeouted
			self._logger.warn("Script '%s' execution timeout (%d seconds). Kill process", 
							script.name, script.exec_timeout)
			if hasattr(proc, "kill"):
				# python >= 2.6
				proc.kill()
			else:
				import signal
				os.kill(proc.pid, signal.SIGKILL)
						
		elapsed_time = time.time() - start_time
		
		stdout.close()
		stderr.close()
		os.remove(script_path)
		
		
		self._logger.info("Script '%s' execution finished. Elapsed time: %.2f seconds, stdout: %s, stderr: %s", 
						script.name, elapsed_time, 
						zrutil.format_size(os.path.getsize(stdout.name)), 
						zrutil.format_size(os.path.getsize(stderr.name)))
		
		# Notify scalr
		self._logger.debug("Prepare 'ExecResult' message")
		message = self._msg_service.new_message(Messages.EXEC_RESULT, body=dict(
			stdout=binascii.b2a_base64(self._get_truncated_log(stdout.name, self._logs_truncate_over)),
			stderr=binascii.b2a_base64(self._get_truncated_log(stderr.name, self._logs_truncate_over)),
			time_elapsed=elapsed_time,
			script_name=script.name,
			script_path=script_path,
			event_name=self._event_name
		))
		
		self._logger.debug("Sending 'ExecResult' message to Scalr")
		producer = self._msg_service.get_producer()
		producer.send(Queues.CONTROL, message)
		self._logger.debug("Done sending message")
	
	def _get_truncated_log(self, logfile, maxsize):
		f = open(logfile, "r")
		try:
			ret = f.read(int(maxsize))
			if (os.path.getsize(logfile) > maxsize):
				ret += "... Truncated. See the full log in " + logfile
			return ret
		finally:
			f.close()
				
	
	def accept(self, message, queue, behaviour=None, platform=None, os=None, dist=None):
		return message.name == Messages.EVENT_NOTICE