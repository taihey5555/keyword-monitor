from unittest.mock import Mock, patch

import summarizer


def test_deepseek_payload_uses_user_message_and_auth_header():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

    with patch.object(summarizer, "DEEPSEEK_API_KEY", "sk-test"), patch(
        "summarizer.requests.post", return_value=response
    ) as post_mock:
        out = summarizer._deepseek("hello", max_tokens=123, temperature=0.2)

    assert out == "ok"
    kwargs = post_mock.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
    assert kwargs["json"]["model"] == "deepseek-chat"
    assert kwargs["json"]["messages"] == [{"role": "user", "content": "hello"}]
    assert kwargs["json"]["max_tokens"] == 123
    assert kwargs["json"]["temperature"] == 0.2


def test_summarize_without_api_key_falls_back_to_abstract():
    article = {"title": "t", "abstract": "a" * 1000}
    with patch.object(summarizer, "DEEPSEEK_API_KEY", ""):
        out = summarizer.summarize(article)
    assert out == article["abstract"][: summarizer.SUMMARY_MAX_CHARS]
