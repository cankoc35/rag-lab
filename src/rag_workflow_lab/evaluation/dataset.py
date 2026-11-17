"""Select runtime question fields without passing gold to workflows."""


def select_questions(dataset: dict, question_id: str | None) -> list[dict]:
    """Select one question or all questions, retaining only IDs and raw text."""
    questions = [{"question_id": q["question_id"], "question": q["question"]}
                 for q in dataset["questions"] if question_id is None or q["question_id"] == question_id]
    if not questions:
        raise ValueError(f"No questions selected; unknown question ID: {question_id}.")
    return questions
