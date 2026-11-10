# A.R.T.I.C.

**It never forgets, and every thought leaves a permanent trace.**

A non-ephemeral AI agent whose memory is an Obsidian vault, decoupled from any LLM.

```
 you ─► recall (C++ BM25 + link graph) ─► LLM engine ─► answer
                     ▲                                     │
                     │                                     ▼
              Obsidian vault  ◄── reflect ◄── distil, tag, link, journal
          (Journal / Notes / Hubs / Reflections)
```

## Layout
| Path | Role |
|---|---|
| `core/artic_core.cpp` | C++ indexer: BM25 search, wikilink/backlink graph, orphan detection (C ABI) |
| `artic/core.py` | ctypes bridge; pure-Python fallback if the lib isn't built |
| `artic/vault.py` | Append-only vault writer (notes, journal, hubs). Never overwrites or deletes |
| `artic/llm.py` | Swappable engines: Anthropic, any OpenAI-compatible (Ollama, vLLM...), offline echo |
| `artic/agent.py` | The loop: recall → answer → reflect → remember → link, plus `dream()` consolidation |

## Quick start
```bash
cmake -S . -B build_tmp && cmake --build build_tmp     # builds core/build/libartic_core.*
# or: g++ -O2 -std=c++17 -shared -fPIC core/artic_core.cpp -o core/build/libartic_core.so

export ARTIC_VAULT=~/ArticVault        # open this folder in Obsidian
export ARTIC_ENGINE=anthropic          # or openai (Ollama default) / echo
export ARTIC_API_KEY=...               # and optionally ARTIC_MODEL, ARTIC_BASE_URL
python -m artic chat
python -m artic dream                  # consolidate recent notes into a cross-domain synthesis
python -m artic search "some topic"
```

## The Laws, as implemented
1. **Permanent accumulation**: `Vault` only appends. Existing notes receive dated addenda.
2. **Every thought leaves a trace**: each exchange is journaled verbatim and distilled into a linked note.
3. **Compounding context**: tags auto-feed `Hubs/`, links become `[[wikilinks]]`, `dream()` writes syntheses.
4. **Engine independence**: swap `ARTIC_ENGINE` freely; the vault is the mind.

## Roadmap
- Embeddings (ONNX in C++) alongside BM25 for semantic recall
- Incremental indexing and an mmap'd on-disk index
- Git auto-commit of the vault for a full history
- Scheduled `dream()` and orphan-adoption passes
- Tool use (web, files) with every action logged to the Journal
- Contradiction detection across notes
