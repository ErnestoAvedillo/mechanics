**Demo video:** https://youtu.be/cFhAQLos_HY

## Inspiration
Automotive Tier-1 and Tier-2 suppliers spend thousands of engineering hours searching, verifying and cross-referencing OEM specifications (VW, BMW, Ford, JLR, Stellantis, and increasingly BYD, Geely and other Chinese OEMs). The requirements sit in legacy PDFs, often scanned, in several languages and in several editions. Using an outdated edition, or trusting a bad translation, can trigger costly re-tooling. We wanted engineers to ask their own specification library a question and get an answer grounded in the right edition of the right document.

## What it does
Specs is a private, AI-searchable library of engineering standards, part of our engineering web toolbox (spring calculators, tolerance stack-ups, ReqIF viewer).
- **Upload once, index once:** engineers upload PDF standards, scanned ones included. Identical files are detected by hash, so a file is stored and indexed only once, and analysis runs in the background.
- **The AI reads the cover page:** Nemotron proposes the issuer, standard number, title, edition date, language, the editions it replaces and any printed copyright notice. The uploader reviews and confirms these fields before they are used, because they decide which edition replaces which.
- **The right edition, in the right language:** for each user, the most recent edition of a standard is the one searched; older editions stay visible but are marked obsolete. When a standard exists in several languages, the original, which is the language that prevails, is used, and a translation is only used (with an explicit warning) when the original is not in the library.
- **Ask in natural language:** the chat answers in the user's language, searches only the documents the user uploaded, and lists its sources.
- **Agent tools (MCP):** a Model Context Protocol server exposes the library search and a compression-spring calculator, so an agent can retrieve a limit from a standard and calculate a design against it. The agent is instructed never to call a design acceptable unless a limit from a retrieved standard supports it.

## How we built it
- **Models on Nebius Token Factory:** answers come from **NVIDIA Nemotron 3 Super (120B)**; documents and questions are embedded with **Qwen3-Embedding-8B**, both through Nebius's OpenAI-compatible API. Nothing runs locally, so the whole app fits on a small server.
- **Ingestion:** PDFs are stored in MongoDB (GridFS). LlamaParse extracts structured Markdown with OCR, LlamaIndex chunks it, and the vectors (4096 dimensions) go to Qdrant.
- **Metadata:** one Nemotron call at temperature 0 returns JSON that we validate and normalise (issuer aliases such as "Volkswagen AG" to "VW" or "BYD Auto" to "BYD", standard numbers such as `GS90010-1:2023-05` to `GS 90010-1` or Chinese `GB/T 10125—2021` to `GB/T 10125`).
- **Access and versions:** a user's library decides what the chat may search. The resolution of editions and languages is computed per library, not globally, so a document another user uploads can never hide or reveal anything in yours. Nothing is deleted or re-indexed when a newer edition arrives.
- **MCP:** a Python MCP server with three tools (library search, list of spring materials, compression-spring calculation using our `springcalc` library) and a demo agent where Nemotron decides which tool to call.
- **Platform:** Django, PostgreSQL, MongoDB, Qdrant and Nginx in Docker, a bilingual interface (Spanish and English), 82 automated tests, and backup and restore scripts.

## Challenges we ran into
- **Heavy local models:** our first version ran embedding and re-ranking models locally. The Docker image reached 11 GB and the server slowed to a crawl. Moving inference to Nebius Token Factory cut the image to about 2 GB.
- **Scanned PDFs:** most of our test standards have no text layer, so plain text extraction returns nothing. Metadata extraction therefore runs on the OCR output that indexing already produces, at no extra cost.
- **An unstable model:** the same cover page gave different metadata on different runs. Temperature 0 made the results identical across repeated runs, and we kept a human confirmation step because the metadata drives replacement decisions.
- **A silent search bug:** LlamaIndex reserves the `document_id` and `doc_id` payload keys for its own node ids and overwrote ours, so our access filter would have matched nothing. A dry run of our migration exposed it before it touched real data.
- **Translations:** translations often lag behind the original or contain mistakes, and a standard usually states which language prevails. We chose to search the original and treat a translation as a flagged fallback.
- **Copyright and confidentiality:** OEM standards are usually confidential or licensed. We deliberately did not build automatic sharing of documents between users: each user only sees what they uploaded themselves.

## Accomplishments that we're proud of
- A complete pipeline that runs end to end on Nebius with an NVIDIA open model: upload, OCR, metadata, review, versioned search, chat and agent tools.
- Correct handling of real standards: five VW and BMW standards, scanned and digital, German and English.
- A design that never silently hides content and never leaks it between users, backed by tests for edition, language and isolation cases.
- A deployment about five times smaller than our first version.

## What we learned
- In engineering, AI should retrieve and cite, not guess. The agent refuses to judge a design when no limit was found, and says so.
- Version and language rules belong in plain, testable code, not in a prompt. The model proposes the metadata; deterministic rules decide what is searched.
- Real documents are messier than demos: scans, duplicates, translations and models that answer differently each time.

## What's next for Specs
- **Hybrid search** (keyword plus semantic) so exact codes such as TL 226 and TL 262 never get confused, and page-level citations.
- **Cross-OEM comparison:** requirements side by side to design platform-agnostic components.
- **More agent tools:** torsion, extension and conical springs, and tolerance stack-ups, and the MCP tools inside the web chat.
- **Linking translations to originals** explicitly, and change alerts when an OEM publishes a new edition.
- **Agent-to-agent connectors:** a supplier's agent querying an OEM's specification agent over A2A, so requirements can be checked at the RFQ stage.
- **ReqIF integration:** a supplier uploads an OEM's ReqIF file and Specs checks each requirement against the library: it flags the standards a requirement cites that are missing from the library, and suggests which requirements may fall outside the supplier's responsibility, for the engineer to confirm.