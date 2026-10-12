"""守卫规则：纯函数、非 agent（spec §5.4）。追问深度上限、题量上限。"""

MAX_FOLLOWUPS_PER_QUESTION = 3


def must_stop_followup(followup_depth: int) -> bool:
    return followup_depth >= MAX_FOLLOWUPS_PER_QUESTION


def must_close(question_count: int, max_questions: int) -> bool:
    return question_count >= max_questions
