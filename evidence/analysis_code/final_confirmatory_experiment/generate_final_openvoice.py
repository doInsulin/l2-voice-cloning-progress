"""Frozen 160-row OpenVoice V2 + MeloTTS preservation generation."""
from __future__ import annotations
import csv,hashlib,json,os,random,sys,time,traceback
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUNTIME=ROOT/"research/10_multimodel_runtime"
sys.path[:0]=[str(RUNTIME),str(ROOT/".model_cache/src/OpenVoice"),str(ROOT/".model_cache/src/MeloTTS")]
os.environ.update({"HF_HOME":str(ROOT/".model_cache/hf_openvoice"),
                   "HUGGINGFACE_HUB_CACHE":str(ROOT/".model_cache/hf_openvoice/hub"),
                   "TRANSFORMERS_CACHE":str(ROOT/".model_cache/hf_openvoice/hub"),
                   "HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1",
                   "NLTK_DATA":str(ROOT/".model_cache/nltk_data")})
from melo_english_lazy_import_adapter import install_english_only_import_adapter
from runtime_storage import configure
configure("openvoice_v2");install_english_only_import_adapter()
from melo.api import TTS
from openvoice_runtime_compat import FrozenToneColorConverter as ToneColorConverter

OV=ROOT/".model_cache/openvoice_v2/f36e7edfe1684461a8343844af60babc2efbb727"
MELO=ROOT/".model_cache/melo_english_v3/f7c4a35392c0e9be24a755f1edb4c3f63040f759"
FROZEN=HERE/"generation_manifests/openvoice_v2_preservation.csv"
EXECUTION=HERE/"generation_execution/openvoice_v2_preservation.csv"
TMP=ROOT/".tmp/final_openvoice_v2_generation"
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
    if info.samplerate!=22050 or info.channels!=1 or info.frames<=0:raise RuntimeError("native WAV invalid")
    return info


def main():
    freeze=json.loads((HERE/"generation_design_freeze.json").read_text(encoding="utf-8"))
    if sha(FROZEN)!=freeze["manifests"][FROZEN.name]["sha256"]:raise RuntimeError("Frozen manifest drift")
    expected=read(FROZEN);rows=read(EXECUTION) if EXECUTION.exists() else expected
    if len(rows)!=160 or any(tuple(r[k] for k in IDENTITY)!=tuple(e[k] for k in IDENTITY)
                            for r,e in zip(rows,expected)):raise RuntimeError("Execution identity drift")
    if not EXECUTION.exists():save(rows)
    runtime=json.loads((RUNTIME/"openvoice_v2_runtime_lock.json").read_text(encoding="utf-8"))
    if runtime["status"]!="RUNTIME_LOCK_PASS" or not torch.cuda.is_available():raise RuntimeError("Pinned runtime unavailable")
    report_path=RUNTIME/"pinned_weight_download_report.json"
    if sha(report_path)!=runtime["official_weight_report_sha256"]:raise RuntimeError("Pinned weight report drift")
    report=json.loads(report_path.read_text(encoding="utf-8"))
    for item in report["files"]:
        if item["model"]=="openvoice_v2" and item["pinned_weight"] and sha(Path(item["local_path"]))!=item["sha256"]:
            raise RuntimeError(f"Pinned OpenVoice V2 weight drift: {item['file']}")
    bert=runtime["bert_weight_report"]
    for item in bert["files"]:
        if sha(Path(bert["local_path"])/item["file"])!=item["sha256"]:
            raise RuntimeError(f"Pinned BERT weight drift: {item['file']}")
    TMP.mkdir(parents=True,exist_ok=True)
    tts=TTS(language="EN",device="cuda:0",use_hf=False,
            config_path=str(MELO/"config.json"),ckpt_path=str(MELO/"checkpoint.pth"))
    converter=ToneColorConverter(str(OV/"converter/config.json"),device="cuda:0",enable_watermark=False)
    converter.load_ckpt(str(OV/"converter/checkpoint.pth"))
    source_embedding=torch.load(OV/"base_speakers/ses/en-newest.pth",map_location="cuda:0",weights_only=True)
    reference_embeddings={};checked=set()
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
        base=TMP/f"{row['target_id']}.base.wav";temp=output.with_suffix(".tmp.wav")
        base.unlink(missing_ok=True);temp.unlink(missing_ok=True);started=time.perf_counter()
        seed=int(row["seed"]);random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        try:
            ref_id=row["speaker"]
            if ref_id not in reference_embeddings:reference_embeddings[ref_id]=converter.extract_se(row["reference_wav"])
            tts.tts_to_file(row["canonical_text"],0,str(base),sdp_ratio=.2,
                            noise_scale=.6,noise_scale_w=.8,speed=1.0,quiet=True)
            converter.convert(str(base),source_embedding,reference_embeddings[ref_id],output_path=str(temp),tau=.3)
            info=meta(temp);os.replace(temp,output)
            row.update(status="SUCCESS",output_sha256=sha(output),sample_rate_hz=info.samplerate,
                       channels=info.channels,duration_s=f"{info.duration:.9f}",exception="",
                       elapsed_s=f"{time.perf_counter()-started:.3f}")
        except Exception as exc:
            temp.unlink(missing_ok=True)
            row.update(status="FAIL",exception=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                       elapsed_s=f"{time.perf_counter()-started:.3f}")
        finally:base.unlink(missing_ok=True)
        save(rows)
        if i%10==0 or row["status"]=="FAIL":print(f"OPENVOICE_V2 {i}/160 {row['status']}",flush=True)
    counts={v:sum(r["status"]==v for r in rows) for v in ("SUCCESS","FAIL","PENDING")}
    summary={"status":"COMPLETE" if counts["PENDING"]==0 else "PARTIAL","counts":counts,
             "rows":len(rows),"execution_manifest_sha256":sha(EXECUTION),"runtime_lock_sha256":sha(RUNTIME/"openvoice_v2_runtime_lock.json")}
    (HERE/"generation_execution/openvoice_v2_preservation_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
