'''
Created on 07.02.2012

@author: sam
'''
import unittest
import os

from scalarizr.api import sysinfo
from scalarizr.util import system2

DISKSTATS_ = ['   1       0 ram0 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       1 ram1 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       2 ram2 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       3 ram3 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       4 ram4 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       5 ram5 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       6 ram6 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       7 ram7 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       8 ram8 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1       9 ram9 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1      10 ram10 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1      11 ram11 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1      12 ram12 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1      13 ram13 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1      14 ram14 0 0 0 0 0 0 0 0 0 0 0\n',
	'   1      15 ram15 0 0 0 0 0 0 0 0 0 0 0\n',
	'   7       0 loop0 0 0 0 0 0 0 0 0 0 0 0\n',
	'   7       1 loop1 0 0 0 0 0 0 0 0 0 0 0\n',
	'   7       2 loop2 0 0 0 0 0 0 0 0 0 0 0\n',
	'   7       3 loop3 0 0 0 0 0 0 0 0 0 0 0\n',
	'   7       4 loop4 0 0 0 0 0 0 0 0 0 0 0\n',
	'   7       5 loop5 0 0 0 0 0 0 0 0 0 0 0\n',
	'   7       6 loop6 0 0 0 0 0 0 0 0 0 0 0\n',
	'   7       7 loop7 0 0 0 0 0 0 0 0 0 0 0\n',
	'   8       0 sda 122983 61549 5368141 1205624 98504 130221 3727544 2555488 0 841516 3760836\n', 
	'   8       1 sda1 166 28 1328 1060 0 0 0 0 0 1060 1060\n', 
	'   8       2 sda2 162 0 1296 1516 0 0 0 0 0 1516 1516\n', 
	'   8       3 sda3 2 0 12 664 0 0 0 0 0 664 664\n', 
	'   8       5 sda5 113013 43150 5151042 1140888 72407 80384 3194400 2450600 0 788040 3591200\n', 
	'   8       6 sda6 9464 17189 213105 58520 16759 49837 533144 63332 0 48456 121876\n', 
	' 253       0 dm-0 26316 0 210528 284168 66644 0 533144 9233892 0 50344 9518068\n']

CPUINFO_ = ['processor\t: 0\n', 'vendor_id\t: GenuineIntel\n', 'cpu family\t: 6\n', 'model\t\t: 23\n', 'model name\t: Pentium(R) Dual-Core  CPU      E5300  @ 2.60GHz\n', 'stepping\t: 10\n', 'cpu MHz\t\t: 2600.000\n', 'cache size\t: 2048 KB\n', 'physical id\t: 0\n', 'siblings\t: 2\n', 'core id\t\t: 0\n', 'cpu cores\t: 2\n', 'apicid\t\t: 0\n', 'initial apicid\t: 0\n', 'fdiv_bug\t: no\n', 'hlt_bug\t\t: no\n', 'f00f_bug\t: no\n', 'coma_bug\t: no\n', 'fpu\t\t: yes\n', 'fpu_exception\t: yes\n', 'cpuid level\t: 13\n', 'wp\t\t: yes\n', 'flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe nx lm constant_tsc arch_perfmon pebs bts aperfmperf pni dtes64 monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr pdcm xsave lahf_lm dts tpr_shadow vnmi flexpriority\n', 'bogomips\t: 5200.26\n', 'clflush size\t: 64\n', 'cache_alignment\t: 64\n', 'address sizes\t: 36 bits physical, 48 bits virtual\n', 'power management:\n', '\n', 'processor\t: 1\n', 'vendor_id\t: GenuineIntel\n', 'cpu family\t: 6\n', 'model\t\t: 23\n', 'model name\t: Pentium(R) Dual-Core  CPU      E5300  @ 2.60GHz\n', 'stepping\t: 10\n', 'cpu MHz\t\t: 2600.000\n', 'cache size\t: 2048 KB\n', 'physical id\t: 0\n', 'siblings\t: 2\n', 'core id\t\t: 1\n', 'cpu cores\t: 2\n', 'apicid\t\t: 1\n', 'initial apicid\t: 1\n', 'fdiv_bug\t: no\n', 'hlt_bug\t\t: no\n', 'f00f_bug\t: no\n', 'coma_bug\t: no\n', 'fpu\t\t: yes\n', 'fpu_exception\t: yes\n', 'cpuid level\t: 13\n', 'wp\t\t: yes\n', 'flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe nx lm constant_tsc arch_perfmon pebs bts aperfmperf pni dtes64 monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr pdcm xsave lahf_lm dts tpr_shadow vnmi flexpriority\n', 'bogomips\t: 5199.83\n', 'clflush size\t: 64\n', 'cache_alignment\t: 64\n', 'address sizes\t: 36 bits physical, 48 bits virtual\n', 'power management:\n', '\n']

NETSTAT_ = ['Inter-|   Receive                                                |  Transmit\n', ' face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n', '    lo:  946846    1957    0    0    0     0          0         0   946846    1957    0    0    0     0       0          0\n', '  eth0: 45323389  187745    0    0    0     0          0         0 21474707  224662    0    0    0     0       0          0\n']


DISKSTATS = '/tmp/diskstats'
CPUINFO = '/tmp/cpuinfo'
NETSTAT = '/tmp/netstat'

class TestSysInfoAPI(unittest.TestCase):

	def __init__(self, methodName='runTest'):
		unittest.TestCase.__init__(self, methodName=methodName)
		self.info = sysinfo.SysInfoAPI()
		with open(DISKSTATS, 'w+') as fp:
			fp.writelines(DISKSTATS_)
		with open(CPUINFO, 'w+') as fp:
			fp.writelines(CPUINFO_)
		with open(NETSTAT, 'w+') as fp:
			fp.writelines(NETSTAT_)

		self.info._DISKSTATS = DISKSTATS
		self.info._CPUINFO = CPUINFO
		self.info._NETSTAT = NETSTAT
	
	def test_add_extension(self):
		class ApiExt(object):
			def smile(self):
				return 'test_txt'
			
			def __bugaga(self):
				return 'You can`t see this'
		
		ext = ApiExt()
		self.info.add_extension(ext)
		self.assertEqual(self.info.smile(), 'test_txt')

	def test_fqdn(self):
		(out, err, rc) = system2(('hostname'))
		self.assertEqual(out.strip(), self.info.fqdn())
		old_name = out.strip()
		
		self.info.fqdn('Scalr-Role-12345')
		(out, err, rc) = system2(('hostname'))
		self.assertEqual(out.strip(), 'Scalr-Role-12345')
		self.info.fqdn(old_name)

	def test_block_devices(self):
		self.assertIsNotNone(self.info.block_devices())
		
	def test_uname(self):
		self.assertTrue(isinstance(self.info.uname(), dict) and self.info.uname())
		
	def test_dist(self):
		self.assertEqual(self.info.dist(), {'codename': 'oneiric', 'description': 'Ubuntu 11.10 (oneiric)', 'id': 'Ubuntu', 'release': '11.10'})

	def test_pythons(self):
		self.assertIsNotNone(self.info.pythons())
		self.assertEqual(self.info.pythons(), ['3.2.2', '2.7.2+'])

	def test_cpu_info(self):
		cpu = self.info.cpu_info()
		self.assertEqual(cpu, [{'vendor_id': 'GenuineIntel', 'cpu family': '6', 'cache_alignment': '64', 'cpu cores': '2', 'bogomips': '5200.26', 'core id': '0', 'hlt_bug': 'no', 'apicid': '0', 'f00f_bug': 'no', 'fpu_exception': 'yes', 'stepping': '10', 'wp': 'yes', 'clflush size': '64', 'coma_bug': 'no', 'fdiv_bug': 'no', 'cache size': '2048 KB', 'power management': '', 'cpuid level': '13', 'physical id': '0', 'fpu': 'yes', 'flags': 'fpu vme de pse tsc msr pae mce cx8 apic mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe nx lm constant_tsc arch_perfmon pebs bts aperfmperf pni dtes64 monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr pdcm xsave lahf_lm dts tpr_shadow vnmi flexpriority', 'cpu MHz': '2600.000', 'model name': 'Pentium(R) Dual-Core  CPU      E5300  @ 2.60GHz', 'siblings': '2', 'model': '23', 'processor': '0', 'initial apicid': '0', 'address sizes': '36 bits physical, 48 bits virtual'}, {'vendor_id': 'GenuineIntel', 'cpu family': '6', 'cache_alignment': '64', 'cpu cores': '2', 'bogomips': '5199.83', 'core id': '1', 'hlt_bug': 'no', 'apicid': '1', 'f00f_bug': 'no', 'fpu_exception': 'yes', 'stepping': '10', 'wp': 'yes', 'clflush size': '64', 'coma_bug': 'no', 'fdiv_bug': 'no', 'cache size': '2048 KB', 'power management': '', 'cpuid level': '13', 'physical id': '0', 'fpu': 'yes', 'flags': 'fpu vme de pse tsc msr pae mce cx8 apic mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe nx lm constant_tsc arch_perfmon pebs bts aperfmperf pni dtes64 monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr pdcm xsave lahf_lm dts tpr_shadow vnmi flexpriority', 'cpu MHz': '2600.000', 'model name': 'Pentium(R) Dual-Core  CPU      E5300  @ 2.60GHz', 'siblings': '2', 'model': '23', 'processor': '1', 'initial apicid': '1', 'address sizes': '36 bits physical, 48 bits virtual'}])

	def test_load_average(self):
		pass

	def test_disk_stats(self):
		self.assertEqual(self.info.disk_stats(), [{'device': 'ram0', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram1', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram2', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram3', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram4', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram5', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram6', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram7', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram8', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram9', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram10', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram11', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram12', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram13', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram14', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'ram15', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'loop0', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'loop1', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'loop2', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'loop3', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'loop4', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'loop5', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'loop6', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'loop7', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 0, 'bytes': 0, 'sectors': 0}}, {'device': 'sda', 'write': {'num': 98504, 'bytes': 1908502528, 'sectors': 3727544}, 'read': {'num': 122983, 'bytes': 2748488192L, 'sectors': 5368141}}, {'device': 'sda1', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 166, 'bytes': 679936, 'sectors': 1328}}, {'device': 'sda2', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 162, 'bytes': 663552, 'sectors': 1296}}, {'device': 'sda3', 'write': {'num': 0, 'bytes': 0, 'sectors': 0}, 'read': {'num': 2, 'bytes': 6144, 'sectors': 12}}, {'device': 'sda5', 'write': {'num': 72407, 'bytes': 1635532800, 'sectors': 3194400}, 'read': {'num': 113013, 'bytes': 2637333504L, 'sectors': 5151042}}, {'device': 'sda6', 'write': {'num': 16759, 'bytes': 272969728, 'sectors': 533144}, 'read': {'num': 9464, 'bytes': 109109760, 'sectors': 213105}}, {'device': 'dm-0', 'write': {'num': 66644, 'bytes': 272969728, 'sectors': 533144}, 'read': {'num': 26316, 'bytes': 107790336, 'sectors': 210528}}])
		
	def test_net_stats(self):
		self.assertEqual(self.info.net_stats(), [{'receive': {'packets': '1957', 'errors': '0', 'bytes': '946846'}, 'transmit': {'packets': '1957', 'errors': '0', 'bytes': '946846'}, 'iface': 'lo'}, {'receive': {'packets': '187745', 'errors': '0', 'bytes': '45323389'}, 'transmit': {'packets': '224662', 'errors': '0', 'bytes': '21474707'}, 'iface': 'eth0'}])

def tearDownModule():
	os.remove(DISKSTATS)
	os.remove(CPUINFO)
	os.remove(NETSTAT)

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()