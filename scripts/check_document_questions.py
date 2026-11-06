"""Check development-question evidence against pinned local source artifacts.

This read-only check needs Python 3.11+ and the saved snapshots/parsed/chunk
files, but no network, tokenizer package, model or database. It verifies
references and integrity; semantic answer support is an editorial review.
"""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_pinned(record: dict, root: Path) -> tuple[Path, bytes]:
    relative = Path(record["path"])
    path = (root / relative).resolve()
    require(not relative.is_absolute() and path.is_relative_to(root),
            "Artifact paths must be relative to the repository root.")
    data = path.read_bytes()
    require(digest(data) == record["sha256"], f"Pinned file hash mismatch: {relative}")
    return path, data


def validate(dataset_path: Path, root: Path = ROOT) -> dict:
    root = root.resolve()
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    require(dataset["schema_version"] == 1, "Unsupported dataset schema version.")
    require(dataset["split"] == "dev" and dataset["language"] == "en",
            "This checker expects the English development subset.")
    require(dataset["status"] == "source_verified", "Expected source-verified annotation status.")
    state = dataset["source_state"]
    _, manifest_data = read_pinned(state["sources_manifest"], root)
    allowlist = {s["source_id"]: s for s in json.loads(manifest_data)["sources"]}
    sources, chunks = {}, {}
    for source in state["sources"]:
        sid = source["source_id"]
        require(sid not in sources, f"Duplicate source: {sid}")
        require(sid in allowlist and source["source_url"] == allowlist[sid]["url"],
                f"Source is outside the selected allowlist: {sid}")
        files = source["files"]
        manifest_path, saved_manifest = read_pinned(files["manifest"], root)
        raw_path, raw = read_pinned(files["raw_html"], root)
        _, parsed = read_pinned(files["parsed"], root)
        _, chunk_bytes = read_pinned(files["chunks"], root)
        snapshot = json.loads(saved_manifest)["snapshot"]
        parsed_payload, chunk_payload = json.loads(parsed), json.loads(chunk_bytes)
        require(parsed_payload["schema_version"] == chunk_payload["schema_version"] == 1,
                f"Unsupported artifact schema: {sid}")
        document = parsed_payload["document"]
        for label, payload in (("snapshot", snapshot), ("parsed", document), ("chunks", chunk_payload)):
            require(payload["snapshot_id"] == source["snapshot_id"], f"Snapshot mismatch: {sid}/{label}")
        # SourceSpec serializes the default empty section_ids for page scope;
        # the allowlist may omit that optional field.
        expected_source = {**allowlist[sid], "selection": {
            **allowlist[sid]["selection"],
            "section_ids": allowlist[sid]["selection"].get("section_ids", []),
        }}
        require(snapshot["source"] == expected_source, f"Snapshot source definition mismatch: {sid}")
        require(raw_path == (manifest_path.parent / snapshot["local_path"]).resolve(),
                f"Raw HTML path mismatch: {sid}")
        require(snapshot["sha256"] == document["source_sha256"] == digest(raw),
                f"Raw source hash mismatch: {sid}")
        require(snapshot["size_bytes"] == len(raw), f"Raw source size mismatch: {sid}")
        require(document["source_id"] == chunk_payload["source_id"] == sid,
                f"Source identity mismatch: {sid}")
        require(document["source_url"] == source["source_url"], f"Source URL mismatch: {sid}")
        require(document["parser_version"] == source["parser_version"], f"Parser version mismatch: {sid}")
        actual_blocks = []
        source_chunks = chunk_payload["chunks"]
        for position, chunk in enumerate(source_chunks):
            cid = chunk["chunk_id"]
            require(cid not in chunks, f"Duplicate chunk ID: {cid}")
            require(chunk["source_id"] == sid and chunk["snapshot_id"] == source["snapshot_id"],
                    f"Chunk source/snapshot mismatch: {cid}")
            require(chunk["source_url"] == source["source_url"]
                    and chunk["source_sha256"] == document["source_sha256"]
                    and chunk["parser_version"] == document["parser_version"],
                    f"Chunk provenance mismatch: {cid}")
            for key in ("chunker_version", "serialization_version", "tokenizer"):
                require(chunk[key] == state["chunking"][key], f"Chunk {key} mismatch: {cid}")
            for key, value in state["chunking"]["settings"].items():
                require(chunk[key] == value, f"Chunk setting {key} mismatch: {cid}")
            expected_previous = source_chunks[position - 1]["chunk_id"] if position else None
            expected_next = source_chunks[position + 1]["chunk_id"] if position + 1 < len(source_chunks) else None
            require(chunk["previous_chunk_id"] == expected_previous
                    and chunk["next_chunk_id"] == expected_next, f"Chunk neighbor mismatch: {cid}")
            require(len(chunk["blocks"]) == len(chunk["block_indices"]), f"Block position mismatch: {cid}")
            actual_blocks.extend(zip(chunk["block_indices"], chunk["blocks"]))
            chunks[cid] = chunk
        expected_blocks = [(i, b) for i, b in enumerate(document["blocks"], 1) if b["kind"] != "heading"]
        require(actual_blocks == expected_blocks, f"Content blocks lost, duplicated or changed: {sid}")
        sources[sid] = (source, document)

    question_ids, all_evidence_ids, referenced_chunks, referenced_blocks = set(), set(), set(), set()
    evidence_count, requirement_count = 0, 0
    require(bool(dataset["questions"]), "Dataset contains no questions.")
    for question in dataset["questions"]:
        qid = question["question_id"]
        require(qid not in question_ids, f"Duplicate question ID: {qid}")
        question_ids.add(qid)
        require(question["verification_status"] == "source_verified", f"Unverified question: {qid}")
        require(question["question_type"] in {"direct_document", "multi_document"}, f"Unknown question type: {qid}")
        require(bool(question["question"].strip()) and bool(question["expected_answer"].strip()),
                f"Empty question or expected answer: {qid}")
        evidence_ids = set()
        for evidence in question["evidence"]:
            eid = evidence["evidence_id"]
            require(eid.startswith(qid + "-") and eid not in all_evidence_ids,
                    f"Duplicate or mismatched evidence ID: {eid}")
            all_evidence_ids.add(eid)
            evidence_ids.add(eid)
            sid = evidence["source_id"]
            source, document = sources[sid]
            index = evidence["block_index"]
            require(type(index) is int and 1 <= index <= len(document["blocks"]),
                    f"Invalid block index: {eid}")
            block = document["blocks"][index - 1]
            chunk = chunks[evidence["chunk_id"]]
            require(chunk["source_id"] == sid and evidence["snapshot_id"] == source["snapshot_id"],
                    f"Evidence source/snapshot mismatch: {eid}")
            require(index in chunk["block_indices"], f"Evidence block is outside its chunk: {eid}")
            require(chunk["blocks"][chunk["block_indices"].index(index)] == block,
                    f"Evidence block differs from its chunk: {eid}")
            require(digest(block["text"].encode("utf-8")) == evidence["block_sha256"],
                    f"Evidence block hash mismatch: {eid}")
            require(evidence["heading_path"] == block["heading_path"]
                    and evidence["anchor"] == block["anchor"], f"Evidence context mismatch: {eid}")
            citation = source["source_url"] + ("#" + block["anchor"] if block["anchor"] else "")
            require(evidence["citation_url"] == citation, f"Evidence citation URL mismatch: {eid}")
            span = evidence["span"]
            start, end = span["start"], span["end"]
            require(type(start) is int and type(end) is int and 0 <= start < end <= len(block["text"]),
                    f"Invalid evidence span offsets: {eid}")
            require(block["text"][start:end] == span["text"], f"Evidence span text mismatch: {eid}")
            referenced_chunks.add(evidence["chunk_id"])
            referenced_blocks.add((sid, index))
            evidence_count += 1
        require(bool(evidence_ids), f"Question has no evidence: {qid}")
        require(bool(question["answer_requirements"]), f"Question has no answer requirements: {qid}")
        requirement_ids = set()
        for requirement in question["answer_requirements"]:
            rid = requirement["requirement_id"]
            require(rid.startswith(qid + "-") and rid not in requirement_ids, f"Invalid requirement ID: {rid}")
            requirement_ids.add(rid)
            require(requirement["support_mode"] == "any", f"Unsupported evidence support mode: {rid}")
            require(bool(requirement["statement"].strip()), f"Empty answer requirement: {rid}")
            refs = requirement["supporting_evidence_ids"]
            require(bool(refs) and set(refs) <= evidence_ids, f"Unknown requirement evidence: {rid}")
            requirement_count += 1
        if "optional_guidance" in question:
            refs = question["optional_guidance"]["supporting_evidence_ids"]
            require(bool(refs) and set(refs) <= evidence_ids, f"Unknown optional evidence: {qid}")

    return {
        "dataset_id": dataset["dataset_id"], "dataset_version": dataset["dataset_version"],
        "dataset_sha256": digest(dataset_bytes), "questions": len(question_ids),
        "sources": len(sources), "answer_requirements": requirement_count,
        "evidence_records": evidence_count, "referenced_chunks": len(referenced_chunks),
        "referenced_blocks": len(referenced_blocks), "status": "reference_checks_passed",
        "semantic_review": "Recorded editorial review; not inferred by this checker",
        "retrieval_or_model_evaluation": "Not run by this checker",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path,
                        default=ROOT / "data/evaluation/dev/document_questions.json")
    args = parser.parse_args()
    try:
        result = validate(args.dataset)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
