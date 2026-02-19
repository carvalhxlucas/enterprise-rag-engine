# RAG Evals (Continuous Evaluation)

Testes de avaliação do RAG com LLM-as-judge (Ragas), métricas: Answer Relevance e Faithfulness.

## Rodar só evals

```bash
cd backend
pip install -r requirements-eval.txt
export OPENAI_API_KEY=sk-...
pytest tests/evals -m evals -v
```

Com contexto mockado (sem Qdrant, ideal para CI):

```bash
RAG_EVAL_USE_MOCK_CONTEXT=1 pytest tests/evals -m evals -v
```

## Boas práticas

### Mockar o banco vetorial

- **Contexto injetado**: Use `RAG_EVAL_USE_MOCK_CONTEXT=1` e preencha `reference_contexts` no `fixtures/ground_truth_rag.json`. O `ChatOrchestrator.get_answer_for_eval(..., contexts_override=...)` usa esse contexto e não chama o Qdrant.
- **Mock do Qdrant**: Para testes que precisem do fluxo real de retrieval, injete um `QdrantClient` mock no `ChatOrchestrator(qdrant_client=mock_client)`. O mock deve implementar `search()` retornando `ScoredPoint` com `payload` contendo `filename`, `page_number`, `chunk_index` para montar os snippets.

### Custos de API em CI

- Use **contexto mock** (`RAG_EVAL_USE_MOCK_CONTEXT=1`) no CI: só o judge (Ragas) e a geração de resposta usam OpenAI; o retrieval não depende de Qdrant nem de embeddings.
- Mantenha o **dataset pequeno** (ex.: 5 exemplos) para limitar chamadas ao GPT-4o-mini.
- Configure **OPENAI_API_KEY** como secret no repositório; evite rodar evals em cada push se quiser reduzir custo (por exemplo, só em PRs para `main`).
- Para rodar evals sem custo em alguns commits, use um **modelo local** (Ollama) configurando o Ragas com LLM/embeddings locais; exige ajuste no código de eval.
