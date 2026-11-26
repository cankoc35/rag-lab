"""Render the target question-to-answer pipeline with the installed rsvg-convert CLI."""

from html import escape
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
W, H = 3200, 1800
INK, MUTED = "#173342", "#526977"
GREEN, GREEN_FILL = "#087F6F", "#EAF6F1"
GRAY, GRAY_FILL = "#61768A", "#F0F4F8"
BLUE = "#385E8B"
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<title>RAG Workflow Lab - target pipeline from user question to final answer</title>',
         '<desc>Target design: router, Simple, Enhanced and Agentic RAG, answer context, generation, '
         'validation, offline data layer and tracing. Solid boxes are built; dashed boxes are planned. 26 November 2026.</desc>',
         '<defs><marker id="green" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#087F6F"/></marker>',
         '<marker id="gray" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#61768A"/></marker></defs>',
         f'<rect width="{W}" height="{H}" fill="#FCFDFE"/>']


def rect(x, y, w, h, fill, stroke, radius=14, dashed=False, width=2):
    dash = ' stroke-dasharray="12 8"' if dashed else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{width}"{dash}/>')


def text(x, y, value, size=20, color=INK, bold=False, anchor="start"):
    weight = 700 if bold else 400
    parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Helvetica,Arial,sans-serif" '
                 f'font-size="{size}" font-weight="{weight}" fill="{color}">{escape(value)}</text>')


def open_badge(x, y):
    rect(x, y, 74, 28, BLUE, BLUE, 7)
    text(x + 37, y + 20, "OPEN", 16, "white", True, "middle")


def box(x, y, w, h, title, body, built=True, is_open=False, size=21, title_size=25, border=2):
    """Solid green = built and checked; dashed gray = planned."""
    rect(x, y, w, h, GREEN_FILL if built else GRAY_FILL, GREEN if built else GRAY, 12, not built, border)
    text(x + 18, y + 34, title, title_size, INK, True)
    for i, line in enumerate(body):
        text(x + 18, y + 36 + title_size + (size + 7) * i, line, size, MUTED)
    if is_open:
        open_badge(x + w - 90, y + 12)


def lane(y, h, title, caption):
    rect(680, y, 1520, h, "white", "#B9C9D4", 18)
    text(705, y + 42, title, 26, INK, True)
    text(2180, y + 42, caption, 19, MUTED, anchor="end")


def arrow(points, built=True):
    color, marker = (GREEN, "green") if built else (GRAY, "gray")
    dash = "" if built else ' stroke-dasharray="9 7"'
    parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"{dash} '
                 f'marker-end="url(#{marker})"/>')


# Header and legend.
text(70, 62, "RAG WORKFLOW LAB", 22, GREEN, True)
text(70, 112, "Target pipeline: from user question to final answer", 44, INK, True)
text(70, 150, "How the finished system answers one question | Target design, 26 November 2026", 23, MUTED)
rect(2330, 36, 60, 28, GREEN_FILL, GREEN, 6)
text(2405, 58, "Built and checked", 20, INK)
rect(2330, 78, 60, 28, GRAY_FILL, GRAY, 6, dashed=True)
text(2405, 100, "Planned, not built yet", 20, INK)
open_badge(2323, 120)
text(2405, 142, "Design choice still undecided", 20, INK)
text(2780, 58, "Green arrow: working connection", 20, GREEN)
text(2780, 100, "Dashed arrow: planned connection", 20, MUTED)

# Lane backgrounds first, then connections, then boxes, so arrows stay visible.
lane(200, 175, "Simple RAG - baseline", "Built; runs end to end")
lane(405, 575, "Enhanced RAG - hybrid retrieval, reranking, fixed tool steps",
     "Retrieval built and checked live; answer wiring next")
lane(1010, 300, "Agentic RAG - the LLM chooses the next tool (LangGraph)", "Planned")
arrow("300,750 340,750", built=False)
arrow("640,750 660,750 660,310 680,310", built=False)
arrow("660,750 660,690 680,690", built=False)
arrow("660,750 660,1140 680,1140", built=False)
arrow("1470,310 1530,310")
arrow("2170,310 2290,310")
arrow("1110,550 1135,550 1135,610 1160,610")
arrow("1110,725 1135,725 1135,670 1160,670")
arrow("1500,640 1550,640")
arrow("1960,640 2000,640")
arrow("2170,640 2230,640 2230,350 2290,350", built=False)
arrow("2170,890 2245,890 2245,385 2290,385", built=False)
arrow("2170,1145 2260,1145 2260,415 2290,415", built=False)
arrow("1040,1145 1100,1145", built=False)
arrow("1480,1145 1540,1145", built=False)
arrow("1840,1145 1900,1145", built=False)
arrow("2035,1215 2035,1255 875,1255 875,1220", built=False)
arrow("2710,450 2710,495")
arrow("2710,730 2710,785", built=False)
arrow("2710,1020 2710,1075", built=False)
arrow("1000,1395 1000,1316")
arrow("1770,1395 1770,1316", built=False)

# Question and router.
box(70, 670, 230, 160, "User question", ["Raw English text,", "sent unchanged"], size=22, title_size=26)
box(340, 590, 300, 320, "Workflow router", [
    "Picks ONE workflow", "per question", "Input: question text only", "No gold labels or",
    "other workflows' answers", "Method: rules, classifier", "or LLM"], built=False)
open_badge(358, 868)

# Simple RAG.
box(710, 262, 760, 95, "Dense retrieval - top 5", ["Nomic query embedding + pgvector cosine search"])
box(1530, 262, 640, 95, "Top 5 chunks go to the answer", ["One retrieval pass; no hybrid search, reranking or tools"])

# Enhanced RAG.
box(710, 475, 400, 150, "Dense retrieval - top 20",
    ["Nomic Embed Text v1.5, local CPU", "768-dimensional query vector", "pgvector cosine distance"])
box(710, 650, 400, 150, "Lexical retrieval - top 20",
    ["PostgreSQL full-text search", "English stemming, OR of terms", "Ranked by ts_rank_cd"])
box(1160, 555, 340, 170, "RRF fusion",
    ["Sum of 1 / (60 + rank)", "Equal weights, k = 60", "Deduplicate by chunk ID", "Keep top 20 candidates"])
box(1550, 520, 410, 235, "Qwen3-Reranker-4B", [
    "Local model on Apple MPS, float16", "Scores question + heading + chunk", "Relevance = probability of \"yes\"",
    "Re-sorts all 20 candidates", "Dev set, full evidence in top 5:", "82 -> 92 of 100 questions"])
box(2000, 555, 170, 170, "Top 5", ["Whole chunks", "Source IDs", "RRF rank", "Rerank score"])
box(710, 830, 1460, 120, "Fixed DB-tool steps", [
    "Python rules decide when to inspect the frozen sandbox database: read-only schema / index lookup",
    "and EXPLAIN for allowlisted queries. Conditions and tool contracts are not defined yet."], built=False, is_open=True)

# Agentic RAG.
box(710, 1075, 330, 140, "LLM picks next action", ["Retrieve documents,", "use the DB tool,", "or answer"], built=False)
box(1100, 1075, 380, 140, "Run the chosen tool",
    ["Document retrieval tool", "Sandbox DB tool", "(same tools as Enhanced)"], built=False)
box(1540, 1075, 300, 140, "Observe result", ["Add the evidence", "to the agent state"], built=False)
box(1900, 1075, 270, 140, "Enough evidence?", ["Yes -> answer", "No -> repeat"], built=False)
text(1455, 1293, "Repeat within iteration and time limits; limits not decided yet", 18, MUTED, anchor="middle")

# Shared answer path.
box(2290, 230, 840, 220, "Build answer context", [
    "Chunks labelled S1 ... S5, with source IDs and URLs", "Whole chunks, never truncated",
    "Tool results added when a tool was used (planned)", "Final token budget not decided yet"],
    is_open=True, size=23, title_size=28)
box(2290, 500, 840, 230, "Generate answer", [
    "gpt-6-luna via the OpenAI Responses API", "Prompt answer_v1, reasoning none, max 1000 output tokens",
    "Cites S-labels or says \"insufficient evidence\"", "Same model and prompt in every workflow"],
    size=23, title_size=28)
box(2290, 790, 840, 230, "Validate the output", [
    "Today: answer is completed and nonempty", "Planned: every citation label is valid",
    "Undecided: are claims supported by the sources?", "Undecided: retry / repair policy"],
    built=False, is_open=True, size=23, title_size=28)
box(2290, 1080, 840, 200, "Final answer", [
    "Answer with cited sources (S1 ... S5),", "or \"insufficient evidence\" when the sources", "do not support an answer"],
    size=24, title_size=32, border=4)

# Offline data layer.
text(70, 1375, "PREPARED OFFLINE - SHARED BY EVERY WORKFLOW", 24, INK, True)
text(1015, 1362, "feeds retrieval in all workflows", 18, GREEN)
text(1785, 1362, "feeds the DB-tool steps", 18, MUTED)
box(70, 1395, 1250, 160, "Document index", [
    "14 sources: 8 PostgreSQL 18 docs + 6 synthetic Atlas docs",
    "Parsed into 151 chunks (target 512 / max 1024 tokens, no overlap)",
    "Nomic vectors and chunk text in PostgreSQL + pgvector"], size=22, title_size=25)
box(1370, 1395, 800, 160, "Frozen sandbox database", [
    "Fixed tables and indexes for tool questions", "Read-only; identical state for every run",
    "Fixtures not defined yet"], built=False, is_open=True, size=22, title_size=25)
box(2290, 1395, 840, 160, "Models", [
    "Nomic Embed Text v1.5 - embeddings, local CPU", "Qwen3-Reranker-4B - reranking, local Apple MPS",
    "gpt-6-luna - answer generation, hosted API"], size=22, title_size=25)

# Tracing and footer.
rect(70, 1590, 3060, 110, "#F6F8FA", "#B9C9D4", 14)
text(92, 1630, "Tracing - every question is one trace and every step one span, stored in PostgreSQL", 24, INK, True)
text(92, 1670, "Records prompts, chunk IDs and ranks, scores, answer, tokens, time and errors. "
     "Built: retrieval and LLM spans. Planned: router, reranker, DB-tool and validator spans.", 22, MUTED)
text(70, 1745, "Target design, not a measured result. The router, Agentic control, DB tools and shared validator are not built yet; "
     "the 82 -> 92 figure is retrieval evidence on development questions, not answer accuracy.", 19, MUTED)
text(70, 1775, "Sources: METHOD_DESIGN, STATUS, HANDOFF, QWEN_RERANKER_COMPARISON | Detailed status: pipeline.png", 17, MUTED)

parts.append("</svg>")
svg = ROOT / "full-flow.svg"
svg.write_text("\n".join(parts) + "\n", encoding="utf-8")
subprocess.run(["rsvg-convert", "--format", "png", "--zoom", "1.2", "--output", str(ROOT / "full-flow.png"), str(svg)], check=True)
subprocess.run(["rsvg-convert", "--format", "pdf", "--output", str(ROOT / "full-flow.pdf"), str(svg)], check=True)
print("Updated full-flow.svg, full-flow.png and full-flow.pdf")
