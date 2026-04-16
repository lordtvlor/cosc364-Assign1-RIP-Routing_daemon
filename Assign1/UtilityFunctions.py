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