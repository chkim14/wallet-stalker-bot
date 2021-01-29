def union(lst1,lst2): 
  return list(set(lst1).union(set(lst2)))

def intersection(lst1, lst2): 
  return list(set(lst1).intersection(set(lst2)))

def difference(lst1,lst2): 
  return list(set(lst1).difference(set(lst2)))