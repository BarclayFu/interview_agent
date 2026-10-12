import pytest
from sqlalchemy import select

from interview_agent.core.db import get_session_factory
from interview_agent.core.models import SINGLE_USER_ID, Resume, Session, User

pytestmark = [pytest.mark.integration]


async def test_seed_user_exists():
    async with get_session_factory()() as s:
        assert (await s.get(User, SINGLE_USER_ID)).name == "single-user"


async def test_insert_resume_and_session():
    async with get_session_factory()() as s:
        r = Resume(user_id=SINGLE_USER_ID, raw_text="x", parse_status="pending")
        s.add(r)
        await s.flush()
        sess = Session(user_id=SINGLE_USER_ID, resume_id=r.id)
        s.add(sess)
        await s.commit()
        got = (await s.execute(select(Session).where(Session.id == sess.id))).scalar_one()
        assert got.status == "active" and got.round_type == "project"
