"""Resumable frozen F5 generation for one final-confirmatory phase.

Successful audio is never regenerated. A failed row is preserved for technical audit.
"""
from __future__ import annotations

import argparse,csv,gc,hashlib,json,os,time,traceback,wave
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LOCK=ROOT/"research/05_runtime/f5_tts_runtime_lock.json"
FF=ROOT/"research/.audit_deps/f5_ffmpeg_shared/Library/bin"
TL=Path(r"D:\CondaEnvs\MTN_New\Lib\site-packages\torch\lib")
PHASES=("preservation","segmental","f0","timing")
IDENTITY=("model","phase","condition","target_id","speaker","utterance_id","canonical_text",
          "original_wav","pair_id","role","token_id","reference_wav","reference_text",
          "reference_sha256","seed","fix_duration","output_wav")


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()


def read(path:Path)->list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def save(path:Path,rows:list[dict])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        f.flush();os.fsync(f.fileno())
    for attempt in range(20):
        try:
            os.replace(tmp,path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.2)


def wav_meta(path:Path):
    with wave.open(str(path),"rb") as w:return w.getframerate(),w.getnchannels(),w.getnframes()/w.getframerate()


def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument("phase",choices=PHASES);ap.add_argument("--max-new",type=int,default=0)
    args=ap.parse_args();phase=args.phase
    freeze=json.loads((HERE/"generation_design_freeze.json").read_text(encoding="utf-8"))
    frozen=HERE/"generation_manifests"/f"f5_tts_{phase}.csv"
    if sha(frozen)!=freeze["manifests"][frozen.name]["sha256"]:raise RuntimeError("Frozen generation manifest changed")
    expected=read(frozen)
    execution=HERE/"generation_execution"/frozen.name
    rows=read(execution) if execution.exists() else expected
    if len(rows)!=len(expected) or any(tuple(r[k] for k in IDENTITY)!=tuple(e[k] for k in IDENTITY)
                                   for r,e in zip(rows,expected)):
        raise RuntimeError("Execution identity differs from frozen manifest")
    if not execution.exists():save(execution,rows)
    lock=json.loads(LOCK.read_text(encoding="utf-8"));f5=lock["f5_tts"];voc=lock["vocos"]
    if sha(Path(f5["checkpoint_local_path"]))!=f5["checkpoint_sha256"] or sha(Path(voc["checkpoint_local_path"]))!=voc["checkpoint_sha256"]:
        raise RuntimeError("Pinned F5/Vocos weight hash drift")
    os.add_dll_directory(str(FF));os.add_dll_directory(str(TL))
    os.environ["PATH"]=os.pathsep.join([str(FF),str(TL),os.environ["PATH"]])
    import torch
    if not torch.cuda.is_available():raise RuntimeError("Frozen CUDA device unavailable")
    from f5_tts.api import F5TTS
    model=F5TTS(model=f5["model"],ckpt_file=f5["checkpoint_local_path"],vocab_file=f5["vocab_path"],
                ode_method=f5["parameters"]["ode_method"],use_ema=f5["parameters"]["use_ema"],
                vocoder_local_path=str(Path(voc["checkpoint_local_path"]).parent),device="cuda:0")
    checked_refs=set();new=0
    for i,row in enumerate(rows,1):
        out=Path(row["output_wav"])
        if row["status"]=="SUCCESS":
            if not out.exists() or sha(out)!=row["output_sha256"]:raise RuntimeError(f"Successful output drift: {out}")
            continue
        if row["status"]=="FAIL":continue
        if args.max_new and new>=args.max_new:break
        if row["reference_wav"] not in checked_refs:
            if sha(Path(row["reference_wav"]))!=row["reference_sha256"]:raise RuntimeError("Reference hash drift")
            checked_refs.add(row["reference_wav"])
        out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists():
            sr,ch,dur=wav_meta(out)
            if sr!=24000 or ch!=1 or dur<=0:raise RuntimeError(f"Pending output exists but invalid: {out}")
            row.update(output_sha256=sha(out),sample_rate_hz=sr,channels=ch,duration_s=f"{dur:.9f}",
                       status="SUCCESS",exception="RECOVERED_EXISTING_FILE_AFTER_INTERRUPTION",elapsed_s="")
            save(execution,rows);continue
        partial=out.with_suffix(".partial.wav");partial.unlink(missing_ok=True)
        started=time.perf_counter();new+=1
        try:
            fixed=float(row["fix_duration"]) if row["fix_duration"] else f5["parameters"]["fix_duration"]
            _,sr,_=model.infer(ref_file=row["reference_wav"],ref_text=row["reference_text"],
                               gen_text=row["canonical_text"],file_wave=str(partial),file_spec=None,
                               seed=int(row["seed"]),nfe_step=int(f5["parameters"]["nfe_step"]),
                               cfg_strength=float(f5["parameters"]["cfg_strength"]),
                               sway_sampling_coef=float(f5["parameters"]["sway_sampling_coef"]),
                               speed=float(f5["parameters"]["speed"]),fix_duration=fixed,
                               remove_silence=bool(f5["parameters"]["remove_silence"]),show_info=lambda *_:None)
            actual_sr,ch,dur=wav_meta(partial)
            if actual_sr!=24000 or int(sr)!=actual_sr or ch!=1 or dur<=0:raise RuntimeError("Generated WAV technical invalid")
            os.replace(partial,out)
            row.update(output_sha256=sha(out),sample_rate_hz=actual_sr,channels=ch,duration_s=f"{dur:.9f}",
                       status="SUCCESS",exception="",elapsed_s=f"{time.perf_counter()-started:.3f}")
        except Exception as exc:
            partial.unlink(missing_ok=True)
            row.update(status="FAIL",exception=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                       elapsed_s=f"{time.perf_counter()-started:.3f}")
        save(execution,rows);gc.collect();torch.cuda.empty_cache()
        if new%8==0 or row["status"]=="FAIL":
            print(json.dumps({"phase":phase,"processed_new":new,"total":len(rows),
                              "success":sum(r["status"]=="SUCCESS" for r in rows),
                              "fail":sum(r["status"]=="FAIL" for r in rows)}),flush=True)
    counts={x:sum(r["status"]==x for r in rows) for x in ("SUCCESS","FAIL","PENDING")}
    summary={"phase":phase,"rows":len(rows),"counts":counts,
             "status":"COMPLETE" if counts["SUCCESS"]+counts["FAIL"]==len(rows) else "RUNNING_OR_PARTIAL",
             "checkpoint_sha256":f5["checkpoint_sha256"],"vocos_sha256":voc["checkpoint_sha256"],
             "device":torch.cuda.get_device_name(0),"execution_manifest_sha256":sha(execution),
             "updated_at":datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (HERE/"generation_execution"/f"f5_tts_{phase}_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
