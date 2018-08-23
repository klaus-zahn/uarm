#!/usr/bin/python

import sys
import json

from twisted.internet import reactor
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerFactory, \
                               WebSocketServerProtocol, \
                               listenWS

import time

from uarm.wrapper import SwiftAPI


logLevel = 0


       
class BroadcastServerProtocol(WebSocketServerProtocol):
  def onOpen(self):
    self.factory.register(self)

  def onMessage(self, msg, binary):
      if logLevel > 2:
        print("%s " % (msg))

      for key, value in json.loads(msg.decode()).items():
        if key == "y1":
          if -1 <= value <= 1:
            uarmRobot.x_pos = 0
          else:
            uarmRobot.x_pos = -value

        if key == "x1":
          if -1 <= value <= 1:
            uarmRobot.y_pos = 0
          else:
            uarmRobot.y_pos = -value

        if key == "x2":
          if -1 <= value <= 1:
            uarmRobot.tcp_rot = 0
          else:
            uarmRobot.tcp_rot = -value

        if key == "y2":
          if -1 <= value <= 1:
            uarmRobot.z_pos = 0
          else:
            uarmRobot.z_pos = -value

        if key == "z2":
          uarmRobot.pick = value

        if key == "z1":
          uarmRobot.connect = value

      if logLevel > 2:
        print("dx = %s, dy = %s, dz = %s, pick = %s, connect = %s " % (uarmRobot.y_pos, uarmRobot.z_pos, uarmRobot.tcp_rot, uarmRobot.pick, uarmRobot.connect))



  def connectionLost(self, reason):
    WebSocketServerProtocol.connectionLost(self, reason)
    self.factory.unregister(self)

class BroadcastServerFactory(WebSocketServerFactory):
   """
   Simple broadcast server broadcasting any message it receives to all
   currently connected clients.
   """

   def __init__(self, url, debug = False, debugCodePaths = False):
      WebSocketServerFactory.__init__(self, url)#, debug = debug, debugCodePaths = debugCodePaths)
      self.clients = []
      self.tickcount = 0


   def tick(self):
      self.tickcount += 1
      if logLevel > 1:
        self.broadcast("'tick %d' from server" % self.tickcount)
      reactor.callLater(1, self.tick)

   def register(self, client):
      if not client in self.clients:
        if logLevel > 1:
          print("registered client " + client.peer)
        self.clients.append(client)

   def unregister(self, client):
      if client in self.clients:
        if logLevel > 1:
          print("unregistered client " + client.peer)
        self.clients.remove(client)

   def broadcast(self, msg):
      if logLevel > 1:
        print("broadcasting message '%s' .." % msg)
      for c in self.clients:
        c.sendMessage(msg)
        if logLevel > 1:
          print("message sent to " + c.peer)


class uarmRobotClass(object):

  def __init__(self):
    self.x_pos = 0
    self.y_pos = 0
    self.tcp_rot = 0
    self.z_pos = 0
    self.pick = 0
    self.connect = 0
    self.swift = SwiftAPI(filters={'hwid': 'USB VID:PID=2341:0042'})
    self.swift.waiting_ready(timeout=3)
    self.swift.set_speed_factor(0.5)
    self.swift.waiting_ready(timeout=3)
    self.swift.disconnect()

  def openPort(self):
    self.swift.connect()
    #swift = SwiftAPI(filters={'hwid': 'USB VID:PID=2341:0042'})
    self.swift.waiting_ready(timeout=3)
    self.swift.set_speed_factor(0.5)
    self.swift.waiting_ready(timeout=3)
    self.swift.set_position(150, 0, 50, wait=True)

  def closePort(self):
    self.swift.disconnect()
    self.swift.waiting_ready(timeout=3)


  def move(self):
    Index = 0

    pick = 0
    connect = 0

    while True:

      if (dummy == False) and (connect == 0) and (self.connect == 1):
        self.openPort()

        ret = self.swift.get_position(wait=True)
        print("ret values %d, %d, %d" % (ret[0], ret[1], ret[2]))
        x_pos = ret[0]
        y_pos = ret[1]
        tcp_rot = ret[2]
        print("connected")
        connect = 1
      if (dummy == False) and (connect == 1) and (self.connect == 0):
        self.closePort()
        connect = 0
        print("disconnnected")

      if (self.x_pos != 0) or (self.y_pos != 0) or (self.tcp_rot != 0) or (self.z_pos != 0) or (self.pick != 0) or (self.connect != 0):
        if logLevel > 1:
          print("index = %d: x_pos = %d; y_pos = %d; z_pos = %d; tcp_rot = %d; pick = %d; connect = %d" % (Index, self.x_pos, self.y_pos, self.z_pos, self.tcp_rot, self.pick, self.connect))
          Index = Index + 1

      if (dummy == False) and (connect == 1) and ((self.x_pos != 0) or (self.y_pos != 0) or (self.tcp_rot != 0) or (self.z_pos != 0)):
        self.swift.set_position(x=self.x_pos, y=self.y_pos, z=self.z_pos, wait=True, relative=True);

        ret = self.swift.get_position(wait=True)
        if logLevel > 0:
          print("ret values %d, %d, %d" % (ret[0], ret[1], ret[2]))
        
      if (dummy == False) and (pick == 0) and (self.pick != 0):
        self.swift.set_pump(on=True)
        pick = 1
          
      if (dummy == False) and (pick == 1) and (self.pick == 0):
        self.swift.set_pump(on=False)
        pick = 0
      
      time.sleep(0.001);

### Main ###

if __name__ == '__main__':

  if len(sys.argv) > 1 and sys.argv[1] == 'debug':
    log.startLogging(sys.stdout)
    debug = True
  else:
    debug = False

  if len(sys.argv) > 1 and sys.argv[1] == 'dummy':
    print("use as dummy, no output uarm robot")
    dummy = True
  else:
    dummy = False

  ServerFactory = BroadcastServerFactory

  uarmRobot = uarmRobotClass()

  factory = ServerFactory("ws://localhost:9000",
    debug = debug,
    debugCodePaths = debug)

  factory.protocol = BroadcastServerProtocol
  factory.setProtocolOptions()
  listenWS(factory)

  webdir = File("/home/pi/uarm/www")
  web = Site(webdir)
  reactor.listenTCP(8080, web)

  reactor.callInThread(uarmRobot.move)

  reactor.run()
