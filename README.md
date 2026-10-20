# Specs: an AI library for engineering standards

> Built for the **Nebius x NVIDIA Global AI Hackathon**. Runs on **Nebius Token Factory** with the
> **NVIDIA Nemotron 3 Super** open model. Licensed under the [MIT License](LICENSE).

**Demo video:** https://youtu.be/Dp7_NqsXw4w

Specs lets automotive suppliers keep their OEM standards (VW TL, BMW GS, ISO, GB/T...) in a private
library and ask questions about them. It reads scanned PDFs, works out which edition and language of
each standard applies, answers with sources, and exposes the library and a spring calculator to AI
agents through the Model Context Protocol (MCP).

It lives inside a larger personal engineering website (spring calculators, tolerance stack-ups, a ReqIF
viewer), see [The rest of the repository](#the-rest-of-the-repository).

## What it does

- **Upload once, index once.** Identical files are detected by SHA-256, so a file is stored and indexed a single time.
- **Scanned PDFs work.** LlamaParse extracts structured Markdown with OCR, so tables survive.
- **The AI proposes the metadata, you confirm it.** Nemotron reads the cover page and proposes issuer, standard number, title, edition date, language, the editions it replaces and any copyright notice. Only the uploader can review and correct it.
- **The right edition, in the right language, per library.** The newest edition is searched and older ones are marked obsolete; if a standard exists in several languages the original (the one that prevails) is used, and a translation is used only as a flagged fallback. This is computed per user, so what another user uploads never hides or reveals anything in your library.
- **Chat with sources** in Spanish or English, restricted to the documents the user uploaded.
- **MCP tools for agents:** library search, spring material list and a compression-spring calculator.

## How it uses Nebius and NVIDIA

| Need | Model, via Nebius Token Factory (OpenAI-compatible API) |
|---|---|
| Answers and tool calling | `nvidia/nemotron-3-super-120b-a12b` (NVIDIA Nemotron 3 Super) |
| Standard metadata extraction | the same Nemotron model, temperature 0 |
| Embeddings (4096 dimensions) | `Qwen/Qwen3-Embedding-8B` |

Every question and every indexed document makes runtime calls to Token Factory. No model runs locally,
which is what shrank our Docker image from 11 GB to about 2 GB.

Other services: **LlamaParse** (LlamaIndex cloud) parses and OCRs the PDFs, and PostgreSQL, MongoDB and
Qdrant run in the Docker stack.

## Architecture

```
 browser ──> nginx ──> Django ──┬─> PostgreSQL   users, documents, metadata, access
                                ├─> MongoDB      the PDF files (GridFS)
                                ├─> Qdrant       vectors, filtered per user library
                                └─> Nebius Token Factory   Nemotron 3 Super + Qwen3-Embedding-8B
                      LlamaParse (OCR) <── indexing, in a background thread

 MCP server (src/specs/mcp_server.py) ──> same library search + springcalc
```

## Quick start

You need Docker with Compose, a [Nebius Token Factory](https://tokenfactory.nebius.com) API key and a free
[LlamaParse](https://cloud.llamaindex.ai) key.

```bash
git clone https://github.com/ErnestoAvedillo/mechanics.git
cd mechanics
cp .env.example .env
# edit .env: set NEBIUS_API_KEY, LLAMA_CLOUD_API_KEY and replace every CHANGE_ME
docker compose up -d --build
```

The first start takes a few minutes (the `django` container waits for PostgreSQL and runs the migrations;
`docker compose logs -f django` shows the progress). Then open **http://localhost**.

1. **Sign up** (*Create Account*). With `DJANGO_DEBUG=True` the six-digit verification code is printed in the logs instead of being emailed:
   ```bash
   docker compose logs django | grep -iE "verification code|código de verificación"
   ```
2. In the menu choose **Specifications**, then **Upload New PDF**, and upload one or more standards. Indexing runs in the background and takes about a minute per document.
3. Open the document list and click **Metadata to confirm**: review what the AI proposed and confirm it.
4. Click **Go to RAG Chat** and ask a question, for example *"What salt spray test duration does the standard require?"*. The answer lists its sources.

The interface switches between Spanish and English from the header.

## Try the MCP agent

An agent (Nemotron) discovers the MCP tools and decides which to call. Replace `1` with your user id
(the first user you create is `1`):

```bash
docker exec -w /app/src django python -W ignore /app/scripts/mcp_agent_demo.py 1 \
  "Calculate a compression spring: wire 2 mm, mean diameter 16 mm, 8 total coils, free length 60 mm, compressed to 40 mm, material SL. Is the stress acceptable?"
```

It calls `calculate_compression_spring`, then searches your standards for an allowable stress, and refuses
to call the design acceptable if no limit was found. Tools exposed by the server:
`search_specifications`, `list_spring_materials`, `calculate_compression_spring`.

## Tests

```bash
docker exec -w /app/src django python manage.py test specs
```

82 tests cover deduplication, per-user isolation, edition and language resolution, the review screen and
metadata normalisation. The LLM, MongoDB and Qdrant are mocked; only a test database is used.

## What existed before the hackathon and what is new

**Before the hackathon** the repository already held the personal engineering website (spring calculators,
tolerance stack-ups, ReqIF viewer, accounts) and a first RAG prototype of the Specs module (April 2026:
LlamaIndex, Qdrant, LlamaParse, Google Gemini and local Hugging Face models).

**New for the hackathon:**
- Migration to **Nebius Token Factory** with **Nemotron 3 Super** and **Qwen3-Embedding-8B**, replacing Gemini and the local models (image from 11 GB to about 2 GB).
- Documents stored and indexed once, with per-user access (`Document` and `UserDocument` models, hash deduplication, safe deletion).
- AI metadata extraction with a confirmation screen, issuer and standard-number normalisation (including Chinese OEMs and `GB/T` numbers).
- Per-library resolution of editions and languages with the original-language rule and translation warnings.
- The MCP server, the demo agent and the spring-calculation tool.
- Backup and restore scripts, hardened database ports, and 82 automated tests.

## Known limitations

- Documents are never shared between users: each user only sees what they uploaded, because OEM standards are usually confidential or licensed.
- The MCP server serves one fixed user per process and is not wired into the web chat yet.
- LlamaParse is a third-party service; without a key, text-based PDFs still index but scanned ones do not.
- Metadata is proposed by an LLM and must be confirmed by the uploader.
- In production (`DJANGO_DEBUG=False`) sign-up emails need working SMTP credentials.

## The rest of the repository

| Path | Contents |
|---|---|
| `src/specs/` | The Specs module: models, RAG engine, metadata, versions, MCP server, tests |
| `src/muelles/` | Spring calculators (compression, extension, torsion, conical), built on the `springcalc` library |
| `src/tolerances/` | Tolerance and fit analysis |
| `src/reqif/` | ReqIF viewer and editor |
| `src/menuapp/` | Home page, accounts and profile |
| `scripts/` | Backup, restore and the MCP demo agent |
| `config/` | Dockerfiles and nginx configuration |

Useful commands: `make backup` and `make restore DIR=backups/<date>` (data is kept by `make down`;
`make wipe` deletes everything after asking for confirmation).
