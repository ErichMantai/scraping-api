from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True)
    name:        Mapped[str]      = mapped_column(String(100))           # Nome do cliente
    key:         Mapped[str]      = mapped_column(String(64), unique=True, index=True)
    is_active:   Mapped[bool]     = mapped_column(Boolean, default=True)
    rate_limit:  Mapped[int]      = mapped_column(Integer, default=10)   # req/minuto
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_used:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    logs: Mapped[list["RequestLog"]] = relationship(back_populates="api_key")


class RequestLog(Base):
    __tablename__ = "request_logs"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True)
    api_key_id:  Mapped[int]      = mapped_column(ForeignKey("api_keys.id"))
    termo:       Mapped[str]      = mapped_column(String(200))
    paginas:     Mapped[int]      = mapped_column(Integer)
    total:       Mapped[int]      = mapped_column(Integer, default=0)    # produtos retornados
    from_cache:  Mapped[bool]     = mapped_column(Boolean, default=False)
    duration_ms: Mapped[int]      = mapped_column(Integer, default=0)
    status:      Mapped[str]      = mapped_column(String(20), default="ok")  # ok | error
    error_msg:   Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=func.now())

    api_key: Mapped["ApiKey"] = relationship(back_populates="logs")


class SearchCache(Base):
    __tablename__ = "search_cache"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    cache_key:  Mapped[str]      = mapped_column(String(300), unique=True, index=True)
    resultado:  Mapped[str]      = mapped_column(Text)   # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
