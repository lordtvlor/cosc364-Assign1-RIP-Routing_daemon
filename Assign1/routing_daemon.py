from FieldNotFoundError import FieldNotFoundError
import UtilityFunctions as UF
import sys
import socket
import struct
import select
import time

HOST = '127.0.0.1'
INF = 16

getFilename = lambda: sys.argv[1]

def readFile(filename):
    with open(filename) as f:
        lines = f.read().splitlines() #doing this instead of using readlines() means \n chars are automatically removed
    return lines

def removeComments(lines):
    importantLines = []
    for line in lines:
        line.lstrip()
        lineEnds = line.find(';')
        line = line[:lineEnds]
        if (len(line) > 3) and (lineEnds != -1):   #len("id x") == 3 ==> all other lines longer
            importantLines.append(line)
    return importantLines

def extractData(lines):
    data = {}
    idLine = lines[0].split()
    if len(idLine) > 2:
        raise IndexError("There are too many indices for this field.")
    elif idLine[0] != "id":
        raise FieldNotFoundError("id")
    else:
        idLine[1] = int(idLine[1])
        UF.rangeCheck(idLine[1], 1, 64000, "ID")
        data['id'] = idLine[1]

    inportLine = lines[1].split()
    inports = []
    if inportLine[0] != "inports":
        raise FieldNotFoundError("inports")
    else:
        for inport in inportLine[1:]:
            inport = int(inport)
            UF.rangeCheck(inport, 1024, 64000, "Inports")
            inports.append(inport)
    data['inports'] = inports

    outportLine = lines[2].split()
    outports = []
    if outportLine[0] != "outports":
        raise FieldNotFoundError("outports")
    else:
        for outport in outportLine[1:]:
            outport = outport[1:-1]
            portnum, cost, otherId = outport.split(',')
            UF.rangeCheck(int(portnum), 1024, 64000, "Outport portnum")
            UF.rangeCheck(int(cost), 0, INF, "Cost")
            UF.rangeCheck(int(otherId), 1, 64000, "Other ID")
            outports.append((int(portnum), int(cost), int(otherId)))
    data['outports'] = outports

    if len(lines) > 3 :
        argsLine = lines[3].split()
        data['args'] = [int(argsLine[1])]
        for arg in argsLine[2:]:
            if arg.isdigit():
                data['args'].append(int(arg))
                continue
            elif UF.isFloat(arg):
                data['args'].append(float(arg))
                continue
            data['args'].append(arg)
    return data

class RoutingDaemon:
    def __repr__(self):
        return(f"RoutingDaemon {self.id!r}, "
               f"inports: {self.fileInports!r}, "
               f"outports: {self.fileOutports!r}, "
               f"args: {self.fileArgs!r}")

    def __init__(self):
        filename = getFilename()
        contents = readFile(filename)
        contents = removeComments(contents)
        data = extractData(contents)
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
        #Tracks known cost to a Target Id as well as the Router Id for the next hop
        self.routingTable = {id: (cost, id) for _, cost, id in self.fileOutports}

        self.lastHeard = {id: time.time() for _, __, id in self.fileOutports}
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
        for dest, cost in data:
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
        while offset + 20 < len(packet):
            afi, twoZeros, dest, fourZeros1, fourZeros2, cost = struct.unpack_from('HHIIII', packet, offset)
            offset += 20
            if afi != 2:
                #invalid entry, ignore it
                continue
            if not UF.rangeCheck(cost, 0, INF):
                #invalid entry, ignore it
                continue
            data[dest] = cost

        return data, sourceId

    def updateNeghbour(self, neighbourId):
        data = {}
        for dest in self.routingTable.keys():
            if self.routingTable[dest][1] != neighbourId:
                data[dest] = self.routingTable[dest][0]
            else:
                #poisoned reverse, set cost to infinity if path goes through the neighbour we're updating
                #(They already have the rest of the path anyway)
                data[dest] = INF
        packet = self.encodePacket(data)
        self.send(neighbourId, packet)

    def send(self, TargetId, data):
        self.outputSocket.sendto(self.encodePacket(data), self.neighbourToOutport[self.routingTable[TargetId][1]])

    def updateRoutingTable(self, data, neighbourId):
        changed = False
        neighbourCost = self.routingTable[neighbourId][0]
        for dest, cost in data.items():
            newCost = cost + neighbourCost
            if dest not in self.routingTable or newCost < self.routingTable[dest][0]:
                self.routingTable[dest] = (newCost, neighbourId)
                changed = True

            elif self.routingTable[dest][1] == neighbourId and newCost != self.routingTable[dest][0]:
                #edge case: if route to a target goes through N and N's cost changes -> change our cost accordingly
                self.routingTable[dest] = (newCost, neighbourId)
                changed = True

        return changed

    def run(self):
        updateInterval = self.fileArgs[0]
        neighbourDeathTime = 3 * updateInterval
        lastUpdateTime = time.time()

        while 1:
            now = time.time()
            readable, _, _ = select.select(self.input_sockets, [], [], 1.0)
            for sock in readable:
                packet, addr = sock.recvfrom(1024)
                try:
                    data, sourceId = self.decodePacket(packet)
                except ValueError:
                    print(f"bad packet received at time {now}")
                    continue

                self.lastHeard[sourceId] = now  #register the neighbour as alive
                changed = self.updateRoutingTable(data, sourceId)
                if changed:
                    #Trigger Update
                    for id in self.neighbourToOutport.keys():
                        self.updateNeghbour(id)
                        lastUpdateTime = now

            if now - lastUpdateTime > updateInterval:
                #Periodic Update
                for id in self.neighbourToOutport.keys():
                    self.updateNeghbour(id)
                    lastUpdateTime = now

            for neighbour in self.lastHeard.keys():
                changed = False
                if now - self.lastHeard[neighbour] > neighbourDeathTime:
                    for dest in self.routingTable.keys():
                        cost, nextHopId = self.routingTable[dest]
                        if nextHopId == neighbour:
                            self.routingTable[dest] = (INF, nextHopId)
                            del self.lastHeard[neighbour]
                            changed = True

                if changed:
                    #Neighbour Timeout Update
                    for id in self.neighbourToOutport.keys():
                        self.updateNeghbour(id)
                        lastUpdateTime = now




if __name__ == '__main__':
    daemon = RoutingDaemon()
    print(daemon)