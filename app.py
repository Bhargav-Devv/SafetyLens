"""
SafetyLens - the interface specified in DESIGN.md Part 2.

    pip install -r requirements-ui.txt
    streamlit run app.py

Built to that specification, with one deliberate deviation recorded below.

The five required states all exist: loading, empty, refusal, error, result.
**Refusal is not an error state** - it gets its own styling, no error icon, and
no apologetic language, because declining to classify is a correct outcome and
the interface should not look like something went wrong.

DEVIATION FROM THE SPEC. DESIGN.md Part 2 says the regulation card carries a
match score. ADR-019 established that the ranking score is a lexical/latent
blend carrying a 1.5x-3.4x routing multiplier - comparable within one result,
meaningless across incidents, and not a measure of fit. Showing it as "match
0.30" would be exactly the kind of number that looks authoritative and is not.
The card shows RANK instead, plus the calibrated lexical score, matching what
`src/agent.py` says in words.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
from src.service import get_service

# DESIGN.md Part 2 palette
INK, SURFACE, RAISED = "#1C2127", "#FFFFFF", "#F4F5F7"
ACCENT, BORDER, MUTED = "#E8A33D", "#DDE1E6", "#6B7682"
CONFIRMED, CAUTION = "#3E9D6E", "#C25A3A"

EXAMPLE = ("Employee was cleaning a conveyor belt while it was running when his "
           "sleeve became caught in the rollers and his right arm was pulled in, "
           "resulting in an amputation below the elbow.")

st.set_page_config(page_title="SafetyLens", page_icon="■", layout="centered")

st.markdown(f"""<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap');
  html, body, [class*="css"] {{ font-family: Inter, system-ui, sans-serif; color: {INK}; }}
  .stApp {{ background: {SURFACE}; }}
  .sl-title {{ font-size: 32px; font-weight: 700; letter-spacing: -0.02em; margin: 0; }}
  .sl-sub {{ font-size: 15px; color: {MUTED}; margin: 4px 0 28px; }}
  .sl-h {{ font-size: 20px; font-weight: 600; margin: 28px 0 12px; }}
  .sl-card {{ background: {RAISED}; border: 1px solid {BORDER}; border-radius: 8px;
             padding: 18px 20px; margin-bottom: 14px; }}
  /* No shadow on a regulation card - a quote should read as a document, not a widget. */
  .sl-reg {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
             padding: 18px 20px; margin-bottom: 14px; box-shadow: none; }}
  .sl-refusal {{ background: {SURFACE}; border: 1px solid {ACCENT}; border-left: 4px solid {ACCENT};
                 border-radius: 8px; padding: 18px 20px; }}
  .sl-gap {{ background: {SURFACE}; border: 1px solid {BORDER}; border-left: 4px solid {CONFIRMED};
             border-radius: 8px; padding: 18px 20px; }}
  .sl-mono {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px;
              font-weight: 500; }}
  .sl-cap {{ font-size: 12px; color: {MUTED}; }}
  .sl-quote {{ font-size: 15px; line-height: 1.6; border-left: 2px solid {BORDER};
               padding-left: 14px; margin: 12px 0; }}
  .sl-bar-t {{ height: 8px; background: {BORDER}; border-radius: 4px; overflow: hidden; }}
  .sl-bar-f {{ height: 8px; border-radius: 4px; }}
</style>""", unsafe_allow_html=True)

st.markdown('<p class="sl-title">SafetyLens</p>', unsafe_allow_html=True)
st.markdown('<p class="sl-sub">Describe a workplace incident. Get the hazard category, the OSHA '
            'section that applies quoted in full, and whether it has happened before.</p>',
            unsafe_allow_html=True)


def margin_bar(label: str, value: str, margin: float) -> None:
    """A margin, as a labelled bar AND as its number.

    WCAG 2.2 AA: status is never carried by colour or length alone. The number
    is always present, to three decimals, and never converted to a percentage -
    it is a margin, not a probability (DESIGN.md Part 1).
    """
    pct = max(0.0, min(margin / 4.0, 1.0)) * 100
    colour = CONFIRMED if margin >= cfg.MARGIN_FLOOR else CAUTION
    st.markdown(
        f'<div class="sl-card"><div class="sl-cap">{label}</div>'
        f'<div style="font-size:17px;font-weight:600;margin:2px 0 10px">{value}</div>'
        f'<div class="sl-bar-t"><div class="sl-bar-f" style="width:{pct:.1f}%;'
        f'background:{colour}"></div></div>'
        f'<div class="sl-mono" style="color:{MUTED};margin-top:6px">'
        f'margin {margin:.3f} &nbsp;&middot;&nbsp; floor {cfg.MARGIN_FLOOR:.2f}</div></div>',
        unsafe_allow_html=True)


narrative = st.text_area(
    "Incident narrative", height=130, placeholder=EXAMPLE,
    help="What was the person doing, what equipment was involved, which part of the body.")
go = st.button("Analyse", type="primary")

if not go and not narrative:
    # EMPTY STATE
    st.markdown(f'<div class="sl-card"><div class="sl-cap">No incident yet</div>'
                f'<div style="margin-top:6px">Paste a narrative above, or try the example '
                f'in the placeholder.</div></div>', unsafe_allow_html=True)
    st.stop()

if go and not narrative.strip():
    # ERROR STATE - genuinely an error, unlike a refusal
    st.error("Enter a narrative before analysing.")
    st.stop()

if go:
    try:
        # LOADING STATE
        with st.spinner("Loading models and the regulation corpus… first run takes about a minute."):
            svc = get_service()
        result = svc.analyse_incident(narrative)
    except Exception as exc:                      # ERROR STATE
        st.error(f"The system could not run: {exc}")
        st.caption("If the models are missing, run `python main.py train` first.")
        st.stop()

    status = result["status"]

    if status == "insufficient_input":
        st.markdown(f'<div class="sl-refusal"><div class="sl-cap">NOT CLASSIFIED</div>'
                    f'<div style="font-size:17px;font-weight:600;margin:4px 0 8px">'
                    f'Too short to analyse</div><div>{result["message"]}</div></div>',
                    unsafe_allow_html=True)
        st.stop()

    if status == "abstained":
        # REFUSAL STATE. Not an error: no error styling, no icon, no apology.
        asks = "".join(f"<li>{a}</li>" for a in result["ask_for"])
        st.markdown(
            f'<div class="sl-refusal"><div class="sl-cap">NOT CLASSIFIED</div>'
            f'<div style="font-size:17px;font-weight:600;margin:4px 0 8px">'
            f'The hazard cannot be identified reliably from this</div>'
            f'<div class="sl-mono" style="color:{MUTED}">margin {result["margin"]:.3f} '
            f'&nbsp;&middot;&nbsp; below the {result["margin_floor"]:.2f} floor</div>'
            f'<div style="margin-top:12px">Add:</div><ul>{asks}</ul>'
            f'<div class="sl-cap">A confident wrong answer about a safety hazard is the '
            f'thing worth avoiding. This is a correct outcome, not a failure.</div></div>',
            unsafe_allow_html=True)
        st.stop()

    # RESULT STATE
    st.markdown('<p class="sl-h">Hazard</p>', unsafe_allow_html=True)
    margin_bar("GROUP", result["hazard_group"], result["hazard_group_margin"])
    margin_bar("SPECIFIC EVENT", result["specific_event"], result["specific_event_margin"])

    st.markdown('<p class="sl-h">Applicable standard</p>', unsafe_allow_html=True)
    ss = result["standards_status"]

    if ss == "no_specific_standard":
        st.markdown(
            f'<div class="sl-gap"><div class="sl-cap">NO STANDARD EXISTS</div>'
            f'<div style="font-size:17px;font-weight:600;margin:4px 0 8px">'
            f'{result["authority"]}</div><div>{result["standards_message"]}</div>'
            f'<div class="sl-cap" style="margin-top:10px">This is the system reporting that no '
            f'section exists — not failing to find one.</div></div>',
            unsafe_allow_html=True)
    elif ss in ("no_match", "not_attempted"):
        st.markdown(f'<div class="sl-card"><div class="sl-cap">NONE RETURNED</div>'
                    f'<div style="margin-top:6px">{result.get("standards_message") or ""}</div>'
                    f'</div>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="sl-cap">Quoted from eCFR, not generated.</p>',
                    unsafe_allow_html=True)
        for rank, s in enumerate(result["standards"], 1):
            lead = "Closest match" if rank == 1 else f"Ranked {rank}"
            st.markdown(
                f'<div class="sl-reg"><div class="sl-cap">{lead} of '
                f'{len(result["standards"])}</div>'
                f'<div class="sl-mono" style="font-size:15px;margin:4px 0 2px">'
                f'{s["citation"]}</div>'
                f'<div style="font-weight:600;margin-bottom:6px">{s["title"]}</div>'
                f'<div class="sl-quote">"{s["quote"]}"</div>'
                f'<div class="sl-mono" style="color:{MUTED}">lexical score '
                f'{s["lexical_score"]:.3f}</div>'
                f'<div class="sl-cap" style="margin-top:6px">{s["source"]}</div></div>',
                unsafe_allow_html=True)
            with st.expander(f"Full text of {s['citation']}"):
                full = svc.explain_standard(s["section"])
                if full["status"] == "found":
                    st.caption(f"{full['characters']:,} characters · {full['source']}")
                    st.text(full["text"])
                else:
                    st.write(full["message"])
        st.caption("Ranking is relative within this result. It is not a measure of how well a "
                   "section fits, and it is not comparable to another incident's scores.")

    if result.get("similar_incidents"):
        st.markdown('<p class="sl-h">This has happened before</p>', unsafe_allow_html=True)
        for s in result["similar_incidents"]:
            st.markdown(
                f'<div class="sl-card"><div>{s["text"]}</div>'
                f'<div class="sl-mono" style="color:{MUTED};margin-top:8px">'
                f'{s["hazard_group"]} &nbsp;&middot;&nbsp; similarity {s["similarity"]:.3f}'
                f'</div></div>', unsafe_allow_html=True)

    st.caption("Decision support only. What a standard requires is not a finding that anyone "
               "violated it. Not a compliance determination and not a legal opinion.")
