#!/usr/bin/env python

import sys
sys.path.append('gen-py/')

from scigit import RepositoryManager
from scigit.ttypes import *

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

import socket

class RepositoryManagerHandler:
	def addPublicKey(self, userId, publicKey):
		print 'add key'
		return
	def deletePublicKey(self, userId, publicKey):
		print 'delete key'
		return
	def createRepository(self, repoId):
		print 'create repo'
		return
	def deleteRepository(self, repoId):
		print 'delete repo'
		return

handler = RepositoryManagerHandler()
processor = RepositoryManager.Processor(handler)
transport = TSocket.TServerSocket(port = 9090)
tfactory = TTransport.TBufferedTransportFactory()
pfactory = TBinaryProtocol.TBinaryProtocolFactory()
 
server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

print "Starting SciGit repository manager..."
server.serve()
