from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    language = Column(String(10), default="en")
    current_step = Column(String(50), default="language_selection")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="conversations")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    # String session key (the public session id) for ownership validation
    # without a join; kept in sync with session_id FK at creation time.
    session_key = Column(String(255), index=True, nullable=True)
    service_id = Column(String(64), index=True, nullable=False, default="")
    service_name = Column(String(255), nullable=False)
    form_number = Column(String(100), nullable=False)
    reference_number = Column(String(100), unique=True, nullable=False)
    application_data = Column(Text, nullable=True)  # JSON string
    status = Column(String(50), default="draft")  # draft, confirmed, generated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DocumentScan(Base):
    """
    Persisted scan record - metadata only (Phase 4).

    IMPORTANT: Raw OCR text is intentionally NOT persisted here.
    Only masked/structured extraction results, quality metrics and status
    transitions are stored. Temporary images are filesystem-only and cleaned up.
    """
    __tablename__ = "document_scans"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(String(64), unique=True, index=True, nullable=False)
    session_id = Column(String(255), index=True, nullable=False)
    service_id = Column(String(64), nullable=False)
    document_id = Column(String(64), nullable=False)
    status = Column(String(32), default="uploaded")
    # uploaded, ocr_processing, readable, needs_rescan,
    # confirmation_pending, confirmed
    quality_status = Column(String(16), nullable=True)  # GOOD / WARNING / POOR
    classification = Column(String(64), nullable=True)  # detected doc type
    classification_match = Column(String(16), nullable=True)  # MATCH / MISMATCH / UNKNOWN
    extraction = Column(Text, nullable=True)  # JSON: masked structured fields
    ocr_available = Column(String(8), default="true")  # engine availability at scan time
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
