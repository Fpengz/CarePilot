from dataclasses import dataclass, field


@dataclass(frozen=True)
class SafetyDecision:
    decision: str
    reasons: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    redactions: list[str] = field(default_factory=list)


_RED_FLAG_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("chest_pain", ("chest pain", "pressure in chest")),
    ("trouble_breathing", ("trouble breathing", "shortness of breath", "cannot breathe")),
    ("stroke_signs", ("face droop", "slurred speech", "arm weakness", "stroke")),
    ("suicidal_ideation", ("suicidal", "kill myself", "self harm")),
    ("severe_allergic_reaction", ("anaphylaxis", "throat swelling", "severe allergic")),
    ("loss_of_consciousness", ("passed out", "loss of consciousness", "unconscious")),
    ("severe_bleeding", ("severe bleeding", "bleeding heavily", "cannot stop bleeding")),
)


def evaluate_text_safety(text: str) -> SafetyDecision:
    lowered = text.lower()
    reasons: list[str] = []
    for rule_name, patterns in _RED_FLAG_RULES:
        if any(pattern in lowered for pattern in patterns):
            reasons.append(rule_name)

    if reasons:
        return SafetyDecision(
            decision="escalate",
            reasons=reasons,
            required_actions=[
                "Seek urgent medical care or call local emergency services now.",
                "Do not rely on this app for emergency diagnosis or treatment.",
            ],
            redactions=["definitive_diagnosis", "dosage_prescriptions"],
        )

    return SafetyDecision(decision="allow")
