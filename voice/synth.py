"""voice/requests/<名前>.json を読み、まだ音声の無いものを VOICEVOX で作って voice/output/<名前>/ に置く。
JSON の形: {"items": [{"name": "01", "speaker": 14, "text": "...", "speed": 1.0, "pitch": 0.0, "intonation": 1.0,
                        "pause": 1.0, "sentence_gap": 0.0}]}
- pause: 「、」「。」の間の長さの倍率（VOICEVOX の pauseLengthScale）
- sentence_gap: 0 より大きいと、文（「。」「？」「！」で区切る）ごとに作り、文と文の間にこの秒数の無音を入れる
"""
import io, json, pathlib, re, subprocess, urllib.parse, urllib.request, wave

ENGINE = "http://127.0.0.1:50021"
root = pathlib.Path(__file__).parent

def post(path, params, body=None):
    url = f"{ENGINE}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()

def synth(text, item):
    q = json.loads(post("/audio_query", {"text": text, "speaker": item["speaker"]}))
    q["speedScale"] = item.get("speed", 1.0)
    q["pitchScale"] = item.get("pitch", 0.0)
    q["intonationScale"] = item.get("intonation", 1.0)
    if "pauseLengthScale" in q:
        q["pauseLengthScale"] = item.get("pause", 1.0)
    elif item.get("pause", 1.0) != 1.0:
        print("warning: this engine has no pauseLengthScale")
    return post("/synthesis", {"speaker": item["speaker"]}, q)

def join_wavs(chunks, gap, path):
    frames, params = [], None
    for c in chunks:
        with wave.open(io.BytesIO(c)) as w:
            params = w.getparams()
            frames.append(w.readframes(w.getnframes()))
    silence = b"\x00" * (int(params.framerate * gap) * params.sampwidth * params.nchannels)
    with wave.open(str(path), "wb") as out:
        out.setparams(params)
        out.writeframes(silence.join(frames))

available = {st["id"] for sp in json.loads(urllib.request.urlopen(f"{ENGINE}/speakers").read()) for st in sp["styles"]}
for req_file in sorted((root / "requests").glob("*.json")):
    out_dir = root / "output" / req_file.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in json.loads(req_file.read_text(encoding="utf-8"))["items"]:
        mp3 = out_dir / f"{item['name']}.mp3"
        if mp3.exists():
            continue
        if item["speaker"] not in available:
            print(f"skip {item['name']}: speaker {item['speaker']} is not in this engine")
            continue
        gap = item.get("sentence_gap", 0.0)
        parts = [t for t in re.split(r"(?<=[。？！])", item["text"]) if t.strip()] if gap > 0 else [item["text"]]
        chunks = [synth(t, item) for t in parts]
        wav = out_dir / f"{item['name']}.wav"
        join_wavs(chunks, gap, wav)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "128k", str(mp3)], check=True)
        wav.unlink()
        print(f"made {mp3}")
