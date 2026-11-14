"""全部 ORM 模型集中导出，Alembic autogenerate 靠这个包看到所有表。"""
from app.db.base import Base
from app.models.ai_settings import UserAiSettings
from app.models.cache import VisionExtractCache
from app.models.draft import Draft
from app.models.generation import GeneratedQuestion, GenerationTask
from app.models.question import Question, QuestionTag, Tag
from app.models.records import AiCallLog, PracticeRecord
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Question",
    "Tag",
    "QuestionTag",
    "GeneratedQuestion",
    "GenerationTask",
    "Draft",
    "UserAiSettings",
    "VisionExtractCache",
    "PracticeRecord",
    "AiCallLog",
]
