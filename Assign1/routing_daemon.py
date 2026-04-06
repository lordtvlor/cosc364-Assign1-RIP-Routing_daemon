from FieldNotFoundError import FieldNotFoundError
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
        if (len(line) > 4) and (lineEnds != -1):   #len("id x") == 4 ==> all other lines longer
            importantLines.append(line)
    return importantLines

def extractData(lines):
    data = {}
    idLine = lines[0].split()
    inportLine = lines[1].split()
    outportLine = lines[2].split()
    if len(lines) > 3 :
        argsLine = lines[3].split()

    if len(idLine) > 2:
        raise IndexError("There are too many indices for this field.")
    elif idLine[0] != "id":
        raise FieldNotFoundError("id")
    else:
        if int(idLine[1]) < 1 or int(idLine[1]) > 64000:
            raise ValueError("id must be in range 1-64000.")
        else:
            data['id'] = int(idLine[1])

    inports = []
    if inportLine[0] != "inport":
        raise FieldNotFoundError("inport")
    else:
        for inport in inportLine[1:]:
            if int(inport) < 1024 or int(inport) > 64000:
                raise ValueError(f"inport {inport} not in range 1024-64000.")
            else:
                inports.append(int(inport))
    data['inports'] = inports

class RoutingDaemon:
    def __init__(self):
        filename = getFilename()
        contents = readFile(filename)
        contents = removeComments(contents)
        data = extractData(contents)
        self.id = data['id']

if __name__ == '__main__':
    daemon = RoutingDaemon()