# PROJECT_HANDOFF.md — OctoBot (Pharos Network Hub)

> Handoff between Claude instances. Written after a long session that redesigned the
> **Memory Ledger** page, migrated the RAG embedder to a Gemini API, fixed startup
> performance, added a hero banner, animated the live-updates thumbnails, and fixed a
> global page-navigation "ghosting" bug.
>
> **Legend used throughout:** `FACT` = confirmed in code/files · `DECISION` = agreed in
> conversation · `PLAN` = intended, not done · `IDEA` = merely discussed · `UNKNOWN` =
> not verifiable.

---

## 1. PROJECT IDENTITY

- **What it is** (`FACT`): "OctoBot · Pharos Network Hub" — a single-page **Streamlit**
  web app that is a multi-section hub for the Pharos blockchain network: an AI docs
  chatbot, live price/news/X feed, campaigns, DeFi tools, a wallet/transaction
  intelligence dashboard ("Memory Ledger"), a payment/request agent, network stats, and
  more.
- **Purpose/goals** (`FACT`/`DECISION`): give Pharos users one place to ask questions
  (RAG chatbot), read live ecosystem updates, and inspect wallets/transactions with
  AI-synthesized intelligence — read-only, "nothing ever signed or spent."
- **Architecture** (`FACT`):
  - Single giant file `app.py` (**~16,135 lines / ~780 KB**) containing ALL pages.
  - Router pattern: `st.session_state.page` selects the active page via a long
    `if page == "home": … elif page == "chat": …` chain. Pages: `home`, `chat`, `defi`,
    `campaigns`, `updates`, `trade`, `ecosystem`, `pay`, `request`, `chronos`, `network`,
    `spns`, `pulse`, `memory` (Memory Ledger).
  - Streamlit re-executes the **entire** file top-to-bottom on every rerun (every nav
    click / widget interaction). All top-level CSS (`st.markdown("<style>…")`) and several
    `components.html(...)` parent-document bootstraps run each rerun.
  - A custom light/dark theme layered on top of Streamlit via `html[data-theme="dark"]`
    CSS, toggled from the nav.
- **Main tech** (`FACT`): Streamlit **1.58.0**, Python **3.14** (venv), `langchain` +
  `langchain-google-genai` + `langchain-chroma`, ChromaDB **1.5.9**, `plotly`, `pandas`,
  `requests`, `beautifulsoup4/lxml` (crawler), `web3` (used somewhere for on-chain reads).
  Google **Gemini** for both LLM (`gemini-2.5-flash`) and embeddings
  (`models/gemini-embedding-001`).
- **Repo structure** (`FACT`, key files only):
  - `app.py` — the entire app (all pages, CSS, helpers, router).
  - `octobot.py` — RAG engine (embeddings + Chroma + Gemini LLM), class `OctoBot`.
  - `build_vectorstore.py` — build the vector store from `raw_docs/*.txt`.
  - `rebuild_vectorstore_gemini.py` — **one-off migration** script (re-embed existing
    Chroma chunks with the Gemini API into `chroma_gemini/`).
  - `crawl_docs.py` — docs crawler (produces `raw_docs/`).
  - `skill_api.py`, `octobot.py __main__` — standalone/terminal usage.
  - `chroma_gemini/` — **ACTIVE knowledge base** (729 chunks, Gemini embeddings, ~17 MB).
  - `chroma_db/` — **OLD backup** knowledge base (HuggingFace embeddings, ~8.8 MB). No
    longer used by the app; kept for rollback safety (`DECISION`).
  - `.streamlit/config.toml` — perf config (see §13).
  - `.claude/launch.json` — dev-server launch config (`octobot-streamlit`, port 8502).
  - `requirements.txt` — dependency list (slimmed; see §2).
  - `.env` — local secrets (only `GEMINI_API_KEY` present, `FACT`).
  - `README.md`, `Readme2.md` — pre-existing docs (not the source of truth; `UNKNOWN`
    how current).
  - `raw_docs/` — **EMPTY** (`FACT`). The source docs are NOT present; the doc *text*
    lives only inside `chroma_db`/`chroma_gemini`. This matters for any future rebuild.
  - Images: `pharos_logo.jpg`, `Chat_logo.jpg` (1.4 MB), `loading.jpg`.
  - `app.py.bak`, `requirements.txt.bak`, `rebuild.log` — junk backups (safe to delete).
- **Deployment/setup** (`FACT`): hosted on **Streamlit Community Cloud**. User's workflow:
  edit in VS Code → `git push` → open the Streamlit host → **Reboot app**. Local dev via
  the dev server on port 8502.
- **External services** (`FACT`): Google Gemini API (LLM + embeddings, key
  `GEMINI_API_KEY`); CoinGecko (PROS price + news, no key); X/Twitter feed (X API v2 if
  `X_BEARER_TOKEN`/`TWITTER_BEARER_TOKEN` present, else Nitter RSS fallback, else a
  hardcoded `_PHAROS_X_FALLBACK`); Pharos RPC (`PHAROS_RPC_URL`, default fallback used) for
  wallet/tx reads and network stats; PharosScan explorer (`PHAROS_EXPLORER_URL =
  https://pharosscan.xyz`).
- **Env/config requirements** (`FACT`):
  - `GEMINI_API_KEY` — REQUIRED. Local: `.env`. Cloud: **Streamlit Secrets** (Settings →
    Secrets, TOML `GEMINI_API_KEY = "…"`). Streamlit Cloud exposes secrets as env vars, and
    `octobot.py` reads via `os.getenv("GEMINI_API_KEY")` + `load_dotenv()`.
  - Optional: `X_BEARER_TOKEN`/`TWITTER_BEARER_TOKEN`, `PHAROS_RPC_URL`,
    `X402_PAYTO_ADDRESS` (default wallet `0x3111e7e7c8141c0496db20bf90528577c5e1f0f4`).
- **Assumptions the project depends on** (`FACT`/`DECISION`):
  - `chroma_gemini/` **must be committed to the repo** — Streamlit Cloud has no other copy
    of the knowledge base. Same for `.streamlit/config.toml`.
  - The Gemini key used for embeddings/LLM must have **billing enabled** for real multi-user
    use (free tier = 20 `gemini-2.5-flash` requests/day — see §6).
  - Query-time embeddings now hit the Gemini API (1 call per chat question).

---

## 2. COMPLETE DEVELOPMENT HISTORY (this session)

Ordered roughly chronologically. Older decisions preserved even where superseded.

1. **Installed Emil Kowalski design skills** (`emilkowalski/skills` via `npx skills add`) —
   design-engineering skills used as the taste reference for later UI work. (`FACT`)

2. **Memory Ledger full redesign** (`app.py`, `page == "memory"`) — replaced a cluttered
   floating-glass layout with a flat, structured SaaS dashboard (Linear/Stripe/Vercel
   direction). Introduced a token set `--ml-*` (surface/border/text/accent/ok/warn/bad +
   shadows), theme-aware. Structure: compact header → 4 KPI cards → **segmented control**
   (Wallet Profiles | Transaction Intelligence) → single search/sort toolbar → structured
   rows → detail. (`FACT`, complete)

3. **Wallet Intelligence & Transaction Intelligence reports** — the wallet "View profile"
   opens a full inline report (identity → Overview metric strip → Key Insights → OctoBot
   intelligence prose → Evidence timeline → At-a-glance rail). Transactions open a
   `st.dialog` drawer (What happened → Transfer flow FROM→amount→TO → Details grid → How it
   executed steps → Risk signal). **Persisted real tx fields** (`from/to/value/gas/block/
   method/input_data`) into the memory entry so the transfer flow/details render from real
   data (not example values). (`FACT`, complete)

4. **Auto-open reports** — after analyzing a wallet, the report opens automatically
   (`ml_wallet_detail` set before rerun). After explaining a tx, the drawer auto-opens via a
   one-shot `ml_tx_autoopen` flag (`pop`-ed and passed to `_tx_drawer`). (`FACT`, complete)

5. **Light/dark fixes** (several, `FACT`, complete):
   - Input text invisible in light mode: the global `rd-marker` CSS forced input text near
     white; re-pointed input surface + text to `--ml-*` tokens and themed the field.
   - Segmented control showed Streamlit's default red (`#FF4B4B`); restyled the
     `stButtonGroup` / `stBaseButton-segmented_controlActive` to the brand accent.
   - **Dialog theming (portal)**: `st.dialog` renders in a modal **portal outside**
     `stMainBlockContainer`, so container-scoped `--ml-*` tokens never reached it → "some
     black, some white" in light mode. **Fix: moved `--ml-*` token definitions to `:root`
     (light) and `html[data-theme="dark"]` (dark)**, and retinted the modal panel
     (`[data-testid="stDialog"] [role="dialog"]`), title, close button, expander, and
     `st.code` via tokens.

6. **Streamlit 1.58 container quirk (KEY LEARNING)**: `st.container(border=True)` renders as
   a **bordered `stVerticalBlock`**, NOT `stVerticalBlockBorderWrapper` (which does not exist
   in 1.58). So the old flat-card CSS matched nothing and cards were transparent → looked
   cramped. **Fix pattern:** put a hidden marker span (`.ml-cardmark`, `.ml-txcard`,
   `.ml-heromark`) as the first child, hide its element container, and style the parent via
   `[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .marker)`.
   Stable across emotion-hash changes. (`FACT`)

7. **Connected-wallet section** rebuilt as a self-styled `.ml-conn-panel` (not a Streamlit
   container, to guarantee padding), with actions on a separate row, more spacing.

8. **Transaction list row** redesigned to a 2-line card (identity + action | amount + status
   | Inspect · then hairline + AI summary + timestamp), vertically centered columns.

9. **PERFORMANCE work** (`FACT`, complete):
   - **Non-blocking PROS price**: `get_pros_price()` refactored to a process-wide holder +
     background daemon; render thread never blocks on CoinGecko (was up to ~9s first-paint
     stall).
   - **Cached `get_logo_b64()`** (was re-encoding an image every rerun).
   - **Warm the retriever at boot** (one `retriever.invoke("pharos")` on the octobot worker
     thread so the first chat query isn't first-inference-slow).
   - **`.streamlit/config.toml`**: `gatherUsageStats=false`, `headless=true`, and
     **`fileWatcherType = "none"`** — the watcher was walking the `transformers` package on
     every scan (~54 KB of import errors + CPU). Big startup win.

10. **RAG embedder migration (LLM answers unchanged; only the *search* embedder changed)**
    (`FACT`, complete):
    - **Was**: local HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (pulls in
      torch+transformers ~1 GB → slow boot, high memory).
    - **Now**: Google API `models/gemini-embedding-001` (3072-dim). No local ML stack.
    - Only `gemini-embedding-001` works with the user's key/API version (`text-embedding-004`
      and `embedding-001` returned 404).
    - Because dimensions differ, a **fresh store** was required. `rebuild_vectorstore_gemini.py`
      read the 729 chunk texts+metadata out of `chroma_db`, re-embedded with Gemini (paced to
      respect the ~100/min free rate limit; resumable), and wrote **`chroma_gemini/`**.
    - `octobot.py` now points `CHROMA_DB_DIR = "chroma_gemini"`, `EMBEDDING_MODEL =
      "models/gemini-embedding-001"`, and `_get_embeddings` returns
      `GoogleGenerativeAIEmbeddings`. `build_vectorstore.py` updated to match.
    - **`requirements.txt` slimmed**: removed `torch, transformers, sentence-transformers,
      langchain-huggingface, safetensors, tokenizers, huggingface_hub, hf-xet`; collapsed
      duplicates (194→159 lines); rewritten as clean UTF-8 (was UTF-16). Backup:
      `requirements.txt.bak`.
    - **Verified**: retrieval returns correct docs; chat opens instantly with no "Loading
      Knowledge Base". The final *answer text* could not be tested because the LLM daily quota
      (20/day) was exhausted — that's a billing matter, not a migration bug.

11. **Hero banner** for Memory Ledger (`page == "memory"` header): replaced the plain text
    header with a self-contained **dark-indigo glass hero** (`.ml-heromark` marker) — eyebrow,
    gradient "Memory Ledger" wordmark (white→lilac→purple text-clip), subtitle, glass action
    pills (Ask OctoBot + Explorer, same behavior/keys), and a right-side **3D glass "ledger"**
    visual (tilted card with page-stack depth, OctoBot octopus 🐙, "MEMORY LEDGER" label, 4
    floating cubes, glow ring, gentle float + reduced-motion guard). Then **slimmed twice** on
    request (smaller padding/title/visual). (`FACT`, complete)

12. **Live-updates thumbnail motion** (`page == "updates"`, `.updc-*`): added GPU-only motion
    so feed thumbnails "feel alive" — pulsing halo behind the logo, slow diagonal light sweep,
    drifting dot field, floating logo; hover adds a subtle 3D `perspective rotateX` tilt +
    energized (faster) halo/sweep; staggered per-card; full `prefers-reduced-motion` guard.
    (`FACT`, complete) NOTE: the automated preview browser reports `prefers-reduced-motion:
    reduce`, so motion appears OFF there but plays on normal machines.

13. **Global navigation "ghosting" fix** — the **current/last task** (`FACT`, complete &
    verified): see §10.

Rejected/superseded approaches (preserved):
- **Removing the 3D ambient background** on the Memory page (in the very first brief) was
  implemented, then **reversed** — the user later said the global background must stay in both
  modes. See the contradiction note in §7.
- Aggressive per-rerun **component-guarding** of the nav/background/overlay `components.html`
  blocks was considered for perf and **rejected** as high-risk/low-reward after the price fix.
- Wallet detail via `st.dialog` drawer was considered; wallets use the **inline** detail view,
  transactions use the dialog drawer.
- For the nav ghost, a two-phase "loading splash then render" and CSS stale-hiding were
  considered and **rejected** (spec forbade masking); the chosen fix is non-blocking fetch.

---

## 3. CURRENT STATE

### Working (`FACT`)
- Memory Ledger: hero banner, KPI row, segmented tabs, search/sort, wallet rows, wallet
  intelligence report (auto-opens), transaction intelligence drawer (auto-opens), empty
  states, connected-wallet panel — all render in **light and dark**.
- RAG search on `chroma_gemini` (Gemini embeddings) — retrieval verified correct.
- Chat page opens instantly (background octobot init + warm retriever), no loading hang.
- Non-blocking PROS price; non-blocking live X feed + news (ghost fix).
- Updates page renders the live feed with animated thumbnails.
- Startup is clean (no transformers-walk errors).

### Partially Working (`FACT`)
- **Chat answers**: retrieval + UI work, but AI *answer generation* fails when the Gemini
  **free-tier 20/day** LLM quota is spent (429). Needs billing. Not a code bug.
- **Live feeds cold-start**: `get_pharos_x_posts()` falls back to `_PHAROS_X_FALLBACK` content
  while the real feed loads (warmed at boot by the prewarm). Acceptable; the real data appears
  on the next rerun.

### Broken (`FACT`)
- None known in the code as of this handoff. (The only "failure" is the external LLM quota.)

### Pending (`PLAN`)
- **Deploy the latest working tree**: commit `app.py` (+ `chroma_gemini/`, `.streamlit/`,
  `requirements.txt`, `rebuild_vectorstore_gemini.py`) and Reboot on Streamlit Cloud. The last
  git commit `82a3ce0 "OctoBot v2.0…"` predates the hero banner, thumbnail motion, and nav fix
  — those are **uncommitted working changes**.
- **Enable Gemini API billing** (user action) so chat works for multiple users.
- Optionally route **Pulse (market/AI) and Network (net_stats)** fetchers through the shared
  `live_fetch()` helper too (they still use synchronous `session_state` caches and could ghost
  on their transitions). Offered; user hasn't confirmed.

### Future Ideas (`IDEA`)
- Keep-alive pinger (e.g. UptimeRobot) so the Streamlit free app doesn't sleep → faster for
  visitors.
- A "raw snippets, no-LLM" chat mode (mentioned, not wanted now).
- Lighter host / paid tier for more memory + no sleep.

---

## 4. UI/UX AND DESIGN SYSTEM

**Overall visual direction** (`DECISION`): clean, structured, premium, **analytical
SaaS/blockchain-analytics** — Linear + Stripe + Vercel + modern financial dashboards. The data
is the focus. Information-dense but not cluttered.

**Layout philosophy** (`DECISION`): flat/lightly-elevated cards, subtle borders, clear
vertical rhythm, whitespace and typography to establish hierarchy (not just color). Sections
separated by hairline dividers + spacing, not heavy boxes.

**Tokens / theme system** (`FACT`):
- Memory-page component tokens `--ml-*` defined at **`:root`** (light) and
  `html[data-theme="dark"]` (dark) so they reach portaled dialogs. Light: surface `#FFFFFF`,
  surface2 `#F7F8FB`, inset `#F2F4F8`, border `#E6E8F0`, t1 `#0C1322`, t2 `#48526A`, t3
  `#6B7488`, accent `#1A1AFF`, ok `#1E9E54`, warn `#B07A00`, bad `#D64550`. Dark: surface
  `#141824`, t1 `#EDEFF7`, border `#242A38`, accent `#6E86FF`, etc.
- App-global tokens `--bg1/--bg2/--border/--t1..t3/--blue/--green/--fd/--fb/--rad*` also exist
  (older system); light global bg is a muddy slate `#9DAABF`, dark `#0B0E1A`.
- Fonts: **Syne** (display/titles), **Inter / DM Sans** (UI/body), **DM Mono** (addresses/
  hashes). `--fd = Syne`, `--fb = DM Sans`.

**Buttons**: 40–44px min height; brand-accent selected states; hero uses outlined **glass
pills**; Streamlit `primary` is the default red — avoid relying on it, style explicitly.
**Cards**: 10–12px radius, `--ml-surface`, `1px --ml-border`, soft `--ml-shadow`; hover lifts
border/shadow. **Badges**: small uppercase pills with semantic soft backgrounds (ok/warn/bad/
neutral/accent). **Navigation**: segmented control styled as Linear-style tabs (accent-fill
selected). **Header/banner**: dark-glass hero (see §5 Memory Ledger). **Background**: keep the
app's **soft blue/purple perspective-grid ambient** (a canvas `#aura-3d-canvas` injected into
the parent doc) — see contradiction note in §7.

**Animations/transitions** (`DECISION`, Emil-style): restrained, purposeful, **GPU-only**
(transform/opacity/background-position). Durations ~150–300ms UI, custom ease-out curves.
Everything must respect `prefers-reduced-motion`. Hover states subtle. Live-feed thumbnails
have gentle ambient motion (halo pulse, light sweep, drift, float) + a subtle 3D hover tilt.

**Icons/logos**: emojis are used throughout as lightweight glyphs (🧠 🔑 🧾 🐙 etc.) — the app
is emoji-tolerant despite the generic "no emoji icons" guideline; keep consistent with existing
usage. OctoBot brand = an octopus 🐙.

**Dark mode / light mode**: both must be intentional (not inverted). Verified across Memory
Ledger, dialog, hero, rows. `st.code`, expanders, and the dialog modal are token-themed.

**Responsive**: desktop-first; hero visual hides < 820px; `--ml-dl` grids collapse to 1 col <
680px; columns stack on narrow. Mobile should stack intelligently, not squeeze.

**Loading / empty / error states**: prefer a page-owned loading state over a global overlay
that masks. Empty states are proper components ("No wallet profiles yet", "No transactions
explained yet"). Errors surfaced inline (e.g. RPC unreachable warning), never a blank page.

**Things the user LIKES** (`DECISION`): the flat structured SaaS look; the Wallet/Transaction
intelligence report structure; the slim hero banner; the glass pills; the live-feed motion;
consistent tokens; clean spacing.

**Things the user DISLIKES / rejected** (`DECISION` — treat as constraints):
- "too many floating translucent cards", overly glassy, glassmorphism overload.
- an **overly dominant 3D background** that washes out content (original complaint) — BUT
  later the user reversed and wants the ambient background **kept** (contradiction; latest
  wins — see §7).
- neon, glowing borders, excessive gradients, too many pills/badges, random icons/logos,
  huge text blocks, oversized/gimmicky animations, generic crypto-dashboard styling, clutter.
- cramped spacing / elements touching or overlapping (called out repeatedly).
- text invisible in light mode (an actual bug, fixed).
- the banner being too tall/bulky (wanted it slimmer, twice).

---

## 5. PAGE-BY-PAGE STATE

> Only pages we actually worked on are detailed. Others exist and were not touched.

### Memory Ledger (`page == "memory"`) — MOST WORKED ON
- **Purpose**: read-only wallet + transaction intelligence, "organized by wallet and
  transaction." Two views via a segmented control.
- **Design**: dark-glass **hero banner** (`.ml-heromark`) → **KPI row** (4 `.ml-kpi` cards:
  Total memories / Wallet profiles / Transactions / Last updated) → **segmented control**
  (Wallet Profiles | Transaction Intelligence) → per-view toolbar → structured rows → detail.
- **Wallet Profiles view**: connected-wallet panel (or "Profile a wallet" input) → search/sort
  → wallet cards (identity + metrics + summary + tags + actions: **Open report** / Ask OctoBot
  / Remove). **Open report** → inline **Wallet Intelligence report** (auto-opens after a fresh
  analysis via `ml_wallet_detail`). Report sections: identity (copyable address via `st.code`),
  Overview metric strip, Key Insights (semantic-barred findings), OctoBot intelligence
  (paragraphs + "Next step" callout, `_prose_section` folds long text into an expander),
  Evidence timeline (explained tx memories), At-a-glance rail (risk/balance/txns/tags) + Ask
  OctoBot / Remove.
- **Transaction Intelligence view**: "Explain a transaction" input → transaction list (2-line
  cards) → **Inspect** opens a `st.dialog` **Transaction Intelligence** report (auto-opens
  after a fresh explain via `ml_tx_autoopen`). Sections: identity (copyable hash), What
  happened, Transfer flow FROM→amount→TO, Transaction details grid (only available fields), How
  it executed steps, Risk signal (on failure), Raw details expander.
- **Data source**: `fetch_pharos_onchain_data(addr)` (RPC: balance/tx_count/is_contract — NO
  per-tx list), `synthesize_wallet_profile()` (Gemini), `fetch_pharos_transaction(hash)`,
  `explain_transaction()` (Gemini). Memories persist in `st.session_state.memory_entries`
  (per session; `mem_upsert`/`mem_remove`).
- **Constraints**: RPC gives no per-wallet tx list → the wallet report does NOT fabricate a tx
  table; it shows explained-tx memories instead. Keep this honest.
- **Known caveat**: session resets to Home on Streamlit websocket reconnect (testing
  annoyance, not a bug).

### Updates (`page == "updates"`) — live feed + thumbnail motion + ghost fix
- **Purpose**: live feed of @pharos_network posts (+ news elsewhere). "Refreshes
  automatically."
- **Data source**: `get_pharos_x_posts()` → now **non-blocking** `live_fetch("xposts", …)`
  (X API v2 → Nitter RSS → `_PHAROS_X_FALLBACK`). `get_pharos_news()` → `live_fetch("news", …)`
  (CoinGecko news).
- **Design**: `.updc-card-v2` feed cards with a blue-gradient **thumbnail** (`.updc-logo-tile`)
  showing the logo; category badge + relative time + title + "View on X". Thumbnails have
  **ambient motion** (halo pulse, light sweep, drifting dots, floating logo) + **3D hover
  tilt**; reduced-motion safe.
- **Refresh feed** button now calls `live_invalidate("xposts")`.

### Chat (`page == "chat"`) — RAG chatbot
- **Purpose**: answer Pharos questions from docs (Docs-only) or general (Gemini fallback).
- **Flow**: embed question (Gemini) → search `chroma_gemini` → `gemini-2.5-flash` writes the
  answer. Background init at app startup (`load_octobot(start=True)`, daemon thread, single-
  flight, cached singletons), so Chat opens ready.
- **Constraint**: Docs-only still needs the LLM to *write* the answer → subject to the 20/day
  free quota.

### Others (Home, DeFi, Campaigns, Trade, Ecosystem, Pay, Request, Network, SPNs, Chronos,
Pulse) — exist, largely untouched this session. Home shows the live `$PROS` price (now
non-blocking) and feature cards (Memory Ledger, Payment Agent). Pulse/Network fetch live data
via synchronous `session_state` caches (candidate for `live_fetch` if they ghost).

---

## 6. BUGS AND ISSUES (tracker)

1. **Cross-page "ghosting" / previous page bleed-through** — STATUS: **FIXED & verified**.
   - Symptoms: navigating to a live-data page (e.g. Memory Ledger → Updates) left the previous
     page faintly visible under the new one while data loaded.
   - Cause: live fetchers (`get_pharos_x_posts`, `get_pharos_news`) blocked the render run on
     the network; Streamlit shows the previous run's elements (stale) until the run finishes.
     Prewarm couldn't help (thread had no `ScriptRunContext`, couldn't write `session_state`).
   - Fix: shared **`live_fetch()`** (process-wide holder + background daemon, warmed at boot);
     render never blocks → old page unmounted. Verified: 0 lingering elements after
     Updates→Memory.
   - Did NOT do (rejected): CSS stale-hiding, extra overlay, opacity/z-index, sleeps.
   - Next investigation if it recurs elsewhere: route that page's fetcher through `live_fetch`.

2. **Input text invisible in light mode (Memory Ledger)** — FIXED. Global `rd` CSS forced
   input text near-white; re-pointed to `--ml-*` tokens.

3. **Segmented control was Streamlit red** — FIXED. Styled `stButtonGroup` /
   `stBaseButton-segmented_controlActive` to accent; note base-button specificity beat the
   active rule at first (had to raise the active selector's specificity).

4. **Transaction dialog unthemed in light mode** — FIXED. `st.dialog` is portaled outside
   `stMainBlockContainer`; moved `--ml-*` tokens to `:root` + themed the modal panel/chrome.

5. **Cards transparent / cramped** — FIXED. `st.container(border=True)` = bordered
   `stVerticalBlock` in 1.58 (no `stVerticalBlockBorderWrapper`); used the marker technique.

6. **Slow first paint / slow startup** — FIXED. Non-blocking price; `fileWatcherType="none"`
   (transformers-walk); cached logo; API embeddings dropped ~1 GB torch/transformers.

7. **Chat "quota exceeded" (429)** — EXTERNAL, not a code bug. `gemini-2.5-flash` free tier =
   20 generate_content/day. Fix = enable Gemini API billing. Embeddings also rate-limited
   (~100/min free) — only relevant for the one-off rebuild, fine for per-query.

8. **`text-embedding-004` / `embedding-001` return 404** for this key — only
   `gemini-embedding-001` works. Don't switch embedding models without re-testing + rebuilding
   `chroma_gemini`.

Known limitations: `raw_docs/` is empty → a from-source rebuild isn't possible; rebuild only
from the existing Chroma chunks (as `rebuild_vectorstore_gemini.py` does).

---

## 7. IMPORTANT USER REQUIREMENTS

### Hard Requirements (must not violate)
- **Never fabricate on-chain data.** RPC gives no per-wallet tx list → don't invent one.
- **Preserve existing functionality** when redesigning; keep buttons' keys/behavior (e.g.
  `mlcta_header_ask`, Explorer link, Analyze, Inspect, Refresh feed).
- **Commit `chroma_gemini/` and `.streamlit/config.toml`** for deploys — the app breaks
  without them on Cloud.
- **Fix root causes, not symptoms** — the user explicitly forbade masking the nav-ghost bug
  with overlays/opacity/z-index/`display:none`/sleeps.
- **Both light and dark mode must be correct** (test both; don't infer one from the other).
- **Respect `prefers-reduced-motion`** for all animations.
- Marketing/social copy must be written to **X guidelines** (no engagement bait, minimal
  hashtags/emojis, authentic voice) — the user was shadow-banned and is cautious.

### Strong Preferences
- Slim, clean, premium, intentional design (Linear/Stripe/Vercel/analytics vibe).
- Restrained motion; subtle hover; whitespace + typography for hierarchy.
- Keep the app's soft blue/purple perspective-grid ambient background and palette.
- Deploy workflow: VS Code → `git push` → Reboot on Streamlit host. (`git add .` after adding
  `*.bak`, `rebuild.log`, `.claude/` to `.gitignore` is fine.)

### Things the user Dislikes / Avoid
- Floating translucent cards / glassmorphism overload; neon; glowing borders; excessive
  gradients; too many pills/badges; random icons; huge text blocks; oversized/gimmicky
  animations; generic crypto-dashboard styling; clutter; cramped/overlapping elements.
- Banners that are too tall/bulky.

### ⚠️ CONTRADICTION TO RESOLVE THE RIGHT WAY (`DECISION`, latest wins)
- Early: "**Remove** the dominant 3D perspective-grid background" on the Memory page (it washed
  out content) — this was implemented (canvas hidden on that page).
- Later: "the global background **should be there** in both light and dark modes" — this
  **reversed** the earlier removal. **CURRENT/LATEST decision = KEEP the global ambient
  background visible on all pages, in both themes.** The Memory page canvas-hide + flat-bg
  override were removed; cards are opaque and elevated so they read cleanly over the ambient.
  Do not re-hide the background.

---

## 8. ARCHITECTURE AND CODE CONTEXT

- **State**: `st.session_state` for page routing, memory entries, per-session caches. Process-
  wide singletons via `@st.cache_resource` (embeddings, vectorstore, Gemini client, HTTP
  session, holders).
- **RAG data flow**: `load_octobot(start=True)` (module top-level) → daemon `_octobot_worker`
  → `octobot.OctoBot(price_fetcher=get_pros_price)` → `get_shared_resources()` builds/reuses
  `GoogleGenerativeAIEmbeddings` + `Chroma("chroma_gemini")` + retriever + `ChatGoogleGenerativeAI`
  → warms retriever. Chat page waits briefly (`octobot_wait`) if not ready (usually instant).
- **Live-data flow (NEW, important)**: `live_fetch(key, pure_fetch_fn, ttl, default)` in
  `app.py` (~line 590+). Returns `(value, is_loading)` instantly; a daemon writes a process-
  wide `_live_holder(key)` dict `{data, at, fetching, lock}`. `live_invalidate(key)` forces a
  refresh. Pure fetchers: `_fetch_pharos_news_raw`, `_fetch_pharos_x_raw`, `_fetch_pros_price_raw`
  (all NO `st.*`/session access — thread-safe). `_prewarm_worker` warms news/xposts/price
  holders at startup. `get_pharos_x_posts()` mirrors `{items, live, loading}` into
  `st.session_state["pharos_x_cache"]` for the Updates page's existing reader.
- **Theme system**: custom `html[data-theme="dark"]` CSS + `--ml-*` tokens at `:root`. A JS
  theme toggle in the nav. `inject_redesign_css("memory rd-wide")` marks the memory page.
- **The marker technique** (reusable): `.ml-cardmark` (wallet rows + input containers),
  `.ml-txcard` (tx rows), `.ml-heromark` (hero) — each is a hidden span whose element container
  is `display:none`, used with `:has()` to style the specific `stVerticalBlock`.
- **Reusable helpers**: `_get_http_session()` (cached, retry), `_get_gemini_client()`,
  `esc()/esc_url()/valid_addr()/valid_txhash()`, `mem_relative_time()`, `_risk_badge()`,
  `_prose_section()`, `_wallet_insights()`.
- **Technical debt**: single 16k-line `app.py`; UTF-16 was used for `requirements.txt`
  (now UTF-8); heavy per-rerun CSS/components.html; `chroma_db` old backup still committed;
  Pulse/Network still use blocking `session_state` fetchers.

---

## 9. RECENT CHANGES (chronological; newest last)

Session date context: work done ~2026-08-16/17. `ORDER → CHANGE → FILE → STATUS`

1. Memory Ledger full redesign → `app.py` (memory page + `--ml-*` CSS) → DONE
2. Wallet/Transaction intelligence reports + persist tx fields → `app.py` → DONE
3. Auto-open reports (`ml_wallet_detail`, `ml_tx_autoopen`) → `app.py` → DONE
4. Light/dark fixes (inputs, segmented control, dialog `:root` tokens) → `app.py` → DONE
5. Marker technique for card surfaces (`.ml-cardmark`/`.ml-txcard`) → `app.py` → DONE
6. Connected-wallet panel + tx-row redesign + spacing passes → `app.py` → DONE
7. Non-blocking price + cached logo + warm retriever → `app.py` → DONE
8. `.streamlit/config.toml` (`fileWatcherType="none"`, headless, no telemetry) → NEW FILE → DONE
9. RAG → Gemini embeddings migration + `chroma_gemini/` rebuild + slim `requirements.txt`
   → `octobot.py`, `build_vectorstore.py`, `rebuild_vectorstore_gemini.py`, `requirements.txt`,
   `chroma_gemini/` → DONE
10. Hero banner (then slimmed x2) → `app.py` (memory hero CSS + markup) → DONE
11. Live-updates thumbnail motion + 3D hover → `app.py` (`.updc-*` CSS) → DONE
12. **Global nav ghost fix** (`live_fetch`, convert news + xposts, warm holders, refresh
    buttons) → `app.py` → DONE & verified
13. `PROJECT_HANDOFF.md` created → NEW FILE → DONE (this file)

Git: last commit `82a3ce0 "OctoBot v2.0: redesigned Memory Ledger, API embeddings, faster
startup"`. Items 10–12 are **uncommitted** working-tree changes on top of it (plus this file).

---

## 10. CURRENT TASK / WHAT WE WERE WORKING ON

**Immediately before this handoff:** the **global navigation "ghosting" fix** (§6 item 1).

- **User asked**: fix a global bug where navigating to a live-data page left the previous page
  visible underneath while data loaded; fix the real lifecycle (no masking), globally.
- **What was changed**: added `live_fetch()` + `_live_holder()` + `live_invalidate()`;
  extracted pure fetchers (`_fetch_pharos_news_raw`, `_fetch_pharos_x_raw`); converted
  `get_pharos_news()` and `get_pharos_x_posts()` to non-blocking; updated `_prewarm_worker` to
  warm the holders; updated the two "Refresh feed" buttons to invalidate holders.
- **Verified**: Updates renders instantly; after Updates→Memory the DOM has **0** lingering
  Updates elements. No errors on boot.
- **What remains / next logical step**:
  1. **Deploy**: `git add .` (ensure `chroma_gemini/`, `.streamlit/`, and the modified `app.py`
     go up) → commit → push → Reboot on Streamlit Cloud.
  2. **Enable Gemini API billing** (user) so chat answers work.
  3. **Optional**: convert Pulse (`pulse_market_cache`/`pulse_ai_cache`) and Network
     (`net_stats_cache`) fetchers to `live_fetch()` for uniform global coverage. User was
     offered this and hasn't confirmed — ask or do it if the same ghost is seen there.
- **User was NOT unhappy** with the nav fix. Prior in the session, the user pushed back on: a
  too-tall banner (slimmed), red segmented control, invisible light-mode text, and the
  cramped/overlapping layouts — all resolved.

---

## 11. CONVERSATIONAL CONTEXT NOT IN THE CODE

- The user is **non-technical-leaning** on ops: explain deploys plainly; they push to Git and
  click Reboot on Streamlit Cloud. They asked whether a consumer **Gemini Pro subscription**
  could power the app — it CANNOT (that's the chat app, not the API; the app needs an API key
  with billing).
- `fileWatcherType="none"` means **no local hot-reload**; the assistant restarts the dev server
  to preview changes. This is fine for the user because they deploy via git+reboot anyway.
- The user cares a lot about **not breaking** the heavily-iterated nav/background/theme — be
  conservative around those `components.html` parent-doc bootstraps.
- The user wrote an **X post** announcing "OctoBot v2.0" (marketing) — not code; context only.
- The **contradiction** about the 3D background (remove vs keep) is real; **latest = keep**.
- When verifying UI, the automated preview browser has `prefers-reduced-motion: reduce` → CSS
  animations read as OFF there; verify motion via keyframe presence / the user's own machine.
- Streamlit sessions reset to Home on websocket reconnect — expect to re-navigate when testing.

---

## 12. FILE-LEVEL CHANGE LOG

- `app.py` — **the entire app**. Recent: Memory Ledger redesign + reports + hero banner +
  `--ml-*` tokens at `:root`; marker technique; non-blocking price/live-feeds (`live_fetch`);
  cached logo; live-updates `.updc-*` motion. NOTES: 16k lines; edit surgically; the memory
  page is `elif st.session_state.page == "memory":`; live helpers near line ~590; hero CSS near
  the `.ml-sub` rule; `.updc-*` CSS near line ~7250.
- `octobot.py` — RAG engine. Recent: switched to `GoogleGenerativeAIEmbeddings`
  (`models/gemini-embedding-001`), `CHROMA_DB_DIR="chroma_gemini"`, warm retriever. NOTES: uses
  `os.getenv("GEMINI_API_KEY")`; cached singletons; class `OctoBot(price_fetcher=…).ask()`.
- `build_vectorstore.py` — build store from `raw_docs`. Recent: Gemini embedder + `chroma_gemini`.
  NOTE: **can't run** — `raw_docs/` is empty.
- `rebuild_vectorstore_gemini.py` — **migration**: re-embed existing Chroma chunks with Gemini,
  paced+resumable, into `chroma_gemini/`. Recent: created this session.
- `.streamlit/config.toml` — NEW: `gatherUsageStats=false`, `headless=true`,
  `fileWatcherType="none"`.
- `requirements.txt` — slimmed (removed torch/transformers/sentence-transformers/langchain-
  huggingface/safetensors/tokenizers/huggingface_hub/hf-xet), UTF-8, 159 pkgs. Backup `.bak`.
- `chroma_gemini/` — ACTIVE knowledge base (729 chunks, Gemini). Must be committed.
- `chroma_db/` — OLD backup (HF embeddings). Unused; kept for rollback.
- `.claude/launch.json` — dev server `octobot-streamlit` on port 8502.
- `app.py.bak`, `requirements.txt.bak`, `rebuild.log` — junk; safe to delete / gitignore.

---

## 13. COMMANDS AND WORKFLOW

Windows, Git Bash / PowerShell. venv at `venv/`. Dev server on **port 8502**.

- Run locally (dev server): `venv/Scripts/streamlit.exe run app.py --server.port 8502`
  (or via the `.claude/launch.json` `octobot-streamlit` config). **NOTE:** with
  `fileWatcherType="none"`, **restart** to see code changes (no hot reload).
- Syntax check: `venv/Scripts/python.exe -m py_compile app.py octobot.py`
- Rebuild knowledge base (only if changing the embedder): `venv/Scripts/python.exe
  rebuild_vectorstore_gemini.py` (resumable; paced for the free embedding rate limit).
- Install deps: `venv/Scripts/pip install -r requirements.txt`
- Deploy: `git add .` → `git commit -m "…"` → `git push` → Reboot on Streamlit Cloud. Make
  sure `chroma_gemini/`, `.streamlit/`, and `requirements.txt` are included. Suggested
  `.gitignore` additions: `*.bak`, `rebuild.log`, `.claude/`.
- Verify Gemini embeddings quickly (venv): load `.env` via `dotenv_values(".env")`, then
  `GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=…)`.

Unusual: the whole app is one file that re-runs entirely per interaction; heavy CSS/JS is
injected via `st.markdown`/`components.html`. Some JS bootstraps into `window.parent.document`
so it persists across reruns.

---

## 14. INSTRUCTIONS FOR THE NEXT CLAUDE INSTANCE

1. **Read this whole file first.** Then **verify against the actual code** — this is a fast-
   moving single-file app; confirm line numbers/behavior with Grep/Read before editing.
2. **Understand the architecture before changing anything** — especially the router
   (`st.session_state.page`), the `--ml-*` token system at `:root`, the **marker technique**
   for styling `st.container(border=True)`, and the **`live_fetch()`** non-blocking pattern.
3. **Do NOT redesign or rewrite working systems** (nav, background/aura, theme toggle, RAG
   pipeline) unless explicitly asked. They were heavily iterated.
4. **Respect all Hard Requirements and rejected approaches** (§7): no data fabrication, no
   masking of the nav bug, both themes correct, reduced-motion, keep functionality/keys.
5. **The 3D ambient background stays** (latest decision) — do not re-hide it.
6. **Continue from §10 (Current Task)**: the nav ghost fix is DONE; the next steps are the
   deploy, enabling Gemini billing (user action), and optionally routing Pulse/Network
   fetchers through `live_fetch()`.
7. **Chat answers failing = LLM quota, not a bug.** Don't "fix" it in code.
8. **Make reasonable decisions** consistent with the documented direction; ask only when truly
   blocked. When editing, **preserve existing functionality** unless told otherwise, verify in
   **both light and dark**, and keep the design **clean/slim/premium** (Linear/Stripe/analytics),
   avoiding everything in the Dislikes list.
9. **Deploy note**: with the file-watcher off, restart the dev server to preview; the user
   ships via git push + Reboot on Streamlit Cloud and must commit `chroma_gemini/` +
   `.streamlit/`.

---

## 15. ACCURACY / SOURCE TAGS

Tags used inline: `FACT` (verified in code/files this session), `DECISION` (agreed in
conversation), `PLAN` (intended, not done), `IDEA` (discussed only), `UNKNOWN` (unverifiable,
e.g. how current `README.md`/`Readme2.md` are, exact Cloud secret contents, whether the user
has already committed items 10–12). Nothing here is presented as implemented unless tagged
`FACT`/DONE.
