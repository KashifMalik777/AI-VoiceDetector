"""Hash-chained audit ledger.

Every alert and every officer override stores the SHA-256 of the record before it.
GET /api/audit/verify walks the chain and proves nothing was altered.

Say plainly: this is a tamper-evident append-only log, not a blockchain.
It gives non-repudiation for fraud decisions, which is the property that matters.
"""
from __future__ import annotations
import hashlib, json
from .db import SessionLocal, Ledger

GENESIS = "0" * 64


def _ts(dtv) -> str:
    """Timestamps MUST normalise identically on write and on read-back.

    SQLite has no timezone type: a tz-aware datetime goes in as
    "...+00:00" and comes back NAIVE. Hashing the raw isoformat therefore
    broke the chain on the very first verify. Strip tzinfo on both sides.
    """
    return dtv.replace(tzinfo=None).isoformat(timespec="microseconds")


def _digest(prev: str, kind: str, payload: str, ts: str) -> str:
    return hashlib.sha256(f"{prev}|{kind}|{payload}|{ts}".encode("utf-8")).hexdigest()


def append(kind: str, payload: dict) -> str:
    db = SessionLocal()
    try:
        last = db.query(Ledger).order_by(Ledger.idx.desc()).first()
        prev = last.hash if last else GENESIS
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        row = Ledger(kind=kind, payload_json=body, prev_hash=prev, hash="")
        db.add(row)
        db.flush()
        row.hash = _digest(prev, kind, body, _ts(row.ts))
        db.commit()
        return row.hash
    finally:
        db.close()


def verify() -> dict:
    db = SessionLocal()
    try:
        rows = db.query(Ledger).order_by(Ledger.idx.asc()).all()
        prev = GENESIS
        for r in rows:
            expect = _digest(prev, r.kind, r.payload_json, _ts(r.ts))
            if r.prev_hash != prev or r.hash != expect:
                return {"ok": False, "length": len(rows), "broken_at": r.idx,
                        "detail": "chain broken -- a record was altered or removed"}
            prev = r.hash
        return {"ok": True, "length": len(rows), "broken_at": None,
                "head": prev, "detail": "chain intact"}
    finally:
        db.close()


def entries(limit: int = 100) -> list[dict]:
    db = SessionLocal()
    try:
        rows = db.query(Ledger).order_by(Ledger.idx.desc()).limit(limit).all()
        return [{"idx": r.idx, "ts": _ts(r.ts) + "Z", "kind": r.kind,
                 "payload": json.loads(r.payload_json),
                 "prev_hash": r.prev_hash[:16] + "...", "hash": r.hash[:16] + "..."}
                for r in rows]
    finally:
        db.close()
