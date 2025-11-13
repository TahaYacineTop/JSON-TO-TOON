# toon.py
# TOON: Tokenized Object-Oriented Notation
# Simple, lossless encoder/decoder for JSON-like Python objects.
# No external dependencies.

import struct
import base64
from io import BytesIO

# Type tags
T_NULL = 0
T_BOOL = 1
T_INT = 2
T_FLOAT = 3
T_STRING = 4
T_ARRAY = 5
T_OBJECT = 6

VERSION = 1

# varint encode/decode
def write_varint(n: int):
    parts = []
    while True:
        towrite = n & 0x7F
        n >>= 7
        if n:
            parts.append(towrite | 0x80)
        else:
            parts.append(towrite)
            break
    return bytes(parts)

def read_varint(stream: BytesIO):
    shift = 0
    result = 0
    while True:
        b = stream.read(1)
        if not b:
            raise EOFError("EOF while reading varint")
        i = b[0]
        result |= ((i & 0x7F) << shift)
        if not (i & 0x80):
            break
        shift += 7
    return result

# Vocabulary builder
def build_vocab(obj, max_vocab=256):
    from collections import Counter, deque
    c = Counter()
    dq = deque([obj])
    while dq:
        x = dq.popleft()
        if isinstance(x, dict):
            for k, v in x.items():
                c[k] += 3
                dq.append(v)
        elif isinstance(x, list):
            for item in x:
                dq.append(item)
        elif isinstance(x, str):
            if len(x) <= 64:
                c[x] += 1
    vocab = [s for s, _ in c.most_common(max_vocab)]
    return vocab

# Encoder
def encode_value(obj, vocab_map, out: BytesIO):
    if obj is None:
        out.write(bytes([T_NULL])); return
    if isinstance(obj, bool):
        out.write(bytes([T_BOOL])); out.write(b'\x01' if obj else b'\x00'); return
    if isinstance(obj, int) and -(1<<53) < obj < (1<<53):
        out.write(bytes([T_INT])); out.write(write_varint((obj << 1) ^ (obj >> 63))); return
    if isinstance(obj, float):
        out.write(bytes([T_FLOAT])); out.write(struct.pack("<d", float(obj))); return
    if isinstance(obj, str):
        out.write(bytes([T_STRING]))
        if obj in vocab_map:
            out.write(b'\x01'); out.write(write_varint(vocab_map[obj]))
        else:
            out.write(b'\x00'); raw = obj.encode('utf-8'); out.write(write_varint(len(raw))); out.write(raw)
        return
    if isinstance(obj, list):
        out.write(bytes([T_ARRAY])); out.write(write_varint(len(obj)))
        for item in obj: encode_value(item, vocab_map, out)
        return
    if isinstance(obj, dict):
        out.write(bytes([T_OBJECT])); out.write(write_varint(len(obj)))
        for key in sorted(obj.keys()):
            if key in vocab_map:
                out.write(b'\x01'); out.write(write_varint(vocab_map[key]))
            else:
                out.write(b'\x00'); rawk = key.encode('utf-8'); out.write(write_varint(len(rawk))); out.write(rawk)
            encode_value(obj[key], vocab_map, out)
        return
    # fallback
    out.write(bytes([T_STRING])); raw = str(obj).encode('utf-8'); out.write(b'\x00'); out.write(write_varint(len(raw))); out.write(raw)

def encode_toon(pyobj, vocab=None):
    if vocab is None:
        vocab = build_vocab(pyobj, max_vocab=256)
    vocab_map = {s: idx for idx, s in enumerate(vocab)}
    out = BytesIO()
    out.write(bytes([VERSION]))
    out.write(write_varint(len(vocab)))
    for s in vocab:
        raw = s.encode('utf-8'); out.write(write_varint(len(raw))); out.write(raw)
    encode_value(pyobj, vocab_map, out)
    return out.getvalue()

# Decoder
def decode_value(stream: BytesIO, vocab):
    t = stream.read(1)
    if not t: raise EOFError("Unexpected EOF decoding value")
    t = t[0]
    if t == T_NULL: return None
    if t == T_BOOL: return bool(stream.read(1)[0])
    if t == T_INT:
        n = read_varint(stream); val = (n >> 1) ^ (-(n & 1)); return val
    if t == T_FLOAT:
        raw = stream.read(8); return struct.unpack("<d", raw)[0]
    if t == T_STRING:
        flag = stream.read(1)[0]
        if flag == 1:
            idx = read_varint(stream); return vocab[idx]
        else:
            ln = read_varint(stream); raw = stream.read(ln); return raw.decode('utf-8')
    if t == T_ARRAY:
        ln = read_varint(stream); return [decode_value(stream, vocab) for _ in range(ln)]
    if t == T_OBJECT:
        ln = read_varint(stream); obj = {}
        for _ in range(ln):
            key_flag = stream.read(1)[0]
            if key_flag == 1:
                idx = read_varint(stream); key = vocab[idx]
            else:
                kln = read_varint(stream); key = stream.read(kln).decode('utf-8')
            obj[key] = decode_value(stream, vocab)
        return obj
    return None

def decode_toon(byts: bytes):
    stream = BytesIO(byts)
    ver = stream.read(1)[0]
    if ver != VERSION: raise ValueError(f"Unsupported TOON version: {ver}")
    vcount = read_varint(stream)
    vocab = []
    for _ in range(vcount):
        ln = read_varint(stream); raw = stream.read(ln); vocab.append(raw.decode('utf-8'))
    return decode_value(stream, vocab)

def to_base64(byts: bytes):
    return base64.b64encode(byts).decode('ascii')
