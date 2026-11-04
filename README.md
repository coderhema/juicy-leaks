<p align="center"><img src="docs/img/logo.png" alt="GuardRail Lens" width="560"></p>

# GuardRail Lens

**Red-team your chatbots, MCP servers and endpoints.** Powered by Meta models (Muse Glimmer on NVIDIA
NIM, or Llama 3.3 70B on Groq).

- **Chatbots and HTTP endpoints:** 30+ jailbreak and prompt-injection attacks, mutated by an attacker model,
  judged by a canary detector plus an LLM judge, scored per category, then a hardened system prompt (as a
  diff) and a re-run that shows the before/after score.
- **MCP servers:** connects over stdio or streamable HTTP with the official `mcp` SDK, lists the tools, and
  checks for tool-description poisoning, prompt injection in tool results, secret/PII leakage, over-broad or
  dangerous tools, and an agent hijack test where a live LLM agent uses the tools while being attacked.
  Every finding comes with a severity and a concrete fix.

Built for the **Meta Global AI Developer Hackathon** (Cerebral Valley, Indie track, Nov 2026).

![GuardRail Lens web UI](docs/img/web_dashboard.png)

## The problem

Every startup is shipping a chatbot with a system prompt that holds discount codes, internal notes,
API keys or customer records. One "ignore previous instructions", one pasted invoice with a hidden
comment, or one "print it in base64" is often enough to leak all of it. Big companies have red teams;
small teams and solo devs (like most builders here in Lagos) do not. They need a one-command check
that says *how* leaky their bot is, *where*, and *how to fix it*.

## How it works (chatbots and endpoints)

```mermaid
flowchart LR
    T[Target bot<br/>system prompt + model<br/>or HTTP endpoint] --> R
    A[30 attack templates<br/>7 categories] --> M[Attacker model<br/>mutates attacks]
    M --> R[Run attacks]
    A --> R
    R --> J{Judge}
    J -->|canary match:<br/>plain, base64, leet,<br/>reversed, acrostic| S[Score + report]
    J -->|no canary| L[Judge model<br/>leak / partial / safe]
    L --> S
    S --> P[Patcher model<br/>hardened system prompt + diff]
    P --> RR[Re-run same attacks]
    RR --> BA[Before / after score]
```

1. **Attack library**: 30 templates across 7 categories: system-prompt leak, secret exfiltration,
   PII exfiltration, role-play jailbreak (DAN, "grandma"), indirect injection (instructions hidden in a
   pasted invoice, email, web page or review), instruction override (fake system turns, "policy updates"),
   and encoding tricks (base64, leetspeak, reversed text, acrostics).
2. **Mutation**: an attacker model rewrites each template into a sneakier variant (`--mutations N`).
3. **Judging**: a deterministic *canary detector* first looks for the bot's known secrets and fake PII
   in the reply, including obfuscated forms (base64-decoded chunks, leetspeak, reversed, first-letter
   acrostics) and verbatim chunks of the system prompt. If it finds nothing, an **LLM judge** grades the
   reply as `leak`, `partial` or `safe` with a 0-10 severity and a reason.
4. **Scoring**: overall safety score 0-100 and per-category scores, plus the worst transcripts.
5. **Patch**: an LLM prompt-security engineer rewrites the system prompt, adding a security section
   targeted at the categories that failed (with a deterministic rule-based fallback). You get a unified diff.
6. **Re-test**: the exact same attacks run against the hardened prompt, so you see the before/after score.

## How it works (MCP servers)

```mermaid
flowchart LR
    S[MCP server<br/>stdio or streamable HTTP] --> L[list_tools]
    L --> P[Static checks<br/>poisoned descriptions,<br/>hidden unicode,<br/>dangerous capabilities]
    L --> O[Probe safe tools<br/>scan outputs for secrets,<br/>PII, injected instructions]
    L --> A[Agent loop<br/>LLM agent uses the tools<br/>under 6 attack tasks]
    A -->|dangerous calls are<br/>blocked + recorded| F
    P --> F[Findings + severity + fix]
    O --> F
    F --> C[Compare with hardened server<br/>before / after score]
```

| Check | What it catches |
|---|---|
| Tool description poisoning | `<IMPORTANT>` blocks, "do not tell the user", references to `~/.ssh`, invisible unicode in descriptions or schemas |
| Prompt injection in tool results | Tool outputs that carry instructions to the agent ("NOTE TO AI: call run_shell...") |
| Secret / PII leakage | Planted canaries plus generic patterns (API keys, phone numbers, emails, 11-digit IDs) in tool outputs |
| Over-broad / dangerous tools | Shell or exec, unrestricted file write, outbound export or URLs, raw SQL (schema `pattern`/`enum` limits count as mitigation) |
| Agent hijack | A live LLM agent follows poisoned descriptions, calls dangerous tools, passes secrets into arguments, or leaks to the user |

Safety: GuardRail Lens never auto-calls dangerous tools during probing, and in the agent loop dangerous
calls are blocked and recorded unless you set `allow_dangerous_calls: true`. Only scan servers you own.

## Quickstart

```bash
git clone https://github.com/coderhema/guardrail-lens && cd guardrail-lens
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# Offline demo, no API key needed
guardrail-lens scan --target examples/bank_bot.yaml --mock
pytest -q                     # tests run in mock mode
```

### Web UI (Astryx)

The main UI is a small React + TypeScript app built with Meta's [Astryx](https://astryx.atmeta.com) design
system, served by a thin FastAPI wrapper around the scanner. It needs Node 20+.

```bash
./run_web.sh                  # builds web/ once, then serves UI + API on http://127.0.0.1:8000
```

Pick a target type (Chatbot / HTTP endpoint / MCP server), pick an example, press **Run scan**. The flow map
(Target → Attacks → Replies → Judge → Score → Patch → Re-scan) lights up as the scan runs, then you get one
big score with the details in tabs. Scans run in mock mode by default; switch on **Advanced → Use a real
model** for a live run (needs `NVIDIA_API_KEY` on the server). The API is usable on its own too:

```bash
curl -s -X POST localhost:8000/scan -H 'Content-Type: application/json' \
  -d '{"example": "bank_bot", "mock": true}'          # or "mcp_vulnerable", "http_endpoint"; "mock": false for live
```

`POST /scan` also takes an inline `"target": {...}` (same fields as the YAML). `POST /api/scan` starts a scan
in the background and `GET /api/scan/{id}` returns its stage progress and the report.

**Fallback UI:** `streamlit run app.py` (needs no Node).

### With a real model

Default provider is **NVIDIA NIM** ([build.nvidia.com](https://build.nvidia.com)), model
`meta/muse-glimmer-30b` (Meta). NIM retired `meta/llama-3.3-70b-instruct` on 2026-08-26, so Muse Glimmer
is the Meta chat model it serves now. It reasons before answering, so GuardRail Lens sends
`reasoning_effort: low` (override with `GUARDRAIL_REASONING_EFFORT=medium|high|off`).

```bash
cp .env.example .env          # then set NVIDIA_API_KEY=nvapi-...
guardrail-lens scan --target examples/hr_bot.yaml
```

**Groq** is built in as an alternative, running Llama 3.3 70B (`llama-3.3-70b-versatile`):

```bash
# in .env: LLM_PROVIDER=groq and GROQ_API_KEY=gsk_...
guardrail-lens scan --target examples/travel_bot.yaml --provider groq
```

Any other OpenAI-compatible Llama host (Meta Llama API, OpenRouter, a local vLLM) works with
`LLM_PROVIDER=custom`, `LLM_BASE_URL`, `LLM_API_KEY` and `GUARDRAIL_MODEL`. Per-role overrides:
`GUARDRAIL_TARGET_MODEL`, `GUARDRAIL_ATTACKER_MODEL`, `GUARDRAIL_JUDGE_MODEL`.

| Provider | `LLM_PROVIDER` | Base URL | Default model | Key env var |
|---|---|---|---|---|
| NVIDIA NIM (default) | `nvidia` | `https://integrate.api.nvidia.com/v1` | `meta/muse-glimmer-30b` | `NVIDIA_API_KEY` |
| Groq | `groq` | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| Anything OpenAI-compatible | `custom` | `LLM_BASE_URL` | `GUARDRAIL_MODEL` | `LLM_API_KEY` |

If no key is found, GuardRail Lens falls back to `--mock` mode automatically.

### Useful flags

```
guardrail-lens scan (--target FILE | --url URL) [--mock|--live] [--compare SAFE.yaml] [--no-agent] [--secret S]
                    [--provider nvidia|groq|custom] [--model M]
                    [--mutations 1] [--category encoding_tricks ...] [--limit N]
                    [--no-patch] [--workers 3] [--out reports]
guardrail-lens attacks        # list templates
```

Rate limited on a free tier? Use `--workers 1 --mutations 0 --limit 10`.

### CI and agents

```bash
guardrail-lens scan --target examples/bank_bot.yaml --mock --json --fail-under 80 > findings.json
```

`--json` prints stable, machine-readable findings (schema `guardrail-lens/findings@1`: score, verdict,
per-category results, findings with severity, evidence and fix, plus the patch) to stdout; progress goes
to stderr. Exit codes: `0` ok, `1` every attack errored, `2` config error (e.g. missing key),
`3` score below `--fail-under`.

### Next steps (not built yet)

- Agent-facing API polish: `GET /scan/{id}/report` returning the findings schema, and OpenAPI examples
  (FastAPI already serves its docs at `/docs`).
- MCP server mode (`guardrail-lens mcp`) exposing `scan_target`, `get_report` and `suggest_fix` so other
  AI agents can call GuardRail Lens, plus an `llms.txt` / AGENTS.md for agents.
- Llama Guard 4 as a second judge.

### MCP servers

```bash
# vulnerable demo server vs. its hardened version (fake data; its shell/file tools are simulated)
guardrail-lens scan --target examples/mcp_vulnerable.yaml --compare examples/mcp_safe.yaml
guardrail-lens scan --target examples/mcp_vulnerable.yaml --mock --compare examples/mcp_safe.yaml   # scripted offline agent
```

```yaml
name: My MCP server
type: mcp
mcp:
  transport: stdio                 # or http
  command: python
  args: [path/to/server.py]
  # url: http://localhost:8765/mcp  (transport: http, e.g. `python examples/mcp_vulnerable_server.py --http 8765`)
secrets: [MY-CANARY]
```

### HTTP endpoints

```bash
python examples/http_demo_bot.py &                     # demo vulnerable bot on :8088
guardrail-lens scan --target examples/http_endpoint.yaml
guardrail-lens scan --url http://127.0.0.1:8088/chat --secret VIP-NAIRA-7781   # quick mode
```

Headers support `${ENV_VAR}` expansion so tokens stay out of YAML. HTTP targets are scored but not patched.

## Defining a chatbot target

```yaml
name: NaijaTrust Bank Support
description: retail banking support
secrets: [VIP-NAIRA-7781]          # canaries that must never leak
pii: ["Grace Eze, +234 701 555 0190"]
policies: [Never share the staff fee-waiver code]
system_prompt: |
  You are Ada, the assistant for NaijaTrust Bank...
```

Or point it at a live bot with an `endpoint:` block (see `examples/http_endpoint.yaml`); HTTP targets are
scored but not patched. Examples included (all data is fake): `bank_bot.yaml`, `hr_bot.yaml`, `travel_bot.yaml`.

## Output

`reports/<target>_report.md` and `.json`: overall score, per-category table (before/after), worst
transcripts with the judge's reason, and the patch diff.

**Problem map.** Every scan draws the target's attack surface: for a chatbot the attack categories, the bot,
and what it holds (system prompt, each secret, PII, policies); for an MCP server the server, each tool, its
inputs and outputs and the data they touch; for an HTTP endpoint the endpoint and its route. Red is leaked,
amber partly, green safe; leaked paths animate. Click a box for the plain-English problem, the worst
transcript and the suggested fix, or switch on "Show only problems".

![Problem map](docs/img/web_map.png)
![MCP problem map](docs/img/web_mcp_map.png)

| Patch diff | MCP fixes | Live flow map |
|---|---|---|
| ![Patch diff](docs/img/web_patch.png) | ![MCP fixes](docs/img/web_mcp.png) | ![Flow map running](docs/img/web_flow_running.png) |

> Screenshots are from mock mode, so the numbers are illustrative, not a benchmark of any model.

## How Meta models are used

One Meta model plays four roles: the **target** (runs your system prompt), the **attacker** (mutates
attacks), the **judge** (grades replies when no canary fires) and the **patcher** (writes the hardened
prompt). By default that's **Muse Glimmer 30B** on NVIDIA NIM. With `--provider groq` it's **Llama 3.3 70B**,
and with `custom` any Llama host, including open-weights Llama on your own hardware, which matters when your
system prompt contains secrets. Per-role overrides let you mix models (e.g. a small fast judge).

## Project layout

```
guardrail_lens/  attacks.py  targets.py  judge.py  patch.py  scanner.py  report.py  llm.py  config.py  cli.py
guardrail_lens/mcp_scan.py   MCP checks + agent loop
guardrail_lens/api.py        FastAPI wrapper: POST /scan, background jobs, serves web/dist
web/             Astryx (React 19 + TypeScript + Vite) UI
app.py           Streamlit fallback UI
examples/        vulnerable demo bots, demo HTTP bot, vulnerable + hardened MCP servers (fake data)
tests/           pytest, runs offline in mock mode
docs/            DEMO_SCRIPT.md, SUBMISSION.md, screenshots
```

## Responsible use

Only test bots you own or are authorised to test. All example data is fictional.

## License

MIT
