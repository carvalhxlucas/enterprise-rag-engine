# RAG Evals (Continuous Evaluation)

RAG evaluation tests using LLM-as-judge (Ragas). Metrics: Answer Relevance and Faithfulness.

## Running evals only

```bash
cd backend
pip install -r requirements-eval.txt
export OPENAI_API_KEY=sk-...
pytest tests/evals -m evals -v
```

With mocked context (no Qdrant, ideal for CI):

```bash
RAG_EVAL_USE_MOCK_CONTEXT=1 pytest tests/evals -m evals -v
```

## Best practices

### Mocking the vector store

- **Injected context**: Use `RAG_EVAL_USE_MOCK_CONTEXT=1` and fill `reference_contexts` in `fixtures/ground_truth_rag.json`. `ChatOrchestrator.get_answer_for_eval(..., contexts_override=...)` uses that context and does not call Qdrant.
- **Qdrant mock**: For tests that need the real retrieval flow, inject a mock `QdrantClient` into `ChatOrchestrator(qdrant_client=mock_client)`. The mock should implement `search()` returning `ScoredPoint` with `payload` containing `filename`, `page_number`, and `chunk_index` to build snippets.

### API costs in CI

- Use **mocked context** (`RAG_EVAL_USE_MOCK_CONTEXT=1`) in CI: only the judge (Ragas) and answer generation use OpenAI; retrieval does not depend on Qdrant or embeddings.
- Keep the **dataset small** (e.g. 5 examples) to limit calls to GPT-4o-mini.
- Set **OPENAI_API_KEY** as a repository secret; avoid running evals on every push to reduce cost (e.g. only on PRs to `main`).
- To run evals with no API cost on some commits, use a **local model** (e.g. Ollama) by configuring Ragas with local LLM/embeddings; this requires changes in the eval code.
