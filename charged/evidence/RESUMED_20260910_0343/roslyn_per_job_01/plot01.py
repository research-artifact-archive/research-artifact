from pathlib import Path
import datetime,hashlib,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;O=P/'figure01';O.mkdir();source=P/'analysis01/SUMMARY.json';data=json.loads(source.read_text());assert data['status']=='PASS'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
fig,axes=plt.subplots(1,3,figsize=(8.4,2.45),sharey=True)
panels=[('foreground_us','Foreground batch'),('writer_response_median_us','Writer response'),('writer_service_median_us','Writer API service')];export=[]
for ax,(metric,title) in zip(axes,panels):
 rows=[r for r in data['paired_ratios'] if r['numerator']==['three',2] and r['denominator']==['two',2] and r['metric']==metric];assert [r['period_us'] for r in rows]==[0,10,100,1000]
 for i,r in enumerate(rows):
  mean=r['geometric_mean_ratio'];lo,hi=r['percentile95'];ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',color='#1b5e83',capsize=3,markersize=4,zorder=3);export.append(r)
 ax.axvline(1,color='#777777',linestyle='--',linewidth=1);ax.set_xlim(.65,2.9);ax.set_xticks([1,1.5,2,2.5]);ax.set_yticks(range(4));ax.set_yticklabels(['0','10','100','1000']);ax.set_title(title,fontweight='bold',fontsize=10);ax.grid(axis='x',alpha=.16);ax.set_xlabel('Three-mode / two-mode ratio')
axes[0].set_ylabel('Arrival interval (microseconds)');axes[0].invert_yaxis()
fig.tight_layout(w_pad=1.4)
fig.savefig(O/'paired_ratios.pdf',bbox_inches='tight',metadata={'Title':'Paired Roslyn shared-cap timing ratios','Author':'Anonymous Authors','Subject':'All four authored arrival intervals, shared r=2','Keywords':'descriptive; paired bootstrap; no latency guarantee'})
fig.savefig(O/'paired_ratios.png',dpi=180,bbox_inches='tight');plt.close(fig)
(O/'SOURCE_ROWS.json').write_text(json.dumps(export,indent=2)+'\n');(O/'RECEIPT.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),points=12,all_declared_periods=True,estimator='geometric mean of8 paired block ratios of process medians',interval='percentile95%,10000 fixed bootstrap resamples, no multiplicity correction'),indent=2)+'\n')
