"""Indexed queries and original charged transitions after independent checking."""
from bisect import bisect_right
import copy
import verify

class Policy:
    def __init__(self,data,expected_input=None):
        data=copy.deepcopy(data)
        self.receipt=verify.check(data,expected_input)
        self.route=data['route'];self.jobs=tuple(tuple(r) for r in data['input']['jobs']);self.n=len(self.jobs)
        self.prices=tuple((w+min(v,g+r),p+g+r-min(v,g+r),g+r-min(v,g+r),w+p) for w,p,g,v,r in self.jobs)
        self.baseline=data['baseline'];self.entry=dict(data['entry']);inner=data['backend']
        if self.route=='compatible_reduced':
            self.order=tuple(inner['order']);self.ends=[];self.areas=[];self.heights=[];length=area=0
            for h,count in inner['value_slopes']:
                length+=count;area+=h*count;self.ends.append(length);self.areas.append(area);self.heights.append(h)
            self.ends=tuple(self.ends);self.areas=tuple(self.areas);self.heights=tuple(self.heights);self.area=area
            premiums=[0]*(self.n+1);normals=[0]*(self.n+1)
            for q in range(self.n-1,-1,-1):
                i=self.order[q];premiums[q]=premiums[q+1]+self.prices[i][1];normals[q]=normals[q+1]+self.prices[i][0]
            self.premium_caps=tuple(premiums);self.normal_caps=tuple(normals)
        else:
            self.curves={int(k):tuple(tuple(r) for r in f) for k,f in inner['curves'].items()}
            self.starts={k:tuple(r[0] for r in f) for k,f in self.curves.items()}
            self.available={int(k):tuple(v['available']) for k,v in inner['actions'].items()}

    def state(self,state):
        state=self.entry if state is None else state
        if type(state) is not dict or set(state)!={'kind','value'} or type(state['value']) is not int:raise ValueError('tagged state required')
        x=state['value']
        if self.route=='compatible_reduced':
            if state['kind']!='cursor' or not 0<=x<=self.n:raise ValueError('cursor state')
        elif state['kind']!='mask' or x not in self.curves:raise ValueError('reachable unfinished-mask state')
        return x
    def _root(self,b):
        if b==0:return 0
        i=bisect_right(self.ends,b)
        if i==len(self.ends):return self.area
        before_b=self.ends[i-1] if i else 0;before_v=self.areas[i-1] if i else 0
        return before_v+self.heights[i]*(b-before_b)
    def _value(self,x,b):
        if self.route=='compatible_reduced':return min(self._root(b),self.premium_caps[x])
        f=self.curves[x];k=bisect_right(self.starts[x],b)-1;start,y,slope=f[k];return y+slope*(b-start)
    def excess(self,budget,state=None):
        if type(budget) is not int or budget<0:raise ValueError('nonnegative integer budget required')
        return self._value(self.state(state),budget)
    def normal(self,state=None):
        x=self.state(state)
        return self.normal_caps[x] if self.route=='compatible_reduced' else sum(c for i,(c,p,d,s) in enumerate(self.prices) if x>>i&1)
    def total(self,budget,state=None):return self.normal(state)+self.excess(budget,state)
    def choose(self,budget,state=None):
        own=self.excess(budget,state);x=self.state(state)
        if (self.route=='compatible_reduced' and x==self.n) or (self.route!='compatible_reduced' and x==0):return None
        candidates=[]
        ready=(self.order[x],) if self.route=='compatible_reduced' else self.available[x]
        for i in ready:
            child=x+1 if self.route=='compatible_reduced' else x^(1<<i)
            normal=self._value(child,budget);c,p,d,s=self.prices[i]
            candidates.append((p+normal,0,i,'protected'))
            candidates.append((normal if budget==0 else max(normal,c+self._value(x,budget-1)),1,i,'cheap'))
            candidates.append((d+normal if budget==0 else d+max(normal,s+self._value(child,budget-1)),2,i,'cached'))
        value,priority,i,mode=min(candidates);assert value==own,'chosen original branch differs from certificate'
        w,p,g,v,r=self.jobs[i]
        call='fresh_callback' if mode=='protected' else 'cached_callback' if mode=='cached' else 'conditional_commit' if v<=g+r else 'validation_callback'
        return dict(job=i,mode=mode,call=call,excess=value,worst_total=self.normal(state)+value)
    def advance(self,budget,state,mode,outcome):
        choice=self.choose(budget,state)
        if choice is None or choice['mode']!=mode:raise ValueError('mode is not the selected policy action')
        if outcome not in ('success','failure'):raise ValueError('expected success or failure')
        if outcome=='failure' and (mode=='protected' or budget==0):raise ValueError('outcome impossible under the declared contract')
        x=self.state(state);i=choice['job'];w,p,g,v,r=self.jobs[i]
        completed=mode!='cheap' or outcome=='success';next_budget=budget-(outcome=='failure')
        target=x if not completed else x+1 if self.route=='compatible_reduced' else x^(1<<i)
        next_state=dict(kind=self.entry['kind'],value=target)
        paid=w+p+g+r if mode=='protected' else w+min(v,g+r) if mode=='cheap' else w+g+r+(w+p if outcome=='failure' else 0)
        assert paid+self.total(next_budget,next_state)<=self.total(budget,state),'original charge/transition exceeds the checked cap'
        return dict(state=next_state,budget=next_budget,charged_cost=paid,completed_job=i if completed else None)
