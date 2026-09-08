"""Exact cap-certificate verification with shared-subtree sequence comparison.

Uses the proved concave cap theorem; does not import a constructor, use hashes
for equality, enumerate budgets, or claim an unproved complexity for traversal.
"""
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('persistent_certificate_shape',ROOT.parent/'fixed_order_profile_02/checker.py')
shape=importlib.util.module_from_spec(spec);spec.loader.exec_module(shape)


class Scan:
    def __init__(self,data):
        self.nodes=data['nodes']
        self.queries=0;self.query_nodes=0;self.range_nodes=0
        self.expanded_chunks=0;self.identical_chunks=0;self.run_comparisons=0
        self.positions_compared=0

    def size(self,index):return 0 if index==-1 else self.nodes[index][5]

    def mass(self,index,budget):
        total=0;self.queries+=1
        while index!=-1 and budget>0:
            self.query_nodes+=1
            h,count,left,right,_,size,area,_,_,_=self.nodes[index]
            if budget>=size:return total+area
            left_size=self.size(left)
            if budget<=left_size:
                index=left
            else:
                total+=0 if left==-1 else self.nodes[left][6]
                budget-=left_size
                take=min(count,budget);total+=h*take;budget-=take;index=right
        return total

    def high_length(self,index,c):
        total=0;self.queries+=1
        while index!=-1:
            self.query_nodes+=1;h,count,left,right,*_=self.nodes[index]
            if h<c:index=left
            else:total+=self.size(left)+count;index=right
        return total

    def chunks(self,index,lo,hi):
        assert 0<=lo<=hi<=self.size(index)
        out=[]
        def visit(index,lo,hi):
            if lo==hi:return
            self.range_nodes+=1
            h,count,left,right,_,size,*_=self.nodes[index]
            if lo==0 and hi==size:
                out.append(('N',index,size));return
            left_size=self.size(left)
            if lo<left_size:visit(left,lo,min(hi,left_size))
            a=max(lo,left_size);b=min(hi,left_size+count)
            if a<b:out.append(('R',h,b-a))
            if hi>left_size+count:visit(right,max(0,lo-left_size-count),hi-left_size-count)
        visit(index,lo,hi)
        return out

    def expand(self,chunk,stack):
        self.expanded_chunks+=1
        _,index,_=chunk;h,count,left,right,*_=self.nodes[index]
        if right!=-1:stack.append(('N',right,self.size(right)))
        stack.append(('R',h,count))
        if left!=-1:stack.append(('N',left,self.size(left)))

    def equal_ranges(self,one,two,lo,hi):
        left=list(reversed(self.chunks(one,lo,hi)))
        right=list(reversed(self.chunks(two,lo,hi)))
        while left and right:
            a=left.pop();b=right.pop()
            if a[0]==b[0]=='N' and a[1]==b[1]:
                assert a[2]==b[2]
                self.identical_chunks+=1;self.positions_compared+=a[2]
            elif a[0]==b[0]=='R':
                self.run_comparisons+=1
                if a[1]!=b[1]:return False
                used=min(a[2],b[2]);self.positions_compared+=used
                if a[2]>used:left.append(('R',a[1],a[2]-used))
                if b[2]>used:right.append(('R',b[1],b[2]-used))
            elif a[0]=='N' and (b[0]=='R' or a[2]>=b[2]):
                self.expand(a,left);right.append(b)
            else:
                self.expand(b,right);left.append(a)
        return not left and not right

    def constant(self,index,lo,hi,h):
        for kind,key,count in self.chunks(index,lo,hi):
            if kind=='R':
                if key!=h:return False
            else:
                row=self.nodes[key]
                if row[7]!=h or row[8]!=h:return False
        return True

    def counters(self):
        return {k:v for k,v in vars(self).items() if k!='nodes'}


def check(data):
    structural=shape.structure(data);scan=Scan(data);roots=data['roots']
    for cursor,job in enumerate(data['order']):
        own=roots[cursor];child=roots[cursor+1];c,p=data['input']['cp'][job]
        threshold=data['protect_at_budget'][cursor]
        if p==0:
            assert threshold==0 and scan.size(own)==scan.size(child)
            assert scan.equal_ranges(own,child,0,scan.size(child)),('zero_premium_changes_profile',cursor)
            continue
        a=scan.high_length(child,c)
        assert threshold>a,('threshold_before_positive_deficit',cursor)
        fa=scan.mass(child,a);before=scan.mass(child,threshold-1);at=scan.mass(child,threshold)
        prior_deficit=c*(threshold-1-a)-(before-fa)
        deficit=c*(threshold-a)-(at-fa)
        assert prior_deficit<p<=deficit,('threshold_not_first_crossing',cursor)
        crossing=(at-before)+p-prior_deficit
        assert 0<crossing<=c
        assert scan.size(own)==max(scan.size(child),threshold),('wrong_support',cursor)
        assert scan.equal_ranges(own,child,0,a),('prefix_differs',cursor)
        assert scan.constant(own,a,threshold-1,c),('plateau_differs',cursor)
        assert scan.constant(own,threshold-1,threshold,crossing),('crossing_differs',cursor)
        if threshold<scan.size(child):
            assert scan.equal_ranges(own,child,threshold,scan.size(child)),('suffix_differs',cursor)
    return dict(violations=[],shape=structural,counts=scan.counters(),
                domain='ALL_NONNEGATIVE_INTEGER_BUDGETS_BY_CONCAVE_CAP_THEOREM',
                stored_thresholds_checked=True,constructor_imports=False,
                equality='EXACT_SHARED_IDENTITIES_AND_INTEGER_RUN_COMPARISON',
                verified_complexity='output-sensitive traversal; no stronger bound asserted')
