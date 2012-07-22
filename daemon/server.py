#!/usr/bin/python27

import sys
sys.path.append('gen-py/')

from scigit import RepositoryManager
from scigit.ttypes import *

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

import os, shutil
import socket
import getopt
import argparse
import MySQLdb

class RepositoryManagerHandler:
	SCIGIT_DIR = '/var/scigit'
	GIT_REPO_DIR = '/home/git/repositories'
	SCIGIT_REPO_DIR = '/var/scigit/repos'

	def __init__(self, log_file = ''):
		self.dbc = MySQLdb.connect(user='scigit', passwd='scigit', db='scigit')
		self.log_file = None
		if log_file != '':
			self.log_file = open(log_file, 'a')

	def log(self, str):
		if self.log_file != None:
			self.log_file.write('%s\n' % str)
			self.log_file.flush()

	def refresh(self):
		cursor = self.dbc.cursor()
		cursor.execute('SELECT id FROM projects')
		for row in cursor.fetchall():
			self.createRepository(row[0])
		self.updateKeys()

	def updateKeys(self):
		cursor = self.dbc.cursor()
		cursor.execute('SELECT user_id, key_type, public_key FROM user_pub_keys')

		lines = []
		options = 'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty'
		self_key_file = open('/home/git/.ssh/id_rsa.pub', 'r')
		lines.append('command="/usr/local/bin/scigit-shell u0",%s %s' %\
					(options, self_key_file.readline().strip()))
		self_key_file.close()

		for row in cursor.fetchall():
			user_id = row[0]
			key_type = row[1]
			public_key = row[2]
			lines.append('command="/usr/local/bin/scigit-shell u%d",%s %s %s' %\
					(user_id, options, key_type, public_key))
		ak_file = open('/home/git/.ssh/authorized_keys', 'w')
		ak_file.write('\n'.join(lines))

	def addPublicKey(self, userId, publicKey):
		self.log('addPublicKey: %d' % userId)
		self.updateKeys()

	def deletePublicKey(self, userId, publicKey):
		self.log('deletePublicKey: %d' % userId)
		self.updateKeys()

	def createRepository(self, repoId):
		self.log('createRepository: %d' % repoId)
		dir = '%s/r%d.git' % (self.GIT_REPO_DIR, repoId)
		if os.path.isdir(dir) == False:
			os.mkdir(dir, 0700)
			config = {
				'core.fileMode': 'false',
				'scigit.repo.id': repoId,
				'scigit.repo.limit': 16 * 1024 * 1024
			}
			config_commands = '; '.join(['git config %s %s' % (key, config[key]) for key in config])
			os.system('cd %s; git init --bare; %s' % (dir, config_commands))
			os.symlink('%s/hooks/pre-receive' % self.SCIGIT_DIR, '%s/hooks/pre-receive' % dir)
			os.symlink('%s/hooks/post-receive' % self.SCIGIT_DIR, '%s/hooks/post-receive' % dir)

	def deleteRepository(self, repoId):
		self.log('deleteRepository: %d' % repoId)
		dir = '%s/r%d.git' % (self.GIT_REPO_DIR, repoId)
		if os.path.isdir(dir):
			# don't delete, maybe we'll want to restore the repository to the user
			# shutil.rmtree(dir)
			# shutil.rmtree('%s/r%d.git' % (self.SCIGIT_REPO_DIR, repoId))
			return

parser = argparse.ArgumentParser(description='Manages SciGit repositories. Please run under the user \'git\'.')
parser.add_argument('--port', default=9090)
parser.add_argument('--refresh', action='store_true')
parser.add_argument('--log_file', default='/tmp/scigit-daemon-log')
args = parser.parse_args()
handler = RepositoryManagerHandler(log_file=args.log_file)
if args.refresh == True:
	handler.refresh()

processor = RepositoryManager.Processor(handler)
transport = TSocket.TServerSocket(port=args.port)
tfactory = TTransport.TBufferedTransportFactory()
pfactory = TBinaryProtocol.TBinaryProtocolFactory()
 
server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

print "Starting SciGit repository manager..."
server.serve()
