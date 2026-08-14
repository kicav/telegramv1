from tms.datasets.merge_engine import union
from tms.datasets.difference_engine import difference
from tms.datasets.intersection_engine import intersection

def test_set_ops():
    a={1,2,3};b={3,4};assert union(a,b)=={1,2,3,4};assert difference(a,b)=={1,2};assert intersection(a,b)=={3}
