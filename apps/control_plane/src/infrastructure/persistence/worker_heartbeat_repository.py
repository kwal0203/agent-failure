from datetime import datetime
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from sqlalchemy.dialects.postgresql import insert, Insert
from sqlalchemy import select

from .models import WorkerHeartbeatModel


class SQLAlchemyWorkerHeartbeatRepository:
    def record_tick(self, worker_name: str, at: datetime) -> None:
        with SessionFactory() as db:
            stmt: Insert = insert(WorkerHeartbeatModel).values(
                worker_name=worker_name, last_tick_at=at, updated_at=at
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[WorkerHeartbeatModel.worker_name],
                set_={"last_tick_at": at, "updated_at": at},
            )
            db.execute(stmt)
            db.commit()

    def record_success(self, worker_name: str, at: datetime) -> None:
        with SessionFactory() as db:
            stmt: Insert = insert(WorkerHeartbeatModel).values(
                worker_name=worker_name,
                last_tick_at=at,
                last_success_at=at,
                last_error=None,
                updated_at=at,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[WorkerHeartbeatModel.worker_name],
                set_={"last_tick_at": at, "last_success_at": at, "updated_at": at},
            )
            db.execute(stmt)
            db.commit()

    def record_error(self, worker_name: str, at: datetime, error_message: str) -> None:
        with SessionFactory() as db:
            stmt: Insert = insert(WorkerHeartbeatModel).values(
                worker_name=worker_name,
                last_tick_at=at,
                last_error=error_message[:1024],
                updated_at=at,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[WorkerHeartbeatModel.worker_name],
                set_={
                    "last_tick_at": at,
                    "last_error": error_message[:1024],
                    "updated_at": at,
                },
            )
            db.execute(stmt)
            db.commit()

    def read_heartbeat(self, worker_name: str) -> WorkerHeartbeatModel | None:
        with SessionFactory() as db:
            stmt = select(WorkerHeartbeatModel).where(
                WorkerHeartbeatModel.worker_name == worker_name
            )
            return db.execute(stmt).scalar_one_or_none()
