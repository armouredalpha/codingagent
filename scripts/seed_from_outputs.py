"""
Seed Qdrant from all question.json / questions.json files under outputs/.

Only these fields are stored in Qdrant payload (others are silently dropped):
  question_id, topic, difficulty, estimated_time_minutes, question,
  context, files_to_edit, notes, tasks, skill

Field mapping from new-format question.json:
  objective            → question
  scenario             → context
  file_to_edit         → files_to_edit  (wrapped in list)
  constraints          → notes
  tested_skills        → skill
  estimated_solve_minutes → estimated_time_minutes

Usage:
  python scripts/seed_from_outputs.py [--dry-run] [--outputs-dir outputs]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Allowed payload keys (exactly what the user wants in Qdrant)
# ---------------------------------------------------------------------------
ALLOWED_KEYS = {
    "question_id",
    "topic",
    "difficulty",
    "estimated_time_minutes",
    "question",
    "context",
    "files_to_edit",
    "notes",
    "tasks",
    "skill",
}

# ---------------------------------------------------------------------------
# Field normaliser — maps both old and new schema to target schema
# ---------------------------------------------------------------------------

def normalise(raw: dict, fallback_topic: str = "") -> dict | None:
    """Return a payload dict with only ALLOWED_KEYS, or None if no question_id."""
    qid = raw.get("question_id") or raw.get("id")
    if not qid:
        return None

    out: dict = {"question_id": qid}

    # topic
    topic = raw.get("topic") or fallback_topic
    if topic:
        out["topic"] = topic

    # difficulty
    diff = raw.get("difficulty")
    if diff:
        out["difficulty"] = diff

    # estimated_time_minutes  (old: estimated_time_minutes, new: estimated_solve_minutes)
    eta = raw.get("estimated_time_minutes") or raw.get("estimated_solve_minutes")
    if eta is not None:
        out["estimated_time_minutes"] = eta

    # question  (old: question, new: objective)
    question = raw.get("question") or raw.get("objective")
    if question:
        out["question"] = question

    # context  (old: context, new: scenario)
    context = raw.get("context") or raw.get("scenario")
    if context:
        out["context"] = context

    # files_to_edit  (old: files_to_edit list, new: file_to_edit string)
    files = raw.get("files_to_edit") or raw.get("file_to_edit")
    if files:
        out["files_to_edit"] = [files] if isinstance(files, str) else files

    # notes  (old: notes list, new: constraints list)
    notes = raw.get("notes") or raw.get("constraints")
    if notes:
        out["notes"] = notes if isinstance(notes, list) else [notes]

    # tasks  (old format only)
    tasks = raw.get("tasks")
    if tasks:
        out["tasks"] = tasks if isinstance(tasks, list) else [tasks]

    # skill  (old: skill string, new: tested_skills list)
    skill = raw.get("skill") or raw.get("tested_skills")
    if skill:
        out["skill"] = skill if isinstance(skill, list) else [skill]

    return out


# ---------------------------------------------------------------------------
# Collect all questions from outputs/
# ---------------------------------------------------------------------------

def collect_questions(outputs_dir: Path) -> list[dict]:
    """Walk outputs/ and return a list of normalised payload dicts (approved + rejected)."""
    import yaml

    # Dedup by content hash — same question_id with different content gets its
    # own slot; byte-identical duplicates across runs are collapsed to one.
    seen: set[str] = set()
    questions: list[dict] = []

    def _add(payload: dict) -> None:
        h = content_hash(payload)
        if h in seen:
            return
        seen.add(h)
        questions.append(payload)

    # ------------------------------------------------------------------
    # 1. APPROVED — question.json (per-question dirs) and flat Q*.json
    # ------------------------------------------------------------------
    _EXCLUDE_NAMES = {"solution.json", "grading.json", "questions.json"}

    approved_files = sorted(
        f for f in outputs_dir.rglob("*.json")
        if f.name == "question.json"
        or (f.name.startswith("Q") and f.name not in _EXCLUDE_NAMES
            and f.parent.name == "questions")
    )

    for qfile in approved_files:
        try:
            raw = json.loads(qfile.read_text())
        except Exception as e:
            print(f"  SKIP (parse error) {qfile}: {e}", file=sys.stderr)
            continue
        fallback_topic = _infer_topic(qfile)
        payload = normalise(raw, fallback_topic)
        if payload is None:
            continue
        payload["status"] = "approved"
        payload["generated_at"] = _infer_timestamp(qfile)
        _add(payload)

    # ------------------------------------------------------------------
    # 2. APPROVED — bulk questions.json wrapper files
    # ------------------------------------------------------------------
    for qfile in sorted(outputs_dir.rglob("questions.json")):
        try:
            raw = json.loads(qfile.read_text())
        except Exception as e:
            print(f"  SKIP (parse error) {qfile}: {e}", file=sys.stderr)
            continue
        fallback_topic = _infer_topic(qfile)
        if isinstance(raw, dict):
            fallback_topic = raw.get("topic", fallback_topic)
            items = raw.get("questions", [raw])
        elif isinstance(raw, list):
            items = raw
        else:
            continue
        ts = _infer_timestamp(qfile)
        for item in items:
            if not isinstance(item, dict):
                continue
            payload = normalise(item, fallback_topic)
            if payload is None:
                continue
            payload["status"] = "approved"
            payload["generated_at"] = ts
            _add(payload)

    # ------------------------------------------------------------------
    # 3. REJECTED — question.yaml files inside rejected/ subdirectories
    # ------------------------------------------------------------------
    for qfile in sorted(outputs_dir.rglob("rejected/*/question.yaml")):
        try:
            raw = yaml.safe_load(qfile.read_text())
        except Exception as e:
            print(f"  SKIP (parse error) {qfile}: {e}", file=sys.stderr)
            continue
        if not isinstance(raw, dict):
            continue
        fallback_topic = _infer_topic(qfile)
        payload = normalise(raw, fallback_topic)
        if payload is None:
            continue
        payload["status"] = "rejected"
        payload["generated_at"] = _infer_timestamp(qfile)
        _add(payload)

    return questions


def _infer_topic(json_path: Path) -> str:
    """Best-effort topic inference from nearby summary.json or folder name."""
    for parent in json_path.parents:
        summary = parent / "summary.json"
        if summary.exists():
            try:
                s = json.loads(summary.read_text())
                t = s.get("topic") or s.get("run", {}).get("topic")
                if t:
                    return t
            except Exception:
                pass
        if parent.name == "outputs":
            break
    return ""


def _infer_timestamp(qfile: Path) -> str:
    """Return ISO-8601 timestamp for when this question was generated.
    Priority: run_metadata.json created_at → folder name → file mtime."""
    import re, datetime, os

    # 1. Walk up looking for run_metadata.json
    for parent in qfile.parents:
        meta = parent / "run_metadata.json"
        if meta.exists():
            try:
                d = json.loads(meta.read_text())
                ts = d.get("created_at")
                if ts:
                    return ts
            except Exception:
                pass
        if parent.name == "outputs":
            break

    # 2. Parse timestamp from any ancestor folder name (2026-06-13_23-53-52 style)
    for part in qfile.parts:
        m = re.match(r"(\d{4}-\d{2}-\d{2})[_T](\d{2}[-:]?\d{2}[-:]?\d{2})", part)
        if m:
            date = m.group(1)
            time = re.sub(r"[-]", ":", m.group(2))
            return f"{date}T{time}+00:00"

    # 3. Fall back to file modification time
    mtime = os.path.getmtime(qfile)
    return datetime.datetime.fromtimestamp(
        mtime, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ---------------------------------------------------------------------------
# Embedding — uses text-embedding-3-small via OpenRouter (cheapest option)
# ---------------------------------------------------------------------------

def embed_batch(texts: list[str], api_key: str) -> list[list[float]]:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    resp = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=texts,
    )
    return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]


def payload_to_text(p: dict) -> str:
    """Build a single string for embedding from the allowed fields."""
    parts = []
    for key in ["topic", "difficulty", "skill", "question", "context", "notes", "tasks"]:
        val = p.get(key)
        if not val:
            continue
        if isinstance(val, list):
            parts.append(" ".join(str(v) for v in val))
        else:
            parts.append(str(val))
    return " | ".join(parts)


def content_hash(p: dict) -> str:
    """Stable hash of question content — used as the Qdrant point ID so
    two questions with the same question_id but different content each get
    their own slot."""
    key = "|".join(str(p.get(f, "")) for f in
                   ["question", "context", "skill", "files_to_edit", "difficulty"])
    return hashlib.md5(key.encode()).hexdigest()


def point_id_from_content(p: dict) -> int:
    return int(content_hash(p), 16) % (2 ** 63)


# ---------------------------------------------------------------------------
# Upload to Qdrant
# ---------------------------------------------------------------------------

def fetch_existing_content_hashes(client, collection: str) -> set[str]:
    """Scroll all existing points and compute content hashes from their payloads.
    Used to skip re-uploading questions whose content is already in Qdrant."""
    existing: set[str] = set()
    offset = None
    while True:
        results, next_offset = client.scroll(
            collection_name=collection,
            limit=100,
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )
        for r in results:
            h = content_hash(r.payload)
            existing.add(h)
        if next_offset is None:
            break
        offset = next_offset
    return existing


def upload(questions: list[dict], qdrant_url: str, qdrant_api_key: str,
           openrouter_api_key: str, collection: str, batch_size: int = 10,
           dry_run: bool = False) -> None:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=60)

    # Ensure collection exists
    if not client.collection_exists(collection):
        print(f"Collection '{collection}' not found — creating it...")
        if not dry_run:
            probe = embed_batch(["probe"], openrouter_api_key)
            dim = len(probe[0])
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            print(f"  Created collection '{collection}' with dim={dim}")
        existing_hashes: set[str] = set()
    else:
        print(f"Collection '{collection}' exists — fetching existing content hashes to skip duplicates...")
        existing_hashes = fetch_existing_content_hashes(client, collection) if not dry_run else set()
        print(f"  {len(existing_hashes)} existing points found.")

    # Filter to only questions whose content isn't already in Qdrant
    new_questions = [p for p in questions if content_hash(p) not in existing_hashes]
    skipped = len(questions) - len(new_questions)
    print(f"\n  {skipped} questions already in Qdrant (skipped).")
    print(f"  {len(new_questions)} new questions to upload.\n")

    if not new_questions:
        print("Nothing new to upload.")
        return

    total = len(new_questions)
    uploaded = 0

    for i in range(0, total, batch_size):
        batch = new_questions[i: i + batch_size]
        texts = [payload_to_text(p) for p in batch]

        if dry_run:
            for p in batch:
                print(f"  [dry-run] [{p['status']:8}] {p['question_id']}")
            uploaded += len(batch)
            continue

        print(f"  Embedding batch {i // batch_size + 1} ({len(batch)} questions)...")
        vectors = embed_batch(texts, openrouter_api_key)

        points = [
            PointStruct(
                id=point_id_from_content(p),  # content hash — unique per question body
                vector=vec,
                payload=p,
            )
            for p, vec in zip(batch, vectors)
        ]
        client.upsert(collection_name=collection, points=points)
        uploaded += len(batch)
        print(f"  Upserted {uploaded}/{total}")

    print(f"\nDone. {uploaded} new questions added to '{collection}'.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_env(env_file: str = ".env") -> None:
    """Load key=value pairs from .env into os.environ (no-op if file missing)."""
    env_path = Path(env_file)
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Qdrant from outputs/ question files")
    parser.add_argument("--outputs-dir", default="outputs", help="Path to outputs/ directory")
    parser.add_argument("--collection", default="robo_questions", help="Qdrant collection name")
    parser.add_argument("--batch-size", type=int, default=10, help="Embedding batch size")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded, don't actually upload")
    args = parser.parse_args()

    # Load .env from project root (script is in scripts/, root is one level up)
    script_dir = Path(__file__).parent
    load_env(script_dir.parent / ".env")

    qdrant_url = os.environ.get("QDRANT_URL", "")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY", "")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not qdrant_url:
        sys.exit("ERROR: QDRANT_URL not set in .env or environment")
    if not openrouter_api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY not set in .env or environment")

    outputs_dir = Path(args.outputs_dir)
    if not outputs_dir.is_absolute():
        outputs_dir = script_dir.parent / outputs_dir

    print(f"Scanning: {outputs_dir}")
    questions = collect_questions(outputs_dir)
    print(f"Found {len(questions)} unique questions across all output folders.\n")

    if not questions:
        print("Nothing to upload.")
        return

    # Show a quick breakdown
    by_difficulty: dict[str, int] = {}
    for q in questions:
        d = q.get("difficulty", "unknown")
        by_difficulty[d] = by_difficulty.get(d, 0) + 1
    for d, n in sorted(by_difficulty.items()):
        print(f"  {d:10s}: {n}")
    print()

    upload(
        questions=questions,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        openrouter_api_key=openrouter_api_key,
        collection=args.collection,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
