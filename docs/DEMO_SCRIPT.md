# GuardRail Lens: 3-minute demo script

Setup before recording: `.env` has `NVIDIA_API_KEY` (or use mock mode), large terminal font, browser on
`./run_web.sh` (http://127.0.0.1:8000, the Astryx UI; `streamlit run app.py` is the fallback). Do a dry run
first. Live NIM calls take 10-20 s each, so **pre-run the live scans and open the saved JSON reports**
(Advanced → "Open a saved report") instead of waiting on camera. A mock run is instant and shows the flow map
lighting up, so record that part in mock mode and say so.

| Time | On screen | What you say |
|---|---|---|
| 0:00-0:15 | Logo / README hero | "Every company is shipping chatbots and AI agents wired to tools through MCP. One clever message, or one poisoned tool, can leak secrets or make the agent run commands. GuardRail Lens is a red team for chatbots, MCP servers and endpoints, powered by Meta models." |
| 0:15-0:35 | `examples/bank_bot.yaml`, highlight the fake fee-waiver code and fake API key | "Part one: chatbots. Here's a bank support bot with a staff-only code and a backend key in its prompt. Fake data, very real pattern. I mark them as canaries." |
| 0:35-1:00 | UI: Chatbot → NaijaTrust Bank → Run scan. Flow map lights up, then the big score + "By category" tab | "30 attack templates in 7 categories, from prompt leaks and role-play jailbreaks to injections hidden in pasted documents and base64 tricks, each mutated by an attacker model. A canary detector and a Meta-model judge grade every reply. Here's the score per category." |
| 1:00-1:20 | "What leaked" tab, expand the top one, then "The fix" tab (diff) | "Every finding has the attack, the reply and the reason. Then GuardRail Lens writes a hardened system prompt as a diff and re-runs every attack: before (X), after (Y)." |
| 1:20-1:35 | Terminal: `python examples/http_demo_bot.py` then `guardrail-lens scan --url http://127.0.0.1:8088/chat --secret VIP-NAIRA-7781` | "Already deployed? Point it at any HTTP chatbot endpoint, no code changes." |
| 1:35-1:55 | `examples/mcp_vulnerable_server.py`: scroll to the `<IMPORTANT>` block in add_numbers, the injected note, `run_shell` | "Part two: MCP servers. This demo server has a poisoned tool description, a notes tool that returns an injected instruction and a secret, and an unrestricted shell tool. All simulated, nothing executes." |
| 1:55-2:30 | UI: MCP server → Acme MCP (vulnerable) → Run scan (hardened comparison is on by default). "What leaked": agent transcript | "GuardRail Lens connects with the official MCP SDK, lists the tools, flags the poisoned description and the shell tool, probes outputs for leaks and injections, then lets a live agent use the tools under attack. Watch: the agent reads the poisoned note and tries to call run_shell. We block it and record it." |
| 2:30-2:45 | "How to fix" tab, then the big score (vulnerable before → hardened after) | "Each finding comes with a fix. The hardened server applies them: scores go from (X) to (Y)." |
| 2:45-3:00 | README provider table, repo URL | "It runs on Meta's Muse Glimmer on NVIDIA NIM or Llama 3.3 on Groq, works offline in mock mode, and it's open source. GuardRail Lens: find the leak before attackers do." |

Notes
- Say on screen when something is mock mode. Quote live scores only from live runs.
- If short on time, cut the HTTP section (1:20-1:35).
