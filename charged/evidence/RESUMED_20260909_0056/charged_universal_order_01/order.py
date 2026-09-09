"""A weight-aware order, independent of writer budget, retry slack and prices."""
import hashlib,heapq,json

def normalize(c):
 assert type(c) is dict and set(c)=={'works','edges'}
 w=c['works'];edges=c['edges'];assert type(w) is list and type(edges) is list
 assert all(type(x) is int and x>0 for x in w)
 n=len(w);seen=set()
 for e in edges:
  assert type(e) is list and len(e)==2 and all(type(v) is int and 0<=v<n for v in e) and e[0]!=e[1]
  assert tuple(e) not in seen;seen.add(tuple(e))
 return dict(works=w[:],edges=[list(e) for e in sorted(seen)])
def binding(c):return hashlib.sha256(json.dumps(normalize(c),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def construct(c):
 c=normalize(c);w=c['works'];n=len(w);degree=[0]*n;successors=[[] for _ in w]
 for u,v in c['edges']:degree[v]+=1;successors[u].append(v)
 heap=[(w[i],i) for i in range(n) if degree[i]==0];heapq.heapify(heap);order=[]
 while heap:
  _,i=heapq.heappop(heap);order.append(i)
  for v in successors[i]:
   degree[v]-=1
   if degree[v]==0:heapq.heappush(heap,(w[v],v))
 assert len(order)==n,'cyclic input'
 return dict(schema='universal-work-order-v1',input_sha256=binding(c),order=order)

class Policy:
 """The returned order is consumed using only a global failed-cheap allowance."""
 def __init__(self,c,artifact,r,three=True):
  from verify import check
  check(c,artifact);assert type(r) is int and r>=0 and type(three) is bool
  self.order=tuple(artifact['order']);self.remaining=r;self.three=three;self.at=0
 def choose(self):
  if self.at==len(self.order):return None
  return self.order[self.at],('cheap' if self.remaining else 'cached' if self.three else 'protected')
 def advance(self,completed):
  assert type(completed) is bool and self.choose() is not None
  if completed:self.at+=1
  else:assert self.remaining>0;self.remaining-=1
