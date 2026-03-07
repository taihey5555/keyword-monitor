from unittest.mock import patch

import weekly_summary


def test_generate_weekly_comment_prompt_mentions_500_chars():
    top3 = [{"title": "A", "_reason": "R"}]

    captured = {}

    def fake_deepseek(prompt: str, max_tokens: int = 0, temperature: float = 0.0):
        captured["prompt"] = prompt
        return "ok"

    with patch.object(weekly_summary, "DEEPSEEK_API_KEY", "sk-test"), patch(
        "weekly_summary._deepseek", side_effect=fake_deepseek
    ):
        out = weekly_summary.generate_weekly_comment(top3)

    assert out == "ok"
    assert "500文字以内" in captured["prompt"]
