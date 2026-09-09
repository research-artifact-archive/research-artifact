"""Independent scan checker for an input-bound minimum-ready-work order."""
import hashlib,json

def check(c,a):
 assert type(c) is dict and set(c)=={'works','edges'}
 w=c['works'];e=c['edges'];assert type(w) is list and type(e) is list
 assert all(type(x) is int and x>0 for x in w);n=len(w);seen=set();pred=[set() for _ in w]
 for edge in e:
  assert type(edge) is list and len(edge)==2 and all(type(x) is int and 0<=x<n for x in edge)
  u,v=edge;assert u!=v and (u,v) not in seen;seen.add((u,v));pred[v].add(u)
 normalized=dict(works=w,edges=[list(x) for x in sorted(seen)])
 h=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert type(a) is dict and set(a)=={'schema','input_sha256','order'} and a['schema']=='universal-work-order-v1' and a['input_sha256']==h
 order=a['order'];assert type(order) is list and len(order)==n and all(type(i) is int and 0<=i<n for i in order) and len(set(order))==n
 completed=set()
 for i in order:
  ready=[j for j in range(n) if j not in completed and pred[j]<=completed]
  assert i in ready and w[i]==min(w[j] for j in ready)
  completed.add(i)
 return True
