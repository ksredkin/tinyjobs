from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Enum, JSON, ForeignKey
from ..enums import JobStatus
from sqlalchemy.ext.mutable import MutableDict

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    func: Mapped[str]
    func_kwargs: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status", values_callable=lambda enum: [item.value for item in enum]), default=JobStatus.PENDING, nullable=False)
    retries: Mapped[int]
    retries_left: Mapped[int]
    ctx_mode: Mapped[bool]

    steps: Mapped[list["Step"]] = relationship(back_populates="job")


class Step(Base):
    __tablename__ = "steps"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    name: Mapped[str]
    result: Mapped[dict|None] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=None)

    job: Mapped["Job"] = relationship(back_populates="steps")
