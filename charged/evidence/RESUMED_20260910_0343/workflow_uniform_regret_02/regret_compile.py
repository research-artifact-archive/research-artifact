"""Emit a minimum uniform-additive-loss policy for the repair interface.

The archived threshold constructor remains unchanged. This wrapper adds the
proved tolerance and a budget-unaware executable selector. Costs are exact
integer or rational units supplied by the caller; no native calibration occurs.
"""
from pathlib import Path
import importlib.util

source=Path(__file__).resolve().parent.parent/'partial_repair_toll_dag_01/threshold_compile.py'
spec=importlib.util.spec_from_file_location('preserved_repair_thresholds',source)
thresholds=importlib.util.module_from_spec(spec);spec.loader.exec_module(thresholds)

def compile_regret(jobs,edges,retries,toll):
    result=thresholds.compile_thresholds(jobs,edges,retries,toll,export=True)
    loss=-result['root_margin']
    assert loss>=0
    return dict(schema='repair-workflow-uniform-additive-loss-v1',
                optimal_additive_loss=loss,threshold_certificate=result['certificate'])

class Policy:
    """The selector observes dirty masks, never a write budget or count."""
    def __init__(self,certificate):
        assert certificate['schema']=='repair-workflow-uniform-additive-loss-v1'
        self.c=certificate['threshold_certificate'];self.delta=certificate['optimal_additive_loss']
        self.rows={tuple(row['state']):row for row in self.c['thresholds']}
        self.s=(1<<len(self.c['jobs']))-1;self.t=self.c['retries'];self.e=0;self.paid=0

    def next_job(self):
        return self.rows[self.s,self.t,self.e]['job'] if self.s else None

    def observe(self,dirty_mask):
        i=self.next_job()
        if i is None:raise ValueError('already completed')
        o=next((o for o in self.c['jobs'][i]['observations'] if o['mask']==dirty_mask),None)
        if o is None:raise ValueError('unreachable dirty mask')
        nxt=min(self.e+o['c'],self.c['ceiling']);k=self.c['toll'];after=self.s^(1<<i)
        if self.paid+k+o['w']<=self.rows[after,self.t,nxt]['value']+self.delta:
            self.s=after;self.paid+=k+o['w'];action='accept'
        elif self.t and self.paid+k<=self.rows[self.s,self.t-1,nxt]['value']+self.delta:
            self.t-=1;self.paid+=k;action='reject'
        else:raise ValueError('invalid certificate: no feasible shifted action')
        self.e=nxt
        return dict(job=i,dirty_mask=dirty_mask,action=action,completed=self.s==0,
                    cost=self.paid,minimum_consistent_count_clipped=self.e)
