from FieldNotFoundError import FieldNotFoundError
import sys

INF = 16

def isFloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def rangeCheck(value, min, max, varName=None):
    if (value < min or value > max):
        if varName is not None:
            raise  ValueError(f"{varName}: {value} must be in range {min} to {max}")
        else:
            return False
    return True

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
            rangeCheck(int(cost), 0, INF, "Cost")
            rangeCheck(int(otherId), 1, 64000, "Other ID")
            outports.append((int(portnum), int(cost), int(otherId)))
    data['outports'] = outports

    if len(lines) > 3 :
        argsLine = lines[3].split()
        data['args'] = [int(argsLine[1])]
        for arg in argsLine[2:]:
            if arg.isdigit():
                data['args'].append(int(arg))
                continue
            elif isFloat(arg):
                data['args'].append(float(arg))
                continue
            data['args'].append(arg)
    return data