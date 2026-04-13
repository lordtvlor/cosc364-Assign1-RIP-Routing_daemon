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
    def __init__(self):
        filename = getFilename()
        contents = readFile(filename)
        contents = removeComments(contents)
        data = extractData(contents)
        self.id = data['id']
        self.inports = data['inports']
        self.outportsData = data['outports']
        self.args = data['args']
        self.forwardTable = {}
        self.costsTable = {}
        self.outports = {}
        self.assembleFirstTables()

    def __repr__(self):
        return(f"RoutingDaemon {self.id!r}, "
               f"inports: {self.inports!r}, "
               f"outports: {self.outports!r}, "
               f"args: {self.args!r}")

    def assembleFirstTables(self):
        """Necessarily calls openPort to receive socket objects to put in the outports table"""
        for portnum, cost, targetId in self.outportsData:
            self.forwardTable[targetId] = targetId    #next hop for connected routers is via that router
            self.costsTable[targetId] = cost
            self.outports[targetId] = self.openPort(portnum)

    def openPort(self, portnum):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((HOST, portnum))
            print(f"Socket bound to {HOST}:{portnum}")
        except socket.error as msg:
            print(f"Socket Bind failed. Error: {msg}")




if __name__ == '__main__':
    daemon = RoutingDaemon()
    print(daemon)