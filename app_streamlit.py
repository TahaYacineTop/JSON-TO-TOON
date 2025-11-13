# app_streamlit.py
# Streamlit UI for JSON -> TOON converter (dark UI)
import streamlit as st
import json, base64, zlib, time
from toon import encode_toon, decode_toon, to_base64

st.set_page_config(page_title="JSON → TOON Converter", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background-color: #0b0f14; color: #e6eef6; }
    .big-box { background: #0f1720; padding: 18px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.03); }
    .panel-title { font-weight:700; color: #dbeafe; margin-bottom:6px; }
    .muted { color: #9fb0c9; }
    .stat { background:#071124; padding:12px; border-radius:8px; text-align:center; }
    </style>
    """, unsafe_allow_html=True
)

st.title("JSON → TOON Converter — Convert JSON to compact TOON")
col_left, col_right = st.columns([1,1])

EXAMPLE = {
    "items": [
        {"id": 1, "name": "Alice Johnson", "age": 30, "city": "New York", "role": "Developer"},
        {"id": 2, "name": "Bob Smith", "age": 25, "city": "San Francisco", "role": "Designer"},
        {"id": 3, "name": "Charlie Brown", "age": 35, "city": "Chicago", "role": "Manager"}
    ]
}

with st.sidebar:
    st.markdown("### Options")
    delimiter_opt = st.selectbox("Delimiter", (",", "|", "\t"), index=0, format_func=lambda x: {"\t":"Tab","|":"Pipe",",":"Comma (,)"}[x])
    indentation = st.selectbox("Indentation", (0,2,4), index=1)
    show_lengths = st.checkbox("Show length markers (#)", value=True)
    est_token_mode = st.radio("Token estimate mode", ("Conservative (chars/4)", "Chars/4 exact"), index=0)

with col_left:
    st.markdown('<div class="big-box"><div class="panel-title">JSON Input</div>', unsafe_allow_html=True)
    json_text = st.text_area("Paste JSON here", height=360, value=json.dumps(EXAMPLE, indent=2) , key="json_input")
    c1, c2 = st.columns([1,1])
    if c1.button("Load Example"):
        json_text = json.dumps(EXAMPLE, indent=2)
        st.experimental_rerun()
    if c2.button("Clear All"):
        json_text = ""
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="big-box"><div class="panel-title">TOON Output</div>', unsafe_allow_html=True)
    parsed = None
    parse_error = None
    try:
        parsed = json.loads(json_text) if json_text.strip() else None
    except Exception as e:
        parse_error = str(e)

    if parse_error:
        st.error(f"JSON parse error: {parse_error}")
        toon_display = ""
        toon_bytes = b""
    elif parsed is None:
        st.info("No JSON provided. Load example or paste your JSON.")
        toon_display = ""
        toon_bytes = b""
    else:
        t0 = time.time()
        toon_bytes = encode_toon(parsed)
        t1 = time.time()
        toon_b64 = base64.b64encode(toon_bytes).decode('ascii')
        toon_display = ""
        list_of_dicts = None
        if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
            list_of_dicts = parsed
        elif isinstance(parsed, dict):
            for k in ("items","data","rows","results"):
                if k in parsed and isinstance(parsed[k], list) and all(isinstance(x, dict) for x in parsed[k]):
                    list_of_dicts = parsed[k]; break

        if list_of_dicts is not None:
            keys = []
            for d in list_of_dicts:
                for k in d.keys():
                    if k not in keys: keys.append(k)
            lines = []
            lines.append("items[" + str(len(list_of_dicts)) + "]|" + delimiter_opt.join(keys))
            for row in list_of_dicts:
                vals = []
                for k in keys:
                    v = row.get(k, "")
                    if isinstance(v, str):
                        vals.append(f"{v}#{len(v)}" if show_lengths else v)
                    else:
                        vals.append(str(v))
                lines.append(delimiter_opt.join(vals))
            toon_display = "\n".join(lines)
        else:
            toon_display = toon_b64[:1000] + ("..." if len(toon_b64)>1000 else "")

        encode_time = t1 - t0
        raw_json_bytes = json_text.encode("utf-8")
        raw_size = len(raw_json_bytes)
        toon_size = len(toon_bytes)
        gz_raw = zlib.compress(raw_json_bytes)
        gz_toon = zlib.compress(toon_bytes)

        def estimate_tokens_from_bytes(n):
            return max(1, n // 4)
        if est_token_mode.startswith("Conservative"):
            json_tokens_est = estimate_tokens_from_bytes(len(raw_json_bytes))
            toon_tokens_est = estimate_tokens_from_bytes(len(toon_bytes))
        else:
            json_tokens_est = max(1, len(raw_json_bytes)//4)
            toon_tokens_est = max(1, len(toon_bytes)//4)

        saved_pct = 100.0 * (1 - (toon_size / max(1, raw_size)))

        output_area = st.empty()
        output_area.text_area("TOON Output", value=toon_display, height=360, key="toon_output")
        c1, c2, c3 = st.columns([1,1,1])
        if c1.button("Copy"):
            st.clipboard_set(toon_display); st.success("Copied TOON output to clipboard.")
        if c2.download_button("Download .toon (base64)", data=toon_b64.encode('utf-8'), file_name="sample.toon.b64", mime="application/text"):
            pass
        if c3.button("Download binary (.toon)"):
            st.download_button(label="Download Binary", data=toon_bytes, file_name="sample.toon", mime="application/octet-stream")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:12px; display:flex; gap:12px;'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,1])
        c1.markdown(f"<div class='stat'><div style='font-size:20px; font-weight:700'>{json_tokens_est}</div><div class='muted'>JSON tokens (est)</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat'><div style='font-size:20px; font-weight:700'>{toon_tokens_est}</div><div class='muted'>TOON tokens (est)</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat'><div style='font-size:20px; font-weight:700'>{saved_pct:.0f}%</div><div class='muted'>Saved</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Technical details (estimates & timings)"):
            st.write(f"Raw JSON bytes: {raw_size}")
            st.write(f"TOON bytes: {toon_size}")
            st.write(f"GZIP JSON bytes: {len(gz_raw)}")
            st.write(f"GZIP TOON bytes: {len(gz_toon)}")
            st.write(f"Encode time: {encode_time:.4f}s")
            st.write("Token estimate method: chars/4 (approx.). For accurate counts, use model tokenizer (tiktoken / model-specific tokenizer).")

st.markdown("---")
st.markdown("Prototype built for portfolio. Do not store sensitive data without consent.")
