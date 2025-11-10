from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Float, Boolean

Base = declarative_base()

class Log(Base):  # для совместимости
    __tablename__ = "logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String(64))
    level: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)

class Feature(Base):
    __tablename__ = "features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_id: Mapped[int] = mapped_column(Integer)
    vector_ref: Mapped[str] = mapped_column(String(128))

class ModelMeta(Base):
    __tablename__ = "models"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(String(256))
    metric_aupr: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")

class BGLLog(Base):  # старое
    __tablename__ = "bgl_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    line_id: Mapped[int] = mapped_column(Integer)
    alert_tag: Mapped[str] = mapped_column(String(64))
    is_alert: Mapped[bool] = mapped_column(Boolean)
    raw: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)

class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    templ_id: Mapped[int] = mapped_column(Integer)      # id из dict_templ.csv
    template: Mapped[str] = mapped_column(Text)

class TemplateVector(Base):
    __tablename__ = "template_vectors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    templ_id: Mapped[int] = mapped_column(Integer)      # внешний ключ на templates.templ_id (логически)
    vector_json: Mapped[str] = mapped_column(Text)      # JSON список float

