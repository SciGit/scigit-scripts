#!/usr/bin/python2.7

import os, sys
import subprocess

from scigit import RepositoryManager
from scigit.ttypes import *

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

import shutil
import socket
import argparse
import MySQLdb

class RepositoryManagerHandler:
	HOME_DIR = '/home'
	SCIGIT_DIR = '/var/scigit'
	GIT_REPO_DIR = HOME_DIR + '/git/repositories'
	SCIGIT_REPO_DIR = '/var/scigit/repos'
	DELETED_THRESHOLD = 100 # after N deletions, regenerate authorized_keys

	def __init__(self, log_file = ''):
		self.dbc = MySQLdb.connect(user='scigit', passwd='scigit', db='scigit')
		self.log_file = None
		self.deletedkeys = 0
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

	def getAuthKeyCommand(self, userid, keyid, publickey):
		options = 'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty'
		return 'command="/usr/local/bin/scigit-shell u%d %d",%s %s' %\
					(userid, keyid, options, publickey)

	def updateKeys(self):
		cursor = self.dbc.cursor()
		cursor.execute('DELETE FROM user_pub_keys WHERE enabled = 0')
		self.dbc.commit()
		cursor.execute('SELECT id, user_id, key_type, public_key FROM user_pub_keys')

		lines = []
		self_key_file = open(self.HOME_DIR + '/git/.ssh/id_rsa.pub', 'r')
		lines.append(self.getAuthKeyCommand(0, 0, self_key_file.readline().strip()))
		self_key_file.close()

		for row in cursor.fetchall():
			id = row[0]
			userid = row[1]
			keytype = row[2]
			publickey = row[3]
			lines.append(self.getAuthKeyCommand(userid, id, keytype + ' ' + publickey))
		ak_file = open(self.HOME_DIR + '/git/.ssh/authorized_keys', 'w')
		ak_file.write('\n'.join(lines) + '\n')

	def addPublicKey(self, keyid, userid, publicKey):
		self.log('addPublicKey: %d' % userid)
		ak_file = open(self.HOME_DIR + '/git/.ssh/authorized_keys', 'a')
		ak_file.write(self.getAuthKeyCommand(userid, keyid, publicKey) + '\n')

	def deletePublicKey(self, keyid, userid, publicKey):
		self.log('deletePublicKey: %d' % userid)
		# don't need to delete it immediately, as the db invalidates it
		self.deletedkeys += 1
		if self.deletedkeys >= self.DELETED_THRESHOLD:
			self.deletedkeys = 0
			self.updateKeys()

	def createRepository(self, repoid):
		self.log('createRepository: %d' % repoid)
		dir = '%s/r%d.git' % (self.GIT_REPO_DIR, repoid)
		if os.path.isdir(dir) == False:
			os.mkdir(dir, 0700)
			config = {
				'core.fileMode': 'false',
				'scigit.repo.id': repoid,
				'scigit.repo.limit': 16 * 1024 * 1024
			}
			config_commands = '; '.join(['git config %s %s' % (key, config[key]) for key in config])
			os.system('cd %s; git init --bare; %s' % (dir, config_commands))
			# Add our custom hooks.
			os.symlink('%s/hooks/pre-receive' % self.SCIGIT_DIR, '%s/hooks/pre-receive' % dir)
			os.symlink('%s/hooks/post-receive' % self.SCIGIT_DIR, '%s/hooks/post-receive' % dir)
			# Clone the repo locally and create an empty commit.
			os.chdir(self.SCIGIT_REPO_DIR)
			reponame = 'r' + str(repoid)
			subprocess.check_output(
					['env', '-i', 'git', 'clone', 'git@localhost:%s' % reponame])
			os.chdir(reponame)
			subprocess.check_output(
					['env', '-i', 'git', 'config', 'core.fileMode', 'false'])
			subprocess.check_output(
					['git', 'commit', '--allow-empty', '-m', 'Initial commit'])
			subprocess.check_output(
					['env', '-i', 'git', 'push', 'origin', 'master'])
			subprocess.check_output(
					['env', '-i', 'chmod', '755', '-R', '%s/%s' %
							(self.SCIGIT_REPO_DIR, reponame)])

	def deleteRepository(self, repoid):
		self.log('deleteRepository: %d' % repoid)
		dir = '%s/r%d.git' % (self.GIT_REPO_DIR, repoid)
		if os.path.isdir(dir):
			# don't delete, maybe we'll want to restore the repository to the user
			# shutil.rmtree(dir)
			# shutil.rmtree('%s/r%d.git' % (self.SCIGIT_REPO_DIR, repoid))
			return

# Make sure I'm the git user.
if subprocess.check_output('whoami').strip() != 'git':
	print 'Must be run as the git user.'
	exit(1)

# Make sure git ident is set.
subprocess.check_output(['git', 'config', '--global', 'user.name', 'git'])

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
