# Prompts

Structured prompt templates kept out of the code so they can be reviewed and
tuned independently. Each file is a plain-text template with `{placeholder}`
fields filled in at call time by `skills/llm_skill.py`.

| File | Filled by | Placeholders |
| --- | --- | --- |
| `draft_answer.txt` | `llm_skill.draft_answer` | `question`, `facts`, `confidence` |
| `draft_summary.txt` | `llm_skill.draft_summary` | `headline`, `drivers`, `confidence` |

The local LLM (Ollama) is optional. When no daemon is reachable the wrapper falls
back to deterministic, template-based text, so these prompts only shape output
when a model is running. The LLM is never a source of truth — every number comes
from governed DuckDB evidence.
