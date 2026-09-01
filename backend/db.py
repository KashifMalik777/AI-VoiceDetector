"""SQLite. Zero setup, one file, survives dead venue wifi.

PRIVACY BY CONSTRUCTION: no audio bytes are ever written here. Feature vectors,
embeddings, scores, model version, timestamps and hashes only. That is both the
DPDP answer and the CERT-In answer -- "we log decisions, not voices."
Open the DB in front of a judge; it is a twenty-second answer that lands hard.
"""
from __future__ import annotations
import json, datetime as dt
from sqlalchemy import (create_engine, Column, Integer, String, Float, Boolean, Text, DateTime)
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DB_URL

Base = declarative_base()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)


def _now():
    return dt.datetime.now(dt.timezone.utc)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    started_at = Column(DateTime, default=_now)
    ended_at = Column(DateTime, nullable=True)
    meta_json = Column(Text, default="{}")
    peak_risk = Column(Integer, default=0)
    final_band = Column(String, default="SAFE")
    frames = Column(Integer, default=0)
    abstained = Column(Integer, default=0)


class Frame(Base):
    """One scored window. NOTE: features_json, never audio."""
    __tablename__ = "frames"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True)
    seq = Column(Integer)
    t_ms = Column(Integer)
    state = Column(String)                 # SCORED | ABSTAIN
    risk = Column(Integer, nullable=True)
    band = Column(String, nullable=True)
    acoustic = Column(Float, nullable=True)
    context = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    detectors_json = Column(Text, default="{}")
    quality_json = Column(Text, default="{}")
    reasons_json = Column(Text, default="[]")
    features_json = Column(Text, default="{}")     # engineered features, NOT audio
    model_version = Column(String, default="stub-v0")
    created_at = Column(DateTime, default=_now)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    seq = Column(Integer)
    risk = Column(Integer)
    band = Column(String)
    action = Column(String)
    recommendation = Column(Text, default="")
    created_at = Column(DateTime, default=_now)
    overridden = Column(Boolean, default=False)
    override_reason = Column(String, nullable=True)
    override_by = Column(String, nullable=True)
    override_at = Column(DateTime, nullable=True)


class Voiceprint(Base):
    """256-d embedding only. Not reconstructable to audio. Not a voiceprint DATABASE
    in the surveillance sense -- it exists solely to detect drift on one live call."""
    __tablename__ = "voiceprints"
    id = Column(String, primary_key=True)
    name = Column(String)
    embedding_json = Column(Text)
    created_at = Column(DateTime, default=_now)


class Ledger(Base):
    """Tamper-evident hash chain. Every alert and every override chains to the record
    before it. Call it a chained append-only log -- NOT a blockchain. Precision reads
    as expertise to a technical panel; the buzzword reads as bluffing."""
    __tablename__ = "ledger"
    idx = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, default=_now)
    kind = Column(String)                  # ALERT | OVERRIDE | SESSION_END
    payload_json = Column(Text)
    prev_hash = Column(String)
    hash = Column(String)


def init():
    Base.metadata.create_all(engine)


def to_dict(o) -> dict:
    d = {}
    for c in o.__table__.columns:
        v = getattr(o, c.name)
        if isinstance(v, dt.datetime):
            v = v.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        if c.name.endswith("_json") and isinstance(v, str):
            try:
                d[c.name[:-5]] = json.loads(v)
                continue
            except Exception:
                pass
        d[c.name] = v
    return d
