"""Render the editable supervisor diagram with the installed rsvg-convert CLI."""

from html import escape
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
INK, MUTED = "#173342", "#526977"
GREEN, AMBER, GRAY, BLUE = "#087F6F", "#AC5A10", "#61768A", "#385E8B"
COLORS = {"DONE": (GREEN, "#EAF6F1"), "PARTIAL": (AMBER, "#FFF3E4"),
          "NOT BUILT": (GRAY, "#F0F4F8"), "OPEN": (BLUE, "#EFF5FC")}
parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="2800" height="2000" viewBox="0 0 2800 2000">',
         '<title>RAG Workflow Lab - detailed pipeline and implementation status</title>',
         '<desc>Source preparation, current and planned RAG paths, output validation, tracing, and six retrieval metrics. Updated 25 November 2026.</desc>',
         '<defs><marker id="green" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#087F6F"/></marker>',
         '<marker id="gray" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#61768A"/></marker></defs>',
         '<rect width="2800" height="2000" fill="#FCFDFE"/>']


def rect(x, y, w, h, fill="white", stroke="#CEDAE2", radius=16):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')


def text(x, y, value, size=22, color=INK, bold=False):
    weight = 700 if bold else 400
    parts.append(f'<text x="{x}" y="{y}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(value)}</text>')


def lines(x, y, values, size=21, color=MUTED, step=26):
    for i, value in enumerate(values):
        text(x, y + step * i, value, size, color)


def badge(x, y, label):
    color, _ = COLORS[label]
    width = len(label) * 10 + 24
    rect(x, y, width, 30, color, color, 7)
    text(x + 12, y + 21, label, 17, "white", True)
    return width


def panel(x, y, w, h, title, status):
    color, fill = COLORS[status]
    rect(x, y, w, h, fill, color)
    text(x + 22, y + 36, title, 28, INK, True)
    badge(x + w - len(status) * 10 - 46, y + 13, status)


def node(x, y, w, h, title, body, status="DONE", size=20):
    color, fill = COLORS[status]
    rect(x, y, w, h, fill, color, 12)
    text(x + 16, y + 29, title, 23, INK, True)
    lines(x + 16, y + 56, body, size=size, step=24)


def arrow(points, current=False, head=True):
    color = GREEN if current else GRAY
    dash = "" if current else ' stroke-dasharray="9 7"'
    marker = f' marker-end="url(#{"green" if current else "gray"})"' if head else ""
    parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"{dash}{marker}/>')


text(60, 45, "RAG WORKFLOW LAB", 22, GREEN, True)
text(60, 95, "Detailed pipeline and implementation status", 43, INK, True)
text(60, 132, "Supervisor discussion | Updated 25 November 2026 | Basic = Simple in the codebase", 23, MUTED)
for x, status in [(1930, "DONE"), (2070, "PARTIAL"), (2240, "NOT BUILT"), (2450, "OPEN")]:
    badge(x, 38, status)
text(1930, 106, "Solid green: implemented path / component", 20, GREEN)
text(1930, 135, "Dashed: planned connection; tags state build status", 20, MUTED)

text(60, 184, "A. BEFORE QUESTIONS - PREPARE SHARED, VERSIONED EVIDENCE", 28, INK, True)
for x in [700, 1380, 2060]:
    arrow(f"{x},{277} {x + 40},{277}", True)
prep = [
    (60, "01  Select sources", ["8 PostgreSQL 18 docs + 6 synthetic Atlas docs.", "Public documentation and fictional deployment facts."]),
    (740, "02  Snapshot and parse", ["Immutable HTML / Markdown; source IDs and hashes.", "Preserve sections, SQL blocks and tables."]),
    (1420, "03  Chunk and embed", ["Whole-block chunks; target 512 / ceiling 1024 tokens.", "Local Nomic Embed Text v1.5, 768-dimensional vectors."]),
    (2100, "04  Store evidence", ["PostgreSQL + pgvector; shared index: 151 chunks.", "113 PostgreSQL + 38 Atlas; earlier controls retained."]),
]
for x, title, body in prep:
    panel(x, 210, 640, 135, title, "DONE")
    lines(x + 22, 285, body, size=21)

text(60, 400, "B. QUESTION TIME - ONE SELECTED WORKFLOW, THEN ANSWER VALIDATION", 28, INK, True)

# Draw connections first so the cards remain readable at junctions.
arrow("260,740 310,740")
arrow("560,740 585,740 585,475 620,475")
arrow("585,740 585,750 620,750")
arrow("585,750 585,1050 620,1050")
arrow("160,680 160,545 650,545", True)
arrow("2170,545 2220,545 2280,545", True)
arrow("2170,750 2220,750 2220,570 2280,570")
arrow("2170,1050 2245,1050 2245,590 2280,590")
arrow("2510,620 2510,660", True)
arrow("2510,895 2510,950", True)

node(60, 680, 200, 120, "User question", ["Raw English", "question text."], size=21)
rect(310, 630, 250, 265, COLORS["NOT BUILT"][1], GRAY)
badge(332, 644, "NOT BUILT")
text(332, 713, "Workflow router", 26, INK, True)
lines(332, 755, ["Select one RAG path.", "Method OPEN:", "rules / classifier / LLM.", "No gold labels or", "other methods' answers."], size=19)
text(60, 520, "CURRENT: CLI selects Simple directly", 22, GREEN, True)
node(60, 965, 500, 175, "Research question - working draft", [
    "Compare fixed vs dynamic control with equal tools.",
    "Measure answer quality, cost and latency.",
    "Later: can routing choose a cheaper adequate path?",
    "Final protocol and held-out set: OPEN."], "OPEN", size=19)

panel(620, 435, 1550, 170, "Basic / Simple RAG", "DONE")
arrow("1070,545 1110,545", True)
arrow("1440,545 1480,545", True)
node(650, 500, 420, 80, "Dense retrieval", ["DONE | question embedding + cosine search"], size=19)
node(1110, 500, 330, 80, "Select top 5 chunks", ["DONE | whole chunks, source IDs"], size=19)
node(1480, 500, 650, 80, "Build cited answer context", ["DONE | one retrieval pass; no reranking or sandbox tools"], size=19)

panel(620, 630, 1550, 245, "Enhanced RAG - components exist; workflow composition not built", "PARTIAL")
arrow("895,730 915,730 915,775 935,775", True)
arrow("895,811 935,811 935,795", True)
arrow("1165,775 1205,775", True)
arrow("1420,775 1460,775", True)
arrow("1810,775 1850,775")
node(650, 695, 245, 70, "Dense top-20", ["DONE | Nomic + cosine"], size=18)
node(650, 780, 245, 70, "Lexical top-20", ["DONE | English full-text"], size=18)
node(935, 715, 230, 126, "RRF [DONE]", ["k=60; equal weights", "Merge + chunk-ID dedup", "At most 40 unique hits"], size=18)
node(1205, 715, 215, 126, "Keep 20 [DONE]", ["From RRF ranking", "Fixed probe candidates", "No gold-based selection"], size=17)
node(1460, 695, 350, 150, "Qwen3 reranker", ["PARTIAL | local probes done", "4B / 0.6B relevance scoring", "Final model / batch: OPEN", "Live workflow wiring not built"], "PARTIAL", size=19)
node(1850, 715, 290, 126, "Answer context [OPEN]", ["Initial target: top 5", "Compare cutoffs 5 / 10 / 20", "Final token budget: OPEN"], "OPEN", size=19)

rect(620, 890, 1550, 62, "#F0F4F8", GRAY, 12)
text(642, 916, "SHARED SANDBOX TOOLS [NOT BUILT]: allowed DB inspection and EXPLAIN for permitted query IDs", 21, INK, True)
text(642, 942, "Enhanced: fixed Python conditions/order | Agentic: model chooses actions | Same relevant tools; fixtures/contracts OPEN", 20, MUTED)
arrow("1995,890 1995,841")
arrow("1255,952 1255,1018")

panel(620, 970, 1550, 185, "Agentic RAG - dynamic tool control", "NOT BUILT")
arrow("1000,1058 1040,1058")
arrow("1470,1058 1510,1058")
arrow("1820,1058 1860,1058")
node(650, 1018, 350, 80, "LLM chooses an action", ["NOT BUILT | LangGraph selected"], "NOT BUILT", size=19)
node(1040, 1018, 430, 80, "Retrieval + shared DB tools", ["NOT BUILT | exact retrieval policy OPEN"], "NOT BUILT", size=19)
node(1510, 1018, 310, 80, "Observe tool results", ["NOT BUILT | graph / state"], "NOT BUILT", size=19)
node(1860, 1018, 280, 80, "Finish or repeat", ["OPEN | stop / retry limits"], "OPEN", size=19)
arrow("1995,1098 1995,1130 825,1130 825,1098")
text(1050, 1125, "Repeat only if more evidence is needed; bounds not yet defined", 18, MUTED)

panel(2280, 435, 460, 185, "Answer generation", "PARTIAL")
lines(2302, 510, ["DONE in Simple: Luna + answer_v1.", "Same generator/settings across RAG arms.", "Context is evidence; citations requested.", "Enhanced/Agentic integration: NOT BUILT."], size=20)
panel(2280, 660, 460, 235, "Output validation", "PARTIAL")
lines(2302, 735, ["DONE in Simple: completed + nonempty.", "PLANNED: valid citation labels.", "OPEN: claims supported by evidence?", "OPEN: failure / retry / repair policy.", "Extra LLM verification: undecided.", "Shared validator stage: NOT BUILT."], size=20)
node(2280, 950, 460, 110, "Response", ["Cited answer or insufficient evidence.", "Current working path: Simple."], size=20)
lines(2280, 1100, ["A valid citation label alone does not", "prove that the source supports a claim."], size=19)

panel(60, 1210, 1050, 220, "C. Tracing - execution observability", "PARTIAL")
lines(82, 1285, [
    "Trace = one question/workflow; span = one operation.",
    "DONE: Simple retrieval + LLM; PostgreSQL traces / spans.",
    "Recorded: prompt, chunk ranks/IDs, answer, tokens, timings/errors.",
    "Cost remains NULL when unknown; tool calls are not fabricated.",
    "NOT BUILT: reranker, router, DB-tool and validator spans."], size=21)
panel(1150, 1210, 1590, 220, "Reranking study - local development evidence", "PARTIAL")
lines(1172, 1285, [
    "RRF top-20 -> score every pair -> measure prefixes at 5 / 10 / 20; full ranks are saved.",
    "Four-question batch-one probes: Qwen4B 27.90 s/question; Qwen0.6B 5.95 s/question.",
    "Batch four: one P05 check took 46.36 s versus 30.85 s at batch one; no speed gain shown.",
    "120-question 4B run: user-reported in progress; completed full-set results not reviewed.",
    "Final model/context budget: OPEN. Reranker benchmarks write JSON; tracing integration pending."], size=21)

text(60, 1480, "D. OFFLINE DEVELOPMENT EVALUATION - SEPARATE FROM THE USER RESPONSE PATH", 28, INK, True)
text(60, 1514, "Six retrieval-quality metrics at k = 5, 10, 20 | Means: 100 answerable questions | 20 unanswerable cases reported separately", 23, MUTED)
stages = [
    (60, "1  Fixed questions / evidence", "DONE", 640),
    (740, "2  Run and compare methods", "PARTIAL", 640),
    (1420, "3  Six metrics + timing", "DONE", 640),
    (2100, "4  Final answer / tool / router study", "NOT BUILT", 640),
]
for x, title, status, width in stages:
    color, fill = COLORS[status]
    rect(x, 1540, width, 58, fill, color, 10)
    text(x + 16, 1577, title, 23, INK, True)
    badge(x + width - len(status) * 10 - 42, 1554, status)
for x in [700, 1380, 2060]:
    arrow(f"{x},1569 {x + 40},1569")

metrics = [
    (60, 1620, "1  Annotated chunk Recall@k", ["Of all annotated reference chunks,", "what fraction appears in the first k?"]),
    (970, 1620, "2  Required-claim coverage@k", ["Of all required claims, what fraction has", "its annotated support in the first k?"]),
    (1880, 1620, "3  All-claims-supported rate@k", ["Fraction of answerable questions whose", "required claims are all supported at k."]),
    (60, 1770, "4  Precision@k", ["Annotated reference hits in the first k / k.", "The denominator stays k for short result lists."]),
    (970, 1770, "5  MRR@k", ["Mean 1/rank of the first reference hit.", "No reference hit in the first k gives zero."]),
    (1880, 1770, "6  nDCG@k", ["Rewards reference chunks near the top;", "normalized against an ideal ordering."]),
]
for x, y, title, body in metrics:
    panel(x, y, 860, 125, title, "DONE")
    lines(x + 22, y + 77, body, size=23)
text(60, 1930, "These metrics assess retrieved evidence, not LLM answer accuracy. Labels are not exhaustive; unannotated passages remain unjudged.", 22, MUTED)
text(60, 1960, "120 development questions; held-out thesis test set and final protocol OPEN. Later: compare Simple / Enhanced / Agentic / routed / LLM-only.", 21, MUTED)
text(60, 1987, "Status snapshot: 25 Nov 2026 | Sources: STATUS, METHOD_DESIGN, EVALUATION_PLAN, QWEN_RERANKER_COMPARISON", 17, MUTED)

parts.append("</svg>")
svg = ROOT / "pipeline.svg"
svg.write_text("\n".join(parts) + "\n", encoding="utf-8")
subprocess.run(["rsvg-convert", "--format", "png", "--zoom", "1.5", "--output", str(ROOT / "pipeline.png"), str(svg)], check=True)
subprocess.run(["rsvg-convert", "--format", "pdf", "--output", str(ROOT / "pipeline.pdf"), str(svg)], check=True)
print("Updated pipeline.svg, pipeline.png and pipeline.pdf")
