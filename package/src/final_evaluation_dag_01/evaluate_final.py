"""Final wrapper keeps the successful preflight implementation immutable."""
import time
import evaluate as original
import lemmas
def evaluate(case):
    start=time.perf_counter()
    row,encoded=original.evaluate(case)
    row['lemma_checks']=lemmas.check(case)
    row['elapsed_seconds']=time.perf_counter()-start
    return row,encoded
