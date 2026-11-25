"""Frozen 160-row CosyVoice 2 preservation generation, resumable by row."""
from __future__ import annotations
import csv,hashlib,json,os,random,sys,time,traceback
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/".model_cache/src/CosyVoice"
sys.path[:0]=[str(SOURCE),str(SOURCE/"third_party/Matcha-TTS"),str(ROOT/"research/10_multimodel_runtime")]
from runtime_storage import configure
configure("cosyvoice2")
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"})
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice_audio_compat import install
install()

MODEL_DIR=ROOT/".model_cache/cosyvoice2/eec1ae6c79877dbd9379285cf8789c9e0879293d"
FROZEN=HERE/"generation_manifests/cosyvoice2_preservation.csv"
EXECUTION=HERE/"generation_execution/cosyvoice2_preservation.csv"
IDENTITY=("model","phase","condition","target_id","speaker","utterance_id","canonical_text",
          "original_wav","reference_wav","reference_text","reference_sha256","seed","output_wav")


def sha(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()


def read(p:Path):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def save(rows:list[dict]):
    EXECUTION.parent.mkdir(parents=True,exist_ok=True)
    tmp=EXECUTION.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);f.flush();os.fsync(f.fileno())
    for attempt in range(20):
        try:
            os.replace(tmp,EXECUTION)
            break
        except PermissionError:
            if attempt == 19:raise
            time.sleep(.2)


def meta(p:Path):
    info=sf.info(p)
    if info.samplerate!=24000 or info.channels!=1 or info.frames<=0:raise RuntimeError("native WAV invalid")
    return info


def main():
    freeze=json.loads((HERE/"generation_design_freeze.json").read_text(encoding="utf-8"))
    if sha(FROZEN)!=freeze["manifests"][FROZEN.name]["sha256"]:raise RuntimeError("Frozen manifest drift")
    expected=read(FROZEN);rows=read(EXECUTION) if EXECUTION.exists() else expected
    if len(rows)!=160 or any(tuple(r[k] for k in IDENTITY)!=tuple(e[k] for k in IDENTITY)
                            for r,e in zip(rows,expected)):raise RuntimeError("Execution identity drift")
    if not EXECUTION.exists():save(rows)
    runtime=json.loads((ROOT/"research/10_multimodel_runtime/cosyvoice2_runtime_lock.json").read_text(encoding="utf-8"))
    if runtime["status"]!="RUNTIME_LOCK_PASS" or not torch.cuda.is_available():raise RuntimeError("Pinned runtime unavailable")
    report_path=ROOT/"research/10_multimodel_runtime/pinned_weight_download_report.json"
    if sha(report_path)!=runtime["official_weight_report_sha256"]:raise RuntimeError("Pinned weight report drift")
    report=json.loads(report_path.read_text(encoding="utf-8"))
    for item in report["files"]:
        if item["model"]=="cosyvoice2" and item["pinned_weight"] and sha(Path(item["local_path"]))!=item["sha256"]:
            raise RuntimeError(f"Pinned CosyVoice 2 weight drift: {item['file']}")
    model=CosyVoice2(str(MODEL_DIR),load_jit=False,load_trt=False,load_vllm=False,fp16=False)
    checked=set()
    for i,row in enumerate(rows,1):
        output=Path(row["output_wav"])
        if row["status"]=="SUCCESS":
            if sha(output)!=row["output_sha256"]:raise RuntimeError(f"Completed WAV drift: {output}")
            continue
        if row["status"]=="FAIL":continue
        if row["reference_wav"] not in checked:
            if sha(Path(row["reference_wav"]))!=row["reference_sha256"]:raise RuntimeError("Reference drift")
            checked.add(row["reference_wav"])
        output.parent.mkdir(parents=True,exist_ok=True)
        if output.exists():
            info=meta(output)
            row.update(status="SUCCESS",output_sha256=sha(output),sample_rate_hz=info.samplerate,
                       channels=info.channels,duration_s=info.duration,exception="RECOVERED_EXISTING")
            save(rows);continue
        temp=output.with_suffix(".tmp.wav");temp.unlink(missing_ok=True);started=time.perf_counter()
        seed=int(row["seed"]);random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        try:
            outputs=list(model.inference_zero_shot(row["canonical_text"],row["reference_text"],
                            row["reference_wav"],stream=False,speed=1.0,text_frontend=True))
            if not outputs or any("tts_speech" not in x for x in outputs):raise RuntimeError("Missing TTS output")
            speech=torch.cat([x["tts_speech"].detach().cpu() for x in outputs],dim=1)
            sf.write(str(temp),speech.numpy().T,model.sample_rate,subtype="PCM_16")
            info=meta(temp);os.replace(temp,output)
            row.update(status="SUCCESS",output_sha256=sha(output),sample_rate_hz=info.samplerate,
                       channels=info.channels,duration_s=f"{info.duration:.9f}",exception="",
                       elapsed_s=f"{time.perf_counter()-started:.3f}")
        except Exception as exc:
            temp.unlink(missing_ok=True)
            row.update(status="FAIL",exception=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                       elapsed_s=f"{time.perf_counter()-started:.3f}")
        save(rows)
        if i%10==0 or row["status"]=="FAIL":print(f"COSYVOICE2 {i}/160 {row['status']}",flush=True)
    counts={v:sum(r["status"]==v for r in rows) for v in ("SUCCESS","FAIL","PENDING")}
    summary={"status":"COMPLETE" if counts["PENDING"]==0 else "PARTIAL","counts":counts,
             "rows":len(rows),"execution_manifest_sha256":sha(EXECUTION),"runtime_lock_sha256":sha(ROOT/"research/10_multimodel_runtime/cosyvoice2_runtime_lock.json")}
    (HERE/"generation_execution/cosyvoice2_preservation_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
