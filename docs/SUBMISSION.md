# Submission draft: Meta Global AI Developer Hackathon (Indie track)

> Draft answers. Edit them into your own words before submitting. Fill in the [brackets] after a live run.

**Project name:** Juicy Leaks

**Tagline:** Red-team your chatbots, MCP servers and endpoints: attack, score, fix, prove it.

**Track / theme:** Indie track. Push the Frontier (AI safety tooling), also Build for Your World
(small teams and solo builders in Nigeria shipping bots and agents with no security team).

**Repository:** https://github.com/coderhema/juicy-leaks

**Demo video:** [YouTube link, 3 min]

## What it does
Juicy Leaks is an automated red team for chatbots. You give it a target: a system prompt plus a model,
or a live HTTP endpoint. It runs 30 jailbreak and prompt-injection templates across 7 categories
(system-prompt leak, secret exfiltration, PII exfiltration, role-play jailbreaks, indirect injection through
pasted documents, instruction override and encoding tricks), and uses an attacker Llama to mutate each one
into a stronger variant. Every reply is graded by a deterministic canary detector (which also catches
base64, leetspeak, reversed and acrostic leaks) and a Llama judge. You get an overall safety score,
per-category scores and the worst transcripts. A Llama "prompt-security engineer" then writes a hardened
system prompt as a diff, and Juicy Leaks re-runs every attack to show the before and after score.
It also works on any deployed chatbot behind an HTTP endpoint.

For **MCP servers** it connects over stdio or streamable HTTP with the official MCP Python SDK, lists the
tools, and checks for tool-description poisoning (hidden instructions or invisible unicode), prompt
injection in tool results, secret and PII leakage through tool outputs, and over-broad or dangerous tools
(shell, unrestricted file write, outbound export). Then a live LLM agent uses the tools while being
attacked, and Juicy Leaks records whether it follows poisoned instructions, calls dangerous tools
(blocked in a sandbox) or leaks data. Each finding has a severity and a concrete fix. A bundled
vulnerable MCP server and its hardened version show the before and after.
It ships as a CLI (with `--json` findings and `--fail-under` for CI) and a web app built with Meta's Astryx design system: pick a target, press Run (or "Try the demo"), get a one-sentence verdict, one big score, and an interactive problem map where red paths show exactly how an attack got through. Click any part for the worst transcript and the fix. A Streamlit app is kept as a fallback.

## Why it matters / inspiration
Chatbots are going into banks, HR and customer support everywhere, and the system prompts often hold
discount codes, keys and customer data. Large companies have red teams; most small teams have nothing.
I wanted a one-command check any developer can run before they ship.

## How Llama / Meta models are used
A Meta model plays five roles. The default is Meta's **Muse Glimmer 30B** on NVIDIA NIM (NIM retired
Llama 3.3 70B Instruct in August 2026); **Llama 3.3 70B** on Groq is built in as an alternative.
1. **Target**: runs the bot's system prompt so we attack real model behaviour.
2. **Attacker**: rewrites each attack template into a sneakier variant.
3. **Judge**: grades replies as leak, partial or safe with a severity and a reason, as JSON.
4. **Patcher**: rewrites the system prompt with targeted defences.
5. **Agent**: uses MCP tools in a live loop, so we can see whether poisoned tools hijack it.
Any OpenAI-compatible Llama host works, including open-weights Llama on your own hardware, which matters
when the thing you are testing contains secrets.

## How we built it
Python package with an OpenAI-compatible client (swap providers with one env var), a YAML target format,
an attack library, a two-stage judge (canary detector, then Llama), a scorer, a patch generator with a
rule-based fallback, Markdown/JSON reports, an Astryx (React + TypeScript) UI with a React Flow problem map over a FastAPI wrapper, a Streamlit fallback, and pytest tests that run offline in mock mode.

## Challenges
- The model I planned on (Llama 3.3 70B on NIM) had been retired, so the provider layer became
  configurable (NIM, Groq, any OpenAI-compatible host) and handles reasoning models.
- MCP agents can do real damage, so dangerous tools are never auto-called during probing, and in the
  agent loop dangerous calls are blocked and recorded instead of executed.
- LLM judges are inconsistent, so the canary detector runs first and gives deterministic proof of a leak,
  including obfuscated leaks (base64, leetspeak, reversed, acrostics). The LLM only judges what's left.
- Free-tier rate limits: added retries with backoff, a worker setting, and skipping the judge call when a
  canary already proves a leak.
- Keeping the patch useful: the patcher must keep the bot's business content, so there's a validation step
  and a deterministic fallback if the LLM drifts.
- Our own detector had a false positive on the first live run (a refusal repeating public opening hours); we fixed it and re-graded from the saved transcript.
- Getting the attacker model to cooperate: it's framed as an authorised test on fake data.

## Accomplishments
- End-to-end loop (attack, judge, score, patch, re-test) in one command.
- Live (NVIDIA NIM, Muse Glimmer 30B): NaijaTrust Bank bot scored 100/100 before and after, 0 of 30 attacks leaked. [Add HR, travel and MCP live scores when those runs finish.]
- MCP: vulnerable demo server [X]/100 -> hardened server [Y]/100.
- Works fully offline in mock mode, so anyone can try it in 30 seconds.

## What we learned
Most leaks come from a few patterns (asking for the prompt "for debugging", hidden instructions in pasted
content, and encoded output), and a short targeted security section fixes most of them.

## What's next
- Multi-turn attacks (slowly escalating conversations) and RAG injection tests.
- MCP rug-pull detection (tool descriptions that change after approval) and resource/prompt scanning.
- A GitHub Action that fails CI when a bot's safety score drops.
- Llama Guard as an extra judge, and a public leaderboard of prompt-hardening patterns.
- Larger community-contributed attack library.

## Built with
Python, Meta Muse Glimmer, Llama 3.3 70B, NVIDIA NIM, Groq, MCP Python SDK, FastAPI, React 19, TypeScript, Astryx, React Flow, Streamlit, pandas, pytest.
