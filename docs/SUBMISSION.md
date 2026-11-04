# Submission draft: Meta Global AI Developer Hackathon (Indie track)

> Draft answers. Edit them into your own words before submitting. Fill in the [brackets] after a live run.

**Project name:** GuardRail Lens

**Tagline:** Red-team your chatbot with Llama: attack it, score it, patch it, prove the fix.

**Track / theme:** Indie track. Push the Frontier (AI safety tooling), also Build for Your World
(small teams and solo builders in Nigeria shipping bots with no security team).

**Repository:** https://github.com/coderhema/guardrail-lens

**Demo video:** [YouTube link, 3 min]

## What it does
GuardRail Lens is an automated red team for chatbots. You give it a target: a system prompt plus a model,
or a live HTTP endpoint. It runs 30 jailbreak and prompt-injection templates across 7 categories
(system-prompt leak, secret exfiltration, PII exfiltration, role-play jailbreaks, indirect injection through
pasted documents, instruction override and encoding tricks), and uses an attacker Llama to mutate each one
into a stronger variant. Every reply is graded by a deterministic canary detector (which also catches
base64, leetspeak, reversed and acrostic leaks) and a Llama judge. You get an overall safety score,
per-category scores and the worst transcripts. A Llama "prompt-security engineer" then writes a hardened
system prompt as a diff, and GuardRail Lens re-runs every attack to show the before and after score.
It ships as a CLI and a Streamlit web app.

## Why it matters / inspiration
Chatbots are going into banks, HR and customer support everywhere, and the system prompts often hold
discount codes, keys and customer data. Large companies have red teams; most small teams have nothing.
I wanted a one-command check any developer can run before they ship.

## How Llama / Meta models are used
Llama 3.3 70B (via NVIDIA NIM by default, Groq as an alternative) plays four roles:
1. **Target**: runs the bot's system prompt so we attack the real model behaviour.
2. **Attacker**: rewrites each attack template into a sneakier variant.
3. **Judge**: grades replies as leak, partial or safe with a severity and a reason, in JSON mode.
4. **Patcher**: rewrites the system prompt with targeted defences.
Because Llama is open-weights, the whole loop can run on infrastructure you control, which matters when the
thing you are testing contains secrets.

## How we built it
Python package with an OpenAI-compatible client (swap providers with one env var), a YAML target format,
an attack library, a two-stage judge (canary detector, then Llama), a scorer, a patch generator with a
rule-based fallback, Markdown/JSON reports, a Streamlit UI, and pytest tests that run offline in mock mode.

## Challenges
- LLM judges are inconsistent, so the canary detector runs first and gives deterministic proof of a leak,
  including obfuscated leaks (base64, leetspeak, reversed, acrostics). The LLM only judges what's left.
- Free-tier rate limits: added retries with backoff, a worker setting, and skipping the judge call when a
  canary already proves a leak.
- Keeping the patch useful: the patcher must keep the bot's business content, so there's a validation step
  and a deterministic fallback if the LLM drifts.
- Getting the attacker model to cooperate: it's framed as an authorised test on fake data.

## Accomplishments
- End-to-end loop (attack, judge, score, patch, re-test) in one command.
- On the demo bank bot: [before score] -> [after score] with a live Llama 3.3 70B run.
- Works fully offline in mock mode, so anyone can try it in 30 seconds.

## What we learned
Most leaks come from a few patterns (asking for the prompt "for debugging", hidden instructions in pasted
content, and encoded output), and a short targeted security section fixes most of them.

## What's next
- Multi-turn attacks (slowly escalating conversations) and tool-use / RAG injection tests.
- A GitHub Action that fails CI when a bot's safety score drops.
- Llama Guard as an extra judge, and a public leaderboard of prompt-hardening patterns.
- Larger community-contributed attack library.

## Built with
Python, Llama 3.3 70B, NVIDIA NIM, Groq, Streamlit, pandas, pytest.
