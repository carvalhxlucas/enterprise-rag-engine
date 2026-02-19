import json
import os
from pathlib import Path

import pytest
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import answer_relevancy, faithfulness

from app.models.schemas import ChatConfig
from app.services.chat import ChatOrchestrator


GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "fixtures" / "ground_truth_rag.json"
MIN_AVERAGE_SCORE = 0.85


def _load_ground_truth():
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        return json.load(f)


def _extract_mean_scores(result):
    repr_dict = getattr(result, "_repr_dict", None)
    if repr_dict:
        f = repr_dict.get("faithfulness")
        a = repr_dict.get("answer_relevancy")
        if f is not None and a is not None:
            return (float(f) + float(a)) / 2.0
        if f is not None:
            return float(f)
        if a is not None:
            return float(a)
    scores = getattr(result, "scores", None)
    if scores and isinstance(scores, list) and scores and isinstance(scores[0], dict):
        f_vals = [s.get("faithfulness") for s in scores if s.get("faithfulness") is not None]
        a_vals = [s.get("answer_relevancy") for s in scores if s.get("answer_relevancy") is not None]
        if f_vals and a_vals:
            return (sum(f_vals) / len(f_vals) + sum(a_vals) / len(a_vals)) / 2.0
    return 0.0


@pytest.mark.evals
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY required for RAG evals (LLM-as-judge)",
)
def test_rag_answer_relevance_and_faithfulness_above_threshold():
    samples = _load_ground_truth()
    orchestrator = ChatOrchestrator()
    config = ChatConfig(temperature=0.0)
    eval_user_id = os.getenv("RAG_EVAL_USER_ID", "eval-test-user")

    use_mock_context = os.getenv("RAG_EVAL_USE_MOCK_CONTEXT", "").lower() in ("1", "true", "yes")
    eval_samples = []
    for item in samples:
        question = item["question"]
        ground_truth = item["ground_truth"]
        contexts_override = item.get("reference_contexts") if use_mock_context else None
        if contexts_override is not None and isinstance(contexts_override, str):
            contexts_override = [contexts_override]
        answer, contexts = orchestrator.get_answer_for_eval(
            eval_user_id, question, config, contexts_override=contexts_override
        )
        if not contexts:
            contexts = [""]
        eval_samples.append(
            SingleTurnSample(
                user_input=question,
                retrieved_contexts=contexts,
                response=answer,
                reference=ground_truth,
            )
        )

    dataset = EvaluationDataset(samples=eval_samples)
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
    )

    average = _extract_mean_scores(result)
    assert average >= MIN_AVERAGE_SCORE, (
        f"RAG eval average score {average:.3f} is below threshold {MIN_AVERAGE_SCORE}. "
        f"Result: {result}"
    )
