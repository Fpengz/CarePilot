"""Tests for inference engine event text capture."""

from pydantic_ai.messages import PartDeltaEvent, PartEndEvent, TextPart, TextPartDelta

from care_pilot.agent.runtime.inference_engine import _collect_text_from_events


def test_collect_text_from_events() -> None:
    events = [
        PartDeltaEvent(index=0, delta=TextPartDelta("hello ")),
        PartEndEvent(index=0, part=TextPart("world")),
    ]

    assert _collect_text_from_events(events) == "hello world"
