from pathlib import Path
import hashlib,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
D=Path(__file__).resolve().parent;data=json.loads((D/'analysis01/SUMMARY.json').read_text());O=D/'figures02';O.mkdir()
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':8,'axes.labelsize':8,'axes.titlesize':8.5,'legend.fontsize':7,'xtick.labelsize':7,'ytick.labelsize':7,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
cells={(x['mode'],x['r'],x['period_us']):x for x in data['cells']};forks=data['per_fork_cells'];periods=[0,10,100,1000];xx=np.arange(4)
styles={'baseline':('#777777','--','s','Unmodified'),'original':('#333333',':','^','Instrumented original'),'two':('#b66a26','--','D','Two modes'),'three':('#1e7097','-','o','Three modes')}
fig,axs=plt.subplots(2,2,figsize=(5.65,4.15),sharex=True,layout='constrained')
for row,r in enumerate([0,2]):
 for col,key in enumerate(['foreground_us','background_e2e_p95_us']):
  ax=axs[row,col]
  for arm in ['baseline','original','two','three']:
   rr=r if arm in ['two','three'] else 0;color,style,marker,label=styles[arm]
   ys=[cells[(arm,rr,d)]['metrics'][key]['median'] for d in periods]
   # Small points are each process's median, not request-level confidence intervals.
   for i,d in enumerate(periods):
    points=[f['metrics'][key]['median'] for f in forks if (f['mode'],f['r'],f['period_us'])==(arm,rr,d)]
    ax.scatter(np.full(6,i)+np.linspace(-.065,.065,6),points,s=5,color=color,alpha=.35,linewidths=0,zorder=1)
   ax.plot(xx,ys,color=color,linestyle=style,marker=marker,markersize=3.5,linewidth=1.2,label=label,zorder=3)
  ax.set_yscale('log');ax.grid(True,axis='y',which='major',alpha=.19);ax.set_xlim(-.2,3.2)
  ax.set_title(('Foreground batch' if col==0 else 'Background request p95')+f', r = {r}')
  ax.set_ylabel('Time (µs)');ax.set_xticks(xx,['Burst','10','100','1,000'])
  if row==1:ax.set_xlabel('Requested background interval (µs)')
handles,labels=axs[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncols=2,frameon=False)
fig.savefig(O/'arrival_tradeoffs.pdf',metadata={'Title':'Roslyn independent-arrival validation','Author':'Anonymous','Subject':'Medians across60 batches per cell; faint dots are six process medians'})
fig.savefig(O/'arrival_tradeoffs.png',dpi=240)
(O/'RECEIPT.json').write_text(json.dumps({'input_sha256':hashlib.sha256((D/'analysis01/SUMMARY.json').read_bytes()).hexdigest(),'series':'all24 arm/interval cells; r0/r2 panels; medians of60 batches; faint dots six process medians','new_experiments':0,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.glob('*') if p.suffix in ['.pdf','.png']}},indent=2)+'\n')
print(str(O/'arrival_tradeoffs.png'))
