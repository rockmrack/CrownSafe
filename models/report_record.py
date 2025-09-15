from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from core_infra.database import Base


class ReportRecord(Base):
    __tablename__ = "report_records"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    report_type = Column(String, nullable=False)
    storage_path = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")

    def to_dict(self):
        return {
            "report_id": self.report_id,
            "user_id": self.user_id,
            "report_type": self.report_type,
            "storage_path": self.storage_path,
            "created_at": self.created_at.isoformat() + "Z",
        }


