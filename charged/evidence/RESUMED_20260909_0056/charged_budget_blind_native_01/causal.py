"""New policy checking plus unchanged source-model feasibility and sequence replay."""
import traceback
import strong,fixed_policy,model,search,sequence_checker

def verify(case,run,row):
    try:static=strong.verify_run(case,run,row,fixed_policy.ordinary)
    except AssertionError as exc:return dict(status='REJECTED',accepted=False,layer='fixed_policy_and_static',reason=str(exc),error=traceback.format_exc())
    except Exception:return dict(status='CHECKER_FAILURE',accepted=None,layer='fixed_policy_and_static',error=traceback.format_exc())
    try:program=model.build(case,run,row)
    except AssertionError as exc:return dict(status='REJECTED',accepted=False,layer='source_model',reason=str(exc),error=traceback.format_exc())
    except Exception:return dict(status='CHECKER_FAILURE',accepted=None,layer='source_model',error=traceback.format_exc())
    try:result=search.solve(program,max_states=100000,seconds=2)
    except Exception:return dict(status='CHECKER_FAILURE',accepted=None,layer='search',error=traceback.format_exc())
    if result['status']=='FEASIBLE':
        try:checked=sequence_checker.check(program,result['certificate'])
        except Exception:return dict(status='CHECKER_FAILURE',accepted=None,layer='sequence_check',error=traceback.format_exc())
        return dict(status='FEASIBLE',accepted=True,static=static,sequence_check=checked,search_states=result['visited_states'],certificate=result['certificate'])
    return dict(status=result['status'],accepted=False if result['status']=='INFEASIBLE' else None,search=result)
