import UtilityFunctions as UF
import socket
import struct
import select
import time
import random

HOST = '127.0.0.1'
INF = 16

class RoutingDaemon:
    def __repr__(self):
        self_str = f"ID {self.id!r}:\n"
        for target, (cost, nextHop) in self.routingTable.items():
            cost = cost if cost < INF else "INF"
            self_str += f"{target} via {nextHop} for cost {cost}\n"
        return self_str

    def __init__(self):
        filename = UF.getFilename()
        contents = UF.readFile(filename)
        contents = UF.removeComments(contents)
        data = UF.extractData(contents)
        self.id = data['id']
        self.fileInports = data['inports']
        self.fileOutports = data['outports']
        self.fileArgs = data['args']

        self.inports = []
        self.bindInports()
        self.outputSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.neighbourToInport = {}     #maps neighbour Ids to their respective INPORT number
        self.neighbourToOutport = {}    #maps neighbour Ids to their respective OUTPORT number
        self.mapPorts()

        self.routingTable = {}
        self.linkCosts = {}
        self.lastHeard = {}
        now = time.time()
        self.routingTable[self.id] = (0, self.id)
        for _, cost, nid in self.fileOutports:
            #Tracks known cost to a Target Id as well as the Router Id for the next hop
            self.routingTable[nid] = (cost, nid)
            #Tracks the original costs for neighbours, so they aren't lost if the router goes offline
            self.linkCosts[nid] = cost

            self.lastHeard[nid] = now

        self.run()

    def bindInports(self):
        for inport in self.fileInports:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind((HOST, inport))
            self.inports.append(s)

    def mapPorts(self):
        i = 0
        for portnum, _, neighborId in self.fileOutports:
            self.neighbourToInport[neighborId] = self.fileInports[i]
            self.neighbourToOutport[neighborId] = (HOST, portnum)
            i += 1

    def encodePacket(self, data):
        packet = bytearray()
        packet += struct.pack(
            'BBH', #Format string (1byte, 1byte, 2bytes)
            2,      #Command Field
            2,          #Version field
            self.id)    #Replace the zeroed bytes with source id
        for dest, cost in data.items():
            cost = INF if cost >= INF else cost
            packet += struct.pack(
                'HHIIII',   #2, 2, 4, 4, 4, 4 = 20
                2,  #Addr Family Identifier
                0,      #Must be Zeros (MB0)
                dest,   #IPV4 Field, repurposed to hold the destination router ids
                0,      #MB0
                0,      #MB0
                cost    #Metric Field, holds the cost of traversal
            )

        return packet

    def decodePacket(self, packet):
        """Put inside a try/catch block to drop invalid packets - a ValueError will be raised."""
        offset = 0
        command, version, sourceId = struct.unpack_from('BBH', packet, offset)    #Unpack Header
        offset += 4
        if command != 2:
            raise ValueError("Update Packet Command Number must be 2.")
        if version != 2:
            raise ValueError("Update Packet Version Number must be 2.")

        data = {}
        while offset + 20 <= len(packet):
            afi, twoZeros, dest, fourZeros1, fourZeros2, cost = struct.unpack_from('HHIIII', packet, offset)
            offset += 20
            if afi != 2:
                #invalid entry, ignore it
                continue
            if not UF.rangeCheck(cost, 1, INF):
                #invalid entry, ignore it
                continue

            cost = INF if cost >= INF else cost
            data[dest] = cost

        return data, sourceId

    def updateNeighbour(self, neighbourId):
        data = {}
        for dest in self.routingTable:
            if self.routingTable[dest][1] != neighbourId:
                data[dest] = self.routingTable[dest][0]
            else:
                #poisoned reverse, set cost to infinity if path goes through the neighbour we're updating
                #(They already have the rest of the path anyway)
                data[dest] = INF
        self.send(neighbourId, data)

    def send(self, TargetId, data):
        if TargetId in self.neighbourToOutport:
            #direct connection
            nextHop = self.neighbourToOutport[TargetId]
        else:
            #find the relevant neighbour
            nextHop = self.neighbourToOutport[self.routingTable[TargetId][1]]
        self.outputSocket.sendto(self.encodePacket(data), nextHop)

    def updateRoutes(self, data, sourceId):
        linkCost = self.linkCosts[sourceId]
        for dest, cost in data.items():
            if dest == self.id:
                #I can already reach me
                continue

            newCost = min(INF, cost + linkCost)
            if dest not in self.routingTable:
                #if I don't already have a route there, use this one
                if newCost < INF:
                    #assuming it's reachable
                    self.routingTable[dest] = (newCost, sourceId)
                    self.changed = True
                continue

            oldCost, oldNextHop = self.routingTable[dest]
            if oldNextHop == sourceId and oldCost != newCost:
                #route already goes through you nd your cost has changed, have to update my cost when you do
                self.routingTable[dest] = (newCost, sourceId)
                self.changed = True
                continue

            if newCost < oldCost:
                # if the route you've given me is shorter, use it
                self.routingTable[dest] = (newCost, sourceId)
                self.changed = True
                continue

    def shutdown(self, *args):
        self.isRunning = False

    def run(self):
        baseUpdateTime = self.fileArgs[0]
        desync = baseUpdateTime * 0.1

        updateInterval = baseUpdateTime + random.uniform(-desync, desync)
        neighbourDeathTime = 3 * baseUpdateTime
        lastUpdateTime = time.time()

        self.isRunning = True
        while self.isRunning:
            self.changed = False
            self.topoChanged = False
            now = time.time()

            readable, _, _ = select.select(self.inports, [], [], 1)
            for sock in readable:
                packet, _ = sock.recvfrom(1024)
                try:
                    data, sourceId = self.decodePacket(packet)
                except ValueError:
                    print(f"bad packet received at time {now}")
                    continue

                if sourceId not in self.lastHeard:
                    #it had been offline, but is now clearly not, so reassert its direct connection
                    self.routingTable[sourceId] = (self.linkCosts[sourceId], sourceId)

                self.lastHeard[sourceId] = now
                self.updateRoutes(data, sourceId)

            timedOut = set()
            for nid in list(self.lastHeard):
                if now - self.lastHeard[nid] > neighbourDeathTime:
                    for dest, (_, nextHop) in self.routingTable.items():
                        if nextHop == nid:
                            timedOut.add(nid)
                            self.routingTable[dest] = (INF, self.routingTable[dest][1])
                            self.topoChanged = True

            for nid in timedOut:
                del self.lastHeard[nid]

            if self.changed or self.topoChanged or now - lastUpdateTime > updateInterval:
                for neighbour in self.neighbourToOutport:
                    self.updateNeighbour(neighbour)
                lastUpdateTime = now
                print(self)


if __name__ == '__main__':
    daemon = RoutingDaemon()