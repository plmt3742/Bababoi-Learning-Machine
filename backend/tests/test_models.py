"""模型层的行为测试：JSON 结构往返、归属隔离、两条唯一约束。

这里不测业务规则（那是 schema 层与 service 层的事），只证明「库能如实存下来」。
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base, utcnow
from app.models import Draft, Question, Tag, User


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'models.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _user(session: Session, name: str) -> User:
    user = User(username=name, password_hash="hash-not-the-plaintext")
    session.add(user)
    session.flush()
    return user


def test_options_and_blanks_round_trip_unchanged(session) -> None:
    """05 把 options/blanks 存 JSON，那读出来必须和写进去一模一样，包括 LaTeX 反斜杠。"""
    owner = _user(session, "alice")
    question = Question(
        user_id=owner.id,
        subject="数学",
        source_type="text",
        content_md="已知 $x^2=4$ 且 $x<0$，则 $x=$ ___",
        question_type="blank",
        blanks=[{"index": 1, "answer_md": "$-2$"}],
        options=[
            {"label": "A", "content_md": "$2$"},
            {"label": "B", "content_md": "$\\pm 2$"},
        ],
        status="confirmed",
    )
    session.add(question)
    session.commit()

    loaded = session.get(Question, question.id)
    assert loaded.blanks == [{"index": 1, "answer_md": "$-2$"}]
    assert loaded.options[1]["content_md"] == "$\\pm 2$"
    assert loaded.content_md == "已知 $x^2=4$ 且 $x<0$，则 $x=$ ___"
    assert loaded.mastery_status == "unmastered"  # 默认值（原型 A2 三值之一）


def test_questions_are_isolated_per_user(session) -> None:
    """US-6 的安全底线「错题按用户隔离」，库层面先证明可查。"""
    alice, bob = _user(session, "alice"), _user(session, "bob")
    for owner in (alice, bob):
        session.add(
            Question(
                user_id=owner.id,
                subject="数学",
                source_type="text",
                content_md=f"{owner.username} 的题",
                question_type="solve",
                status="confirmed",
            )
        )
    session.commit()

    rows = session.scalars(select(Question).where(Question.user_id == alice.id)).all()
    assert [q.content_md for q in rows] == ["alice 的题"]


def test_draft_is_one_per_account(session) -> None:
    """PRD 5.2.4：每个账号只保留 1 份草稿。"""
    alice = _user(session, "alice")
    session.add(Draft(user_id=alice.id, content_json={"content_md": "第一版"}))
    session.commit()

    session.add(Draft(user_id=alice.id, content_json={"content_md": "第二份"}))
    with pytest.raises(IntegrityError):
        session.commit()


def test_tag_name_is_unique_per_type(session) -> None:
    """05 §5.2 tags 的唯一约束是 (name, type)，不是单 name。"""
    session.add(Tag(name="导数", type="knowledge_point"))
    session.commit()

    session.add(Tag(name="导数", type="custom"))
    session.commit()  # 同名的自定义标签允许

    session.add(Tag(name="导数", type="knowledge_point"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_soft_delete_keeps_the_row(session) -> None:
    owner = _user(session, "alice")
    question = Question(
        user_id=owner.id,
        subject="物理",
        source_type="image",
        content_md="被删的题",
        question_type="solve",
        status="confirmed",
    )
    session.add(question)
    session.commit()

    question.deleted_at = utcnow()
    session.commit()

    assert session.get(Question, question.id) is not None  # 软删除不物理删行
