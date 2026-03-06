# Safety and Medical Guardrails

## Scope and Positioning
Dietary Guardian provides informational wellness and care-support guidance. It is **not** a medical diagnosis or treatment system.

## Non-Negotiable Rules
- Do not provide definitive diagnoses.
- Do not prescribe dosages or medication regimen changes.
- Provide informational guidance and triage-oriented recommendations only.
- Recommend professional medical evaluation when symptoms or context warrant escalation.
- Include a brief safety disclaimer in user-facing recommendation/suggestion outputs.

## Red-Flag Escalation Triggers (Minimum Set)
The system must escalate (urgent care / emergency guidance) when red-flag symptoms are detected, including at minimum:
- chest pain
- trouble breathing / shortness of breath
- stroke-like symptoms (face droop, arm weakness, speech difficulty)
- suicidal ideation / self-harm intent
- severe allergic reaction signs (e.g., throat swelling, trouble breathing)
- loss of consciousness / acute severe confusion
- severe bleeding

## Expected Safety Flow (Target Architecture)
1. **Pre-check** before generation
   - detect red flags / unsafe requests
   - decide: allow, ask clarification, refuse, or escalate
2. **Post-check** after draft generation
   - verify output against safety rules and user constraints
   - enforce disclaimer and escalation wording when required

## Structured Safety Decision (Internal Target Shape)
- `decision`: `allow | modify | refuse | escalate | ask_clarification`
- `reasons`: list of triggered rules or concerns
- `required_actions`: follow-up prompts or escalation instructions
- `redactions`: content to remove from unsafe draft output

## Compliance Notes for Contributors
- Keep safety logic server-side; UI may display warnings but must not be the enforcement point.
- Add tests for new safety rules and escalation cases.
- Prefer explicit rule checks over prompt-only behavior.
- Suggestions API (`POST /api/v1/suggestions/generate-from-report`) now performs red-flag text triage and returns structured `safety` decisions.

## Related Docs
- `ARCHITECTURE.md`
- `docs/archive/architecture/architecture-v1.md` (historical snapshot)
- `docs/roadmap-v1.md`
- `README.md`
