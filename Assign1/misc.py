import ast

wdbeiu = "(5067, 3, 7)"
values = ast.literal_eval(wdbeiu)
portnum, cost, id = values
print(values)
print(cost, id, portnum)