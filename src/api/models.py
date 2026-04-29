from sqlalchemy import Column, String, Boolean, DateTime, Float, Text, PrimaryKeyConstraint, func
from sqlalchemy.orm import relationship
from src.api.database import Base


class CreditCode(Base):
    __tablename__ = "credit_codes"

    id = Column(String(36), primary_key=True)
    code = Column(String(16), unique=True, nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    batch_id = Column(String(36), nullable=True)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    image_id = Column(String(36), nullable=False)
    calibration_mmpp = Column(Float, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    landmarks = Column(Text, nullable=True)  # JSON string of 29 landmarks
    pred_image_path = Column(String(255), nullable=True)  # Path to predicted image
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class CalibrationConfig(Base):
    __tablename__ = "calibration_config"

    key = Column(String(50), primary_key=True)
    value = Column(String(100), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DownloadToken(Base):
    __tablename__ = "download_tokens"

    token = Column(String(64), primary_key=True)
    job_id = Column(String(36), nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PixelSize(Base):
    __tablename__ = "pixel_sizes"

    id = Column(String(36), primary_key=True)
    image_id = Column(String(36), unique=True, nullable=False, index=True)
    mm_per_pixel = Column(Float, nullable=False)
    calibration_source = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
