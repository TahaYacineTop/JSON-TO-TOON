# demo_toon.py
import json, time, zlib
from toon import encode_toon, decode_toon, to_base64

SAMPLE = {
    "name": "Taha Yacine",
    "role": "AI Researcher",
    "education": {"school": "Harbin Institute of Technology Shenzhen", "track": "Mathematical Sciences B"},
    "skills": ["python", "linear algebra", "probability", "ml"],
    "projects": [
        {"title": "Futracode", "role": "Founder"},
        {"title": "Space Apps", "role": "Team Lead"}
    ],
    "metrics": {"gpa_scaled": 18.6, "sat": None, "duolingo": 135},
    "bio": "Student-driven, focused on AI research, ethics, and systems building."
}

def size_bytes(x):
    return len(x)

def gzip_bytes(x: bytes):
    return zlib.compress(x)

def run_demo(sample=SAMPLE):
    raw_json = json.dumps(sample, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    print("Raw JSON bytes:", size_bytes(raw_json))
    start = time.time()
    toon_bytes = encode_toon(sample)
    t_encode = time.time() - start
    print("TOON bytes:", size_bytes(toon_bytes), "(encode time: %.3fs)" % t_encode)
    gz_raw = gzip_bytes(raw_json)
    gz_toon = gzip_bytes(toon_bytes)
    print("GZIP JSON bytes:", size_bytes(gz_raw))
    print("GZIP TOON bytes:", size_bytes(gz_toon))
    print("TOON base64 (first 200 chars):")
    print(to_base64(toon_bytes)[:200])
    decoded = decode_toon(toon_bytes)
    assert decoded == sample, "Decoded object mismatch!"
    print("Decode check: OK")
    factor_raw = size_bytes(raw_json) / max(1, size_bytes(toon_bytes))
    factor_gzip = size_bytes(gz_raw) / max(1, size_bytes(gz_toon))
    print(f"Size ratio (raw_json / toon): {factor_raw:.2f}")
    print(f"GZIP size ratio (json / toon): {factor_gzip:.2f}")

if __name__ == "__main__":
    run_demo()
