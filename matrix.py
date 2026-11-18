"""Generate stable, resumable configuration IDs as CSV; stimuli are specified separately."""
import argparse,csv,itertools,sys,math
p=argparse.ArgumentParser(); p.add_argument('--count',action='store_true'); p.add_argument('--start',type=int,default=0); p.add_argument('--stop',type=int); p.add_argument('--ceiling-continuous',action='store_true'); a=p.parse_args()
axes=[('2520','990'),range(101),range(101),range(101) if a.ceiling_continuous else range(0,21,2),('00','10','01','11'),('C','L','OFF','BYP'),(0,1)]
n=math.prod(map(len,axes))
if a.count: print(n); sys.exit()
if not 0<=a.start<=n or (a.stop is not None and not a.start<=a.stop<=n): p.error('invalid range')
w=csv.writer(sys.stdout);w.writerow(['id','opamp','in_pct','out_pct','ceiling_pct' if a.ceiling_continuous else 'ceiling_mark','release_bits','mode','ds'])
for i in range(a.start,n if a.stop is None else a.stop):
    q=i; row=[]
    for axis in reversed(axes): q,r=divmod(q,len(axis));row.append(axis[r])
    w.writerow([i,*reversed(row)])
