# Polynomial source generation. No expanded-state construction or oracle call.
OPS={
  0:[(1,[(1,0,'nw')]),(2,[(2,0,'n0')]),(3,[(2,0,'n0'),(0,1,'n0')]),(4,[(4,0,'nwp')])],
  1:[(5,[(4,0,'n0'),(0,1,'n0'),(1,1,'n0')]),(6,[(3,0,'n0'),(2,1,'n0')]),
     (7,[(4,0,'n0'),(4,1,'nwp')]),(8,[(1,0,'n0'),(0,1,'n0')]),(9,[(0,0,'n0')])],
  2:[(10,[(3,0,'nwp')]),(11,[(0,0,'n0')])],
  3:[(12,[(4,0,'n0')]),(13,[(1,0,'n0')]),(14,[(2,0,'n0')])]
}
def export(jobs,B,initial=None):
    n=len(jobs);initial=[0]*n if initial is None else initial
    lines=['smg','player controller [c] endplayer','player nature [n0],[nw],[nwp] endplayer',
           'formula done = '+' & '.join(f'x{i}=4' for i in range(n))+';']
    for i in range(n):lines.append(f'formula e{i} = (x{i}=0 | x{i}=1) ? 1 : 0;')
    lines.append(f'formula avail{n} = 0;')
    for i in reversed(range(n)):lines.append(f'formula avail{i} = e{i}+avail{i+1};')
    lines.extend(['module protocol',' phase : [0..16] init 0;',f' k : [0..{n+1}] init 0;',' cnt : [0..2] init 0;',
                  f' b : [0..{max(B,1)}] init {B};'])
    for i in range(n):lines.extend([f' x{i} : [0..4] init {initial[i]};',f' s{i} : [0..1] init 0;'])
    for i in range(n):
        for x,actions in OPS.items():
            for op,outcomes in actions:
                lines.append(f" [c] phase=0 & x{i}={x} -> (phase'={op}) & (k'={i+1});")
                for target,spent,label in outcomes:
                    guard=f'phase={op} & k={i+1}'+(' & b>0' if spent else '')
                    update=f"(phase'=0) & (k'=0) & (x{i}'={target})"+(" & (b'=b-1)" if spent else '')
                    lines.append(f' [{label}] {guard} -> {update};')
    lines.append(" [c] phase=0 & avail0>=2 -> (phase'=15) & (k'=1) & (cnt'=0);")
    for i in range(n):
        lines.append(f" [c] phase=15 & k={i+1} & e{i}=1 & cnt+1+avail{i+1}>=2 -> (s{i}'=1) & (cnt'=min(2,cnt+1)) & (k'={i+2});")
        lines.append(f" [c] phase=15 & k={i+1} & cnt+avail{i+1}>=2 -> (s{i}'=0) & (k'={i+2});")
    lines.append(f" [c] phase=15 & k={n+1} & cnt=2 -> (phase'=16) & (k'=1) & (cnt'=0);")
    for i in range(n):
        lines.append(f" [n0] phase=16 & k={i+1} & s{i}=0 -> (k'={i+2});")
        common=f"(s{i}'=0) & (k'={i+2})"
        lines.append(f" [n0] phase=16 & k={i+1} & s{i}=1 & x{i}=0 -> {common} & (x{i}'=2);")
        lines.append(f" [n0] phase=16 & k={i+1} & s{i}=1 & x{i}=1 -> {common} & (x{i}'=3);")
        lines.append(f" [n0] phase=16 & k={i+1} & s{i}=1 & x{i}=1 & b>0 -> {common} & (x{i}'=2) & (b'=b-1);")
    lines.extend([f" [n0] phase=16 & k={n+1} -> (phase'=0) & (k'=0);",
                  ' [n0] phase=0 & done -> true;','endmodule','label "goal" = phase=0 & done;','rewards "work"'])
    for i,(w,p) in enumerate(jobs):lines.extend([f' [nw] k={i+1} : {w};',f' [nwp] k={i+1} : {w+p};'])
    lines.extend(['endrewards',''])
    return '\n'.join(lines)
