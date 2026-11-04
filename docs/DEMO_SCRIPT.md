# GuardRail Lens: 3-minute demo script

Setup before recording: `.env` has `NVIDIA_API_KEY` (or use `--mock`), terminal font large, browser at
`streamlit run app.py`, bank bot selected. Do one dry run so the live scan is cached in your head.
Tip: if the live API is slow, record the live CLI scan with `--limit 10 --mutations 0` and use the UI for the full run.

| Time | On screen | What you say |
|---|---|---|
| 0:00-0:20 | Title slide or README hero: "GuardRail Lens" | "Every company is shipping chatbots with secrets in the system prompt: discount codes, API keys, customer records. One clever message can leak all of it. Big companies have red teams. Small teams don't. GuardRail Lens is a red team in one command, powered by Llama." |
| 0:20-0:45 | `examples/bank_bot.yaml` in the editor. Highlight the fake fee-waiver code and fake API key | "Here's a typical bank support bot. Fake data, but a very real pattern: a staff-only code and a backend key sitting right in the prompt. I mark them as canaries so we can catch leaks for certain." |
| 0:45-1:15 | Terminal: `guardrail-lens scan --target examples/bank_bot.yaml` running, progress lines | "GuardRail Lens loads 30 attack templates across 7 categories: prompt leaks, secret and PII exfiltration, role-play jailbreaks, indirect injection hidden in pasted documents, fake system messages, and encoding tricks like base64 and leetspeak. An attacker Llama mutates each one into a sneakier variant, so it's 60 attacks." |
| 1:15-1:45 | Streamlit dashboard: score metric, category bar chart | "Each reply is judged twice: a canary detector that even decodes base64, leetspeak, reversed text and acrostics, then a Llama judge for anything subtle. This bot scores (read the number) out of 100. Indirect injection and role-play are the worst." |
| 1:45-2:10 | "Worst transcripts" tab, expand the top leak | "Here's the proof: I asked it to print its instructions and it handed over the fee-waiver code and the API key. Every finding comes with the attack, the reply and the judge's reason." |
| 2:10-2:35 | "Patch diff" tab, scroll the green lines | "Now the fix. A Llama prompt-security engineer rewrites the system prompt with rules targeted at exactly the categories that failed. You get a diff you can paste straight into production." |
| 2:35-2:50 | Back to the metrics: Before vs After, chart with both bars | "Then it re-runs the same attacks against the hardened prompt. Score goes from (before) to (after). Measured, not guessed." |
| 2:50-3:00 | README: provider table, GitHub URL | "It runs on Llama 3.3 70B through NVIDIA NIM or Groq, works on any OpenAI-compatible endpoint or a live HTTP bot, and it's open source. GuardRail Lens: find the leak before attackers do." |

Notes
- Say clearly if a shot is mock mode. Real numbers should come from a live run.
- Keep it under 3:00. Cut the 0:45-1:15 section shorter if needed.
