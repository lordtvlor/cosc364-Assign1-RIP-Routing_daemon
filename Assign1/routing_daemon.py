from FieldNotFoundError import FieldNotFoundError
from isFloat import isFloat
import sys

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
    if inportLine[0] != "inport":
        raise FieldNotFoundError("inport")
    else:
        for inport in inportLine[1:]:
            rangeCheck(inport, 1024, 64000, "Inport")
            inports.append(int(inport))
    data['inports'] = inports
    outportLine = lines[2].split()
    if outportLine[0] != "outport":
        raise FieldNotFoundError("outport")
    else:
        for outport in outportLine[1:]:
            outport = outport[1:-1]
            portnum, cost, otherId = outport.split(',')
            rangeCheck(int(portnum), 1024, 64000, "Outport portnum")
            rangeCheck(int(cost), 0, float('inf'), "Cost")
            rangeCheck(int(otherId), 1, 64000, "Other ID")
            data['outports'] = (int(portnum), int(cost), int(otherId))

    if len(lines) > 3 :
        argsLine = lines[3].split()
        data['args'] = [int(argsLine[1])]
        for arg in argsLine[2:]:
            if arg.isdigit():
                data['args'].append(int(arg))

            elif isFloat(arg):
                data['args'].append(float(arg))

            arg.strip("'")
            if arg.isalpha():
                data['args'].append(str(arg))

    return data

class RoutingDaemon:
    def __init__(self):
        filename = getFilename()
        contents = readFile(filename)
        contents = removeComments(contents)
        data = extractData(contents)
        self.id = data['id']
        self.inports = data['inports']
        self.outports = data['outports']
        self.args = data['args']

    def __repr__(self):
        return(f"RoutingDaemon {self.id!r}, "
               f"inports {self.inports!r}, "
               f"outports {self.outports!r}, "
               f"args {self.args!r}")




if __name__ == '__main__':
    daemon = RoutingDaemon()
    print(daemon)