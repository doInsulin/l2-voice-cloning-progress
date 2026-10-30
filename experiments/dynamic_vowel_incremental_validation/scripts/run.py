"""DVIV-20261030-01. Frozen-source existing-data validation; no audio access."""
from __future__ import annotations
import csv, hashlib, json, math
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[2]
RESEARCH=ROOT/'research'
PREV=RESEARCH/'33_dynamic_vowel_trajectory_20261022'
DYN=RESEARCH/'27_dynamic_vowel_analysis'
FINAL=RESEARCH/'final_confirmatory_experiment'
SEED=20261030
MODELS=('f5_tts','cosyvoice2','openvoice_v2')
VOWELS=('EH','AE','IH','IY')
POINTS=(20,35,50,65,80)
FIG=OUT/'figures'; FIG.mkdir(exist_ok=True)

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(name,rows):
    if not rows:raise RuntimeError('No data: '+name)
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def vec(row,prefix):return np.array([json.loads(row[prefix+'log_f1']),json.loads(row[prefix+'log_f2'])],float).T
def boot(vals,key,n=8000):
    a=np.asarray(vals,float);r=np.random.default_rng(int(hashlib.sha256(f'{SEED}|{key}'.encode()).hexdigest()[:8],16))
    z=a[r.integers(len(a),size=(n,len(a)))].mean(axis=1)
    return float(a.mean()),*map(float,np.quantile(z,[.025,.975]))
def summarize(rows,value,group,metric):
    by=defaultdict(list)
    for x in rows:by[x['speaker']].append(float(x[value]))
    vals=[np.mean(v) for v in by.values()]
    est,lo,hi=boot(vals,group+'|'+metric)
    return dict(analysis=group,metric=metric,estimate=est,ci_low_95=lo,ci_high_95=hi,n_tokens=len(rows),n_speakers=len(by))
def finish_plot(name,title,ylabel,note):
    plt.title(title);plt.ylabel(ylabel);plt.figtext(.02,.01,note,fontsize=8);plt.tight_layout(rect=[0,.04,1,1]);plt.savefig(FIG/name,dpi=180);plt.close()

def main():
    dyn=read(DYN/'dynamic_vowel_tokens.csv')
    natural=read(DYN/'natural_dynamic_vowels.csv')
    g=defaultdict(set)
    for row in dyn:
        if row['strict_dynamic_qc_pass']=='1':g[row['token_key']].add(row['model'])
    common={k for k,v in g.items() if set(MODELS)<=v}
    primary=[r for r in dyn if r['token_key'] in common]
    assert len(common)==214 and len(primary)==642
    # A: midpoint-anchored residual. All components use exactly the same tokens.
    arows=[]
    for r in primary:
        d=vec(r,'clone_')-vec(r,'original_')
        midpoint=float(np.sqrt(np.mean(d[2]**2)))
        residual=float(np.sqrt(np.mean((d-d[2])**2)))
        full=float(np.sqrt(np.mean(d**2)))
        arows.append(dict(model=r['model'],speaker=r['speaker'],phone=r['phone'],token_key=r['token_key'],
                          midpoint_rmse=midpoint,residual_rmse=residual,full_rmse=full,
                          residual_to_midpoint=residual/max(midpoint,1e-9)))
    # Natural matched speaker/vowel original-original residual baseline, first 200 deterministic pairs.
    nb=defaultdict(list)
    for r in natural:
        if r['strict_dynamic_qc_pass']=='1':nb[r['speaker'],r['phone']].append(r)
    natural_scale={}
    for key,items in nb.items():
        pairs=[]
        for i,x in enumerate(items):
            for y in items[i+1:]:
                if x['utterance_id']!=y['utterance_id']:
                    h=hashlib.sha256(f'{SEED}|{x["token_id"]}|{y["token_id"]}'.encode()).hexdigest()
                    pairs.append((h,x,y))
        v=[]
        for _,x,y in sorted(pairs,key=lambda z:z[0])[:200]:
            d=vec(x,'')-vec(y,'');v.append(float(np.sqrt(np.mean((d-d[2])**2))))
        natural_scale[key]=float(np.median(v))
    for r in arows:r['residual_nds']=r['residual_rmse']/natural_scale[r['speaker'],r['phone']]
    write('incremental_value_results.csv',arows)
    asummary=[]
    for m in MODELS:
        rr=[x for x in arows if x['model']==m]
        for met in ('midpoint_rmse','residual_rmse','full_rmse','residual_nds'):
            asummary.append(summarize(rr,met,'A|'+m,met))
    # LOSO fixed-shrinkage LDA: independent vowel identity label, secondary only.
    rows=[r for r in primary if r['model']=='f5_tts']
    speakers=sorted({r['speaker'] for r in rows})
    classes=list(VOWELS)
    def features(r,mode):
        v=vec(r,'clone_');mid=v[2];shape=(v-v.mean(axis=0)).ravel()
        return {'S1_static':mid,'S2_shape':shape,'S3_combined':np.r_[mid,shape],'S4_full':v.ravel()}[mode]
    def fitpredict(trainx,trainy,testx):
        mu=trainx.mean(axis=0);sd=trainx.std(axis=0);sd[sd<1e-8]=1
        x=(trainx-mu)/sd;z=(testx-mu)/sd
        means=np.array([x[trainy==j].mean(axis=0) for j in range(4)])
        resid=np.concatenate([x[trainy==j]-means[j] for j in range(4)])
        cov=resid.T@resid/max(1,len(x)-4);cov=.8*cov+.2*np.diag(np.diag(cov))+.15*np.eye(x.shape[1])
        inv=np.linalg.inv(cov);score=z@inv@means.T-.5*np.sum(means@inv*means,axis=1)
        return score.argmax(axis=1)
    label=np.array([classes.index(r['phone']) for r in rows]);sp=np.array([r['speaker'] for r in rows])
    predrows=[]
    for mode in ('S1_static','S2_shape','S3_combined','S4_full'):
        X=np.array([features(r,mode) for r in rows]);p=np.zeros(len(rows),int)
        for speaker in speakers:
            tr=sp!=speaker;te=~tr
            if len(set(label[tr]))<4:raise RuntimeError('LOSO training class missing')
            p[te]=fitpredict(X[tr],label[tr],X[te])
        predrows.extend(dict(feature_set=mode,speaker=r['speaker'],token_key=r['token_key'],true_phone=r['phone'],pred_phone=classes[p[i]]) for i,r in enumerate(rows))
    def perf(a):
        cm=np.array([[sum(x['true_phone']==t and x['pred_phone']==p for x in a) for p in classes] for t in classes])
        recall=np.diag(cm)/np.maximum(cm.sum(axis=1),1)
        prec=np.diag(cm)/np.maximum(cm.sum(axis=0),1)
        f1=2*prec*recall/np.maximum(prec+recall,1e-12)
        return float(np.mean(recall)),float(np.mean(f1)),cm
    perfrows=[]
    for mode in ('S1_static','S2_shape','S3_combined','S4_full'):
        sel=[x for x in predrows if x['feature_set']==mode]
        for s in ['ALL',*speakers]:
            rr=sel if s=='ALL' else [x for x in sel if x['speaker']==s]
            ba,mf,cm=perf(rr)
            perfrows.append(dict(feature_set=mode,speaker=s,n_tokens=len(rr),balanced_accuracy=ba,macro_f1=mf,confusion_json=json.dumps(cm.tolist())))
    write('classification_predictions.csv',predrows)
    write('classification_results.csv',perfrows)
    per={mode:{r['speaker']:r for r in perfrows if r['feature_set']==mode} for mode in ('S1_static','S2_shape','S3_combined','S4_full')}
    differences=[per['S3_combined'][s]['balanced_accuracy']-per['S1_static'][s]['balanced_accuracy'] for s in speakers]
    delta,delta_lo,delta_hi=boot(differences,'A|S3-S1|speaker')
    # Dimension-matched null: independent Gaussian columns, same 12D classifier and folds.
    base=np.array([features(r,'S1_static') for r in rows]);null_rows=[]
    for rep in range(100):
        noise=np.random.default_rng(SEED+rep).normal(size=(len(rows),10))
        X=np.column_stack([base,noise]);p=np.zeros(len(rows),int)
        for speaker in speakers:
            tr=sp!=speaker;te=~tr;p[te]=fitpredict(X[tr],label[tr],X[te])
        rr=[dict(true_phone=rows[i]['phone'],pred_phone=classes[p[i]]) for i in range(len(rows))]
        ba,_,_=perf(rr);null_rows.append(dict(repetition=rep,balanced_accuracy=ba,delta_vs_static=ba-per['S1_static']['ALL']['balanced_accuracy']))
    write('dimension_matched_negative_control.csv',null_rows)
    # B: frozen five-point DID re-evaluated as canonical functional contrast.
    pairs=read(PREV/'reconstruction_pair_results.csv')
    qc_tokens=read(PREV/'reconstruction_token_trajectories.csv')
    write('qc_attrition_tokens.csv',[dict(contrast=x['contrast'],pair_id=x['pair_id'],speaker=x['speaker'],role=x['role'],
                                      target_id=x['target_id'],original_duration_s=x['original_duration_s'],clone_duration_s=x['clone_duration_s'],
                                      original_reasons=x['original_reasons'],clone_reasons=x['clone_reasons'],
                                      strict_qc=x['pair_strict_qc'],track_qc=x['pair_track_qc']) for x in qc_tokens])
    axes=json.loads((FINAL/'natural_vowel_axes.json').read_text(encoding='utf-8'))['axes']
    brows=[];bsum=[];sensitivity=[]
    for support,qc in [('strict','strict_qc'),('track','track_qc')]:
        for contrast in ('EH_TO_AE','IH_TO_IY'):
            rr=[x for x in pairs if x['contrast']==contrast and x[qc]=='1']
            by=defaultdict(list)
            for x in rr:
                d=np.array(json.loads(x['did_log_trajectory']),float)
                axis=np.array(axes[x['speaker']][contrast]['axis_vector'],float)
                by[x['speaker']].append(d@axis/(axis@axis))
            sm={s:np.mean(v,axis=0) for s,v in by.items()}
            mat=np.array(list(sm.values()));avg=mat.mean(axis=0)
            rng=np.random.default_rng(SEED+len(rr));bootmat=mat[rng.integers(len(mat),size=(8000,len(mat)))].mean(axis=1)
            radius=float(np.quantile(np.max(np.abs(bootmat-avg),axis=1),.95))
            for j,t in enumerate(POINTS):
                e,lo,hi=boot(mat[:,j],f'B|{support}|{contrast}|{t}')
                brows.append(dict(support=support,contrast=contrast,time_pct=t,estimate=e,ci_low_95=lo,ci_high_95=hi,
                                  simultaneous_low=e-radius,simultaneous_high=e+radius,n_pairs=len(rr),n_speakers=len(sm)))
            for metric,v in [('five_point_mean',mat.mean(axis=1)),('midpoint',mat[:,2]),
                             ('early_late',(mat[:,3]+mat[:,4]-mat[:,0]-mat[:,1])/2)]:
                e,lo,hi=boot(v,f'B|{support}|{contrast}|{metric}')
                bsum.append(dict(support=support,contrast=contrast,metric=metric,estimate=e,ci_low_95=lo,ci_high_95=hi,n_pairs=len(rr),n_speakers=len(sm)))
            centered=mat-mat.mean(axis=1,keepdims=True)
            obs=float(np.sqrt(np.mean(centered.mean(axis=0)**2)))
            flip=rng.choice([-1,1],size=(20000,len(mat)))
            null=np.sqrt(np.mean((flip@centered/len(mat))**2,axis=1))
            pv=float((1+(null>=obs).sum())/(len(null)+1))
            bsum.append(dict(support=support,contrast=contrast,metric='time_shape_omnibus_rms',estimate=obs,signflip_p=pv,n_pairs=len(rr),n_speakers=len(sm)))
            sensitivity.append(dict(analysis='B',support=support,contrast=contrast,metric='shape_signflip_p',estimate=pv,n_tokens=len(rr),n_speakers=len(sm)))
    track_groups=defaultdict(set)
    for r in dyn:
        if r['track_qc_pass']=='1':track_groups[r['token_key']].add(r['model'])
    track_keys={k for k,v in track_groups.items() if set(MODELS)<=v}
    for model in MODELS:
        track=[]
        for r in dyn:
            if r['model']==model and r['token_key'] in track_keys:
                d=vec(r,'clone_')-vec(r,'original_')
                track.append(dict(speaker=r['speaker'],value=float(np.sqrt(np.mean((d-d[2])**2)))))
        z=summarize(track,'value','A|common_track|'+model,'residual_rmse')
        sensitivity.append(dict(analysis='A',support='common_track',contrast=model,metric='residual_rmse',estimate=z['estimate'],ci_low_95=z['ci_low_95'],ci_high_95=z['ci_high_95'],n_tokens=z['n_tokens'],n_speakers=z['n_speakers']))
    write('time_resolved_did_results.csv',brows+bsum)
    # C: same exact sentence/phone across speakers, closest duration, strict and cap.
    f5=[r for r in dyn if r['model']=='f5_tts' and r['strict_dynamic_qc_pass']=='1']
    contexts=defaultdict(list)
    def key(r):return (r['utterance_id'],r['word_index_0based'],r['phone_index_in_word_0based'],r['phone'])
    for r in f5:contexts[key(r)].append(r)
    crows=[]
    for target in f5:
        other=[x for x in contexts[key(target)] if x['speaker']!=target['speaker']]
        if not other:continue
        other.sort(key=lambda x:(abs(math.log(float(x['original_duration_s'])/float(target['original_duration_s']))),x['speaker']))
        cross=other[0]
        ratio=abs(math.log(float(cross['original_duration_s'])/float(target['original_duration_s'])))
        a=vec(target,'clone_');own=vec(target,'original_');b=vec(cross,'original_')
        def shape(x):return x-x.mean(axis=0)
        def dist(x,y):return float(np.sqrt(np.mean((x-y)**2)))
        crows.append(dict(speaker=target['speaker'],cross_speaker=cross['speaker'],phone=target['phone'],token_key=target['token_key'],
                          context='|'.join(key(target)),duration_log_ratio=ratio,duration_match=int(ratio<=math.log(1.25)),
                          own_shape=dist(shape(a),shape(own)),cross_shape=dist(shape(a),shape(b)),
                          shape_advantage=dist(shape(a),shape(b))-dist(shape(a),shape(own)),
                          own_mid=dist(a[2],own[2]),cross_mid=dist(a[2],b[2]),
                          midpoint_advantage=dist(a[2],b[2])-dist(a[2],own[2])))
    write('speaker_specific_preservation.csv',crows)
    cprim=[r for r in crows if r['duration_match']==1]
    csummary=[]
    for subset,rr in [('matched',cprim),('no_duration_cap',crows)]:
        for phone in ['ALL',*VOWELS]:
            x=rr if phone=='ALL' else [r for r in rr if r['phone']==phone]
            if len({r['speaker'] for r in x})<2:continue
            for metric in ('shape_advantage','midpoint_advantage'):
                by=defaultdict(list)
                for item in x:by[item['speaker']].append(float(item[metric]))
                z=dict(analysis='C|'+subset+'|'+phone,metric=metric,estimate=float(np.mean([np.mean(v) for v in by.values()])),
                       ci_low_95='',ci_high_95='',n_tokens=len(x),n_speakers=len(by),inference='DESCRIPTIVE_ONLY_BELOW_PRIMARY_80_TOKEN_GATE')
                csummary.append(z)
                sensitivity.append(dict(analysis='C',support=subset,contrast=phone,metric=metric,estimate=z['estimate'],n_tokens=len(x),n_speakers=z['n_speakers'],inference=z['inference']))
    write('sensitivity_results.csv',sensitivity)
    # Compact academic figures.
    plt.figure(figsize=(7,4));xx=np.arange(3)
    for i,m in enumerate(MODELS):
        data=[next(r for r in asummary if r['analysis']=='A|'+m and r['metric']==k) for k in ('midpoint_rmse','residual_rmse','full_rmse')]
        means=[z['estimate'] for z in data]
        errors=np.array([[z['estimate']-z['ci_low_95'] for z in data],[z['ci_high_95']-z['estimate'] for z in data]])
        plt.bar(xx+(i-1)*.23,means,width=.22,label=m,yerr=errors,capsize=2)
    plt.xticks(xx,['Midpoint','Residual after midpoint','Full five-point']);plt.legend(fontsize=8)
    finish_plot('a_midpoint_dynamic.png','Paired distortion on common strict support','log-formant RMSE','214 tokens / 16 speakers; speaker-equal mean and 95% speaker-bootstrap CI')
    for contrast in ('EH_TO_AE','IH_TO_IY'):
        v=[r for r in brows if r['support']=='strict' and r['contrast']==contrast and r.get('time_pct')]
        plt.figure(figsize=(6,4));x=np.array(POINTS);y=np.array([r['estimate'] for r in v]);lo=np.array([r['simultaneous_low'] for r in v]);hi=np.array([r['simultaneous_high'] for r in v])
        plt.plot(x,y,'o-',color='#146b8d');plt.fill_between(x,lo,hi,alpha=.18,color='#146b8d');plt.axhline(0,color='gray',lw=.8)
        plt.xlabel('Vowel time (%)');finish_plot('b_'+contrast.lower()+'.png',contrast+' matched canonical DID','Projection units',f"{v[0]['n_pairs']} pairs / {v[0]['n_speakers']} speakers; simultaneous 95% speaker-bootstrap band")
    plt.figure(figsize=(6,4));v=[r for r in brows if r['support']=='strict' and r['contrast']=='EH_TO_AE' and r.get('time_pct')]
    y=np.array([r['estimate'] for r in v]);plt.plot(POINTS,y,label='Total DID');plt.fill_between(POINTS,[r['simultaneous_low'] for r in v],[r['simultaneous_high'] for r in v],alpha=.15)
    plt.plot(POINTS,y-y.mean(),label='After removing mean');plt.axhline(0,color='gray',lw=.8);plt.legend()
    plt.xlabel('Vowel time (%)');finish_plot('b_eh_decomposition.png','EH: translation and temporal residual','Projection units','35 pairs / 11 speakers; descriptive curve; inference in DID CSV')
    plt.figure(figsize=(6,4));p=[r for r in perfrows if r['speaker']=='ALL'];ci=[]
    for item in p:
        vals=[r['balanced_accuracy'] for r in perfrows if r['feature_set']==item['feature_set'] and r['speaker']!='ALL']
        ci.append(boot(vals,'A|plot|'+item['feature_set']))
    plt.bar([r['feature_set'] for r in p],[z[0] for z in ci],color='#477c9a')
    for i,(z,item) in enumerate(zip(ci,p)):
        plt.plot([i,i],[z[1],z[2]],color='black',lw=1.5)
    plt.xticks(rotation=20)
    finish_plot('a_classification.png','LOSO vowel-category decoding','Balanced accuracy','214 clone tokens / 16 held-out speakers; lines = speaker-bootstrap CI around speaker-equal means')
    plt.figure(figsize=(6,4));plt.scatter([r['own_shape'] for r in cprim],[r['cross_shape'] for r in cprim],alpha=.6);lim=max([r['cross_shape'] for r in cprim]+[r['own_shape'] for r in cprim]);plt.plot([0,lim],[0,lim],color='gray');plt.xlabel('Own original shape distance (log RMSE)')
    finish_plot('c_matched_speaker.png','Exact-context speaker comparison','Cross-speaker original shape distance',f'{len(cprim)} tokens / {len(set(r["speaker"] for r in cprim))} speakers; duration ≤25%')
    plt.figure(figsize=(6,4));plt.bar(['Frozen PASS','Strict dynamic','Track dynamic'],[95,53,88],color=['#777','#146b8d','#88a'])
    finish_plot('qc_attrition.png','EH+IH matched-pair attrition','Pairs','95 frozen PASS; strict 35 EH+18 IH; track 39 EH+49 IH')
    plt.figure(figsize=(7,4));ss=read(PREV/'reconstruction_speaker_results.csv');eh=[r for r in ss if r['support']=='strict' and r['subset']=='all_speakers' and r['contrast']=='EH_TO_AE']
    plt.bar([r['speaker'] for r in eh],[float(r['translation_p']) for r in eh],color='#5686a1');plt.xticks(rotation=50)
    finish_plot('b_speaker_heterogeneity.png','EH five-point mean by speaker','Canonical projection units','35 matched pairs / 11 speakers; speaker means, varying pairs per speaker')
    result={'run_id':'DVIV-20261030-01','status':'COMPUTED','a_primary':asummary,'a_classification_overall':[r for r in perfrows if r['speaker']=='ALL'],
            'a_combined_minus_static_speaker_bootstrap':dict(estimate=delta,ci_low_95=delta_lo,ci_high_95=delta_hi,n_speakers=len(speakers)),
            'a_dimension_matched_null':dict(n_repetitions=100,mean_delta=float(np.mean([r['delta_vs_static'] for r in null_rows])),
                                            q025=float(np.quantile([r['delta_vs_static'] for r in null_rows],.025)),
                                            q975=float(np.quantile([r['delta_vs_static'] for r in null_rows],.975))),
            'b_summary':bsum,'c_summary':csummary,'c_candidate_tokens':len(crows),'c_duration_matched_tokens':len(cprim),
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [DYN/'dynamic_vowel_tokens.csv',DYN/'natural_dynamic_vowels.csv',PREV/'reconstruction_pair_results.csv',FINAL/'natural_vowel_axes.json']}}
    (OUT/'analysis_summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print(json.dumps({'A':len(arows),'B':len(brows),'C':len(crows),'C_matched':len(cprim),'figures':len(list(FIG.glob('*.png')))},indent=2))
if __name__=='__main__':main()
