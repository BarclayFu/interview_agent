from interview_agent.engine.guards import must_close, must_stop_followup


def test_followup_cap():
    assert not must_stop_followup(2)
    assert must_stop_followup(3)


def test_question_cap():
    assert must_close(8, 8)
    assert not must_close(7, 8)
