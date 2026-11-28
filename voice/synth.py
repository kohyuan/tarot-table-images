"""voice/requests/<名前>.json を読み、まだ音声の無いものを VOICEVOX で作って voice/output/<名前>/ に置く。
JSON の形: {"items": [{"name": "01", "speaker": 14, "text": "...", "speed": 1.0, "pitch": 0.0, "intonation": 1.0}]}
"""
import json, pathlib, subprocess, urllib.parse, urllib.request

ENGINE = "http://127.0.0.1:50021"
root = pathlib.Path(__file__).parent

def post(path, params, body=None):
    url = f"{ENGINE}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()

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
        q = json.loads(post("/audio_query", {"text": item["text"], "speaker": item["speaker"]}))
        q["speedScale"] = item.get("speed", 1.0)
        q["pitchScale"] = item.get("pitch", 0.0)
        q["intonationScale"] = item.get("intonation", 1.0)
        wav = out_dir / f"{item['name']}.wav"
        wav.write_bytes(post("/synthesis", {"speaker": item["speaker"]}, q))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "128k", str(mp3)], check=True)
        wav.unlink()
        print(f"made {mp3}")
