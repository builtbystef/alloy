from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from alloy_server.modules.assistant.agent import HISTORY_TURNS, trim_history


def test_history_trimming_keeps_whole_turns():
    messages: list[ModelMessage] = []
    for i in range(HISTORY_TURNS + 5):
        messages.append(ModelRequest(parts=[UserPromptPart(content=f"q{i}")]))
        messages.append(ModelResponse(parts=[TextPart(content=f"a{i}")]))
    trimmed = trim_history(messages)
    assert len(trimmed) == 2 * HISTORY_TURNS + 1
    note, first_kept = trimmed[0], trimmed[1]
    assert isinstance(note, ModelRequest)
    assert isinstance(first_kept, ModelRequest)
    note_part, kept_part = note.parts[0], first_kept.parts[0]
    assert isinstance(note_part, UserPromptPart)
    assert isinstance(kept_part, UserPromptPart)
    assert "5 earlier turns" in str(note_part.content)
    assert kept_part.content == "q5"
    assert trim_history(messages[:4]) == messages[:4]
