from FieldNotFoundError import FieldNotFoundError
from isFloat import isFloat
import sys
import socket

HOST = '127.0.0.1'

def getFilename():
    return sys.argv[1]

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

def rangeCheck(value, min, max, varName):
    if value < min or value > max:
        raise  ValueError(f"{varName}: {value} must be in range {min} to {max}")

def extractData(lines):
    data = {}
    idLine = lines[0].split()
    if len(idLine) > 2:
        raise IndexError("There are too many indices for this field.")
    elif idLine[0] != "id":
        raise FieldNotFoundError("id")
    else:
        idLine[1] = int(idLine[1])
        rangeCheck(idLine[1], 1, 64000, "ID")
        data['id'] = idLine[1]

    inportLine = lines[1].split()
    inports = []
    if inportLine[0] != "inports":
        raise FieldNotFoundError("inports")
    else:
        for inport in inportLine[1:]:
            inport = int(inport)
            rangeCheck(inport, 1024, 64000, "Inports")
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
            rangeCheck(int(portnum), 1024, 64000, "Outport portnum")
            rangeCheck(int(cost), 0, float('inf'), "Cost")
            rangeCheck(int(otherId), 1, 64000, "Other ID")
            outports.append((int(portnum), int(cost), int(otherId)))
    data['outports'] = outports

    if len(lines) > 3 :
        argsLine = lines[3].split()
        data['args'] = [int(argsLine[1])]
        for arg in argsLine[2:]:
            if arg.isdigit():
                data['args'].append(int(arg))

            elif isFloat(arg):
                data['args'].append(float(arg))

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

        self.nextHop = {}

    def bindInports(self):
        for inport in self.fileInports:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind((HOST, inport))
            s.listen()
            self.inports.append(s)

    def mapPorts(self):
        i = 0
        for portnum, cost, neighborId in self.fileOutports:
            self.neighbourToInport[neighborId] = self.fileInports[i]
            self.neighbourToOutport[neighborId] = (HOST, portnum)
            i += 1

    def recieve(self):
        for sock in self.inports:
            data, addr = sock.recvfrom(1024)
            local_port = sock.getsockname()[1]
            neighbour_id = None
            for nid, port in self.neighbourToInport.items():
                if port == local_port:
                    neighbour_id = nid
                    break

        return data, neighbour_id

    def send(self, TargetId, data):
        toPort = self.nextHop[TargetId]
        host, port = self.neighbourToOutport[toPort]
        self.outputSocket.sendto(data, (host, port))




if __name__ == '__main__':
    daemon = RoutingDaemon()
    print(daemon)