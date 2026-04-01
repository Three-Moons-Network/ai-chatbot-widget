"""
Tests for the AI chatbot widget handler.

Uses mocking to avoid real AWS/Anthropic API calls during CI.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.handler import (
    ConversationRecord,
    get_conversation,
    handle_get_chat,
    handle_post_chat,
    lambda_handler,
    save_conversation,
)


class TestPostChat:
    @patch("src.handler.anthropic.Anthropic")
    @patch("src.handler.save_conversation")
    def test_post_chat_new_conversation(
        self, mock_save, mock_anthropic_cls, mock_dynamodb_table, mock_anthropic
    ):
        """Test creating a new conversation with POST /chat."""
        mock_save.return_value = True
        mock_anthropic_cls.return_value = mock_anthropic.return_value

        with patch("src.handler.get_conversation", return_value=None):
            body = {
                "session_id": "user-123",
                "message": "How do I reset my password?",
            }

            response_body, status_code = handle_post_chat(body)

            assert status_code == 200
            assert response_body["session_id"] == "user-123"
            assert response_body["user_message"] == "How do I reset my password?"
            assert "assistant_message" in response_body
            assert response_body["message_count"] == 2  # 1 user + 1 assistant
            mock_save.assert_called_once()

    @patch("src.handler.anthropic.Anthropic")
    @patch("src.handler.save_conversation")
    @patch("src.handler.get_conversation")
    def test_post_chat_existing_conversation(
        self,
        mock_get_conv,
        mock_save,
        mock_anthropic_cls,
        mock_anthropic,
        sample_conversation_messages,
    ):
        """Test adding to an existing conversation."""
        # Mock existing conversation
        existing_conv = ConversationRecord(
            session_id="user-123",
            messages=sample_conversation_messages,
            created_at="2026-04-01T12:00:00Z",
            expires_at="2026-04-08T12:00:00Z",
            ttl=1234567890,
        )
        mock_get_conv.return_value = existing_conv
        mock_save.return_value = True
        mock_anthropic_cls.return_value = mock_anthropic.return_value

        body = {
            "session_id": "user-123",
            "message": "Thanks for the help!",
        }

        response_body, status_code = handle_post_chat(body)

        assert status_code == 200
        assert response_body["message_count"] == 6  # 4 existing + 2 new

    def test_post_chat_missing_session_id(self):
        """Test POST /chat with missing session_id."""
        body = {"message": "Hello"}

        response_body, status_code = handle_post_chat(body)

        assert status_code == 400
        assert "session_id" in response_body["error"]

    def test_post_chat_missing_message(self):
        """Test POST /chat with missing message."""
        body = {"session_id": "user-123"}

        response_body, status_code = handle_post_chat(body)

        assert status_code == 400
        assert "message" in response_body["error"]

    def test_post_chat_empty_message(self):
        """Test POST /chat with empty message."""
        body = {"session_id": "user-123", "message": "   "}

        response_body, status_code = handle_post_chat(body)

        assert status_code == 400
        assert "message" in response_body["error"]

    def test_post_chat_oversized_message(self):
        """Test POST /chat with message exceeding size limit."""
        body = {
            "session_id": "user-123",
            "message": "x" * 10_001,
        }

        response_body, status_code = handle_post_chat(body)

        assert status_code == 400
        assert "exceeds maximum" in response_body["error"]

    @patch("src.handler.anthropic.Anthropic")
    @patch("src.handler.save_conversation")
    def test_post_chat_anthropic_error(
        self, mock_save, mock_anthropic_cls
    ):
        """Test POST /chat handling Anthropic API errors."""
        import anthropic as anthropic_mod

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic_mod.APIError(
            message="rate limited",
            request=MagicMock(),
            body=None,
        )
        mock_anthropic_cls.return_value = mock_client

        with patch("src.handler.get_conversation", return_value=None):
            body = {
                "session_id": "user-123",
                "message": "Hello",
            }

            response_body, status_code = handle_post_chat(body)

            assert status_code == 502
            assert "AI service" in response_body["error"]


class TestGetChat:
    @patch("src.handler.get_conversation")
    def test_get_chat_existing_conversation(
        self, mock_get_conv, sample_conversation_messages
    ):
        """Test retrieving an existing conversation."""
        conv = ConversationRecord(
            session_id="user-123",
            messages=sample_conversation_messages,
            created_at="2026-04-01T12:00:00Z",
            expires_at="2026-04-08T12:00:00Z",
            ttl=1234567890,
        )
        mock_get_conv.return_value = conv

        response_body, status_code = handle_get_chat("user-123")

        assert status_code == 200
        assert response_body["session_id"] == "user-123"
        assert len(response_body["messages"]) == 4
        assert response_body["created_at"] == "2026-04-01T12:00:00Z"
        assert response_body["expires_at"] == "2026-04-08T12:00:00Z"

    @patch("src.handler.get_conversation")
    def test_get_chat_nonexistent_conversation(self, mock_get_conv):
        """Test retrieving a conversation that doesn't exist."""
        mock_get_conv.return_value = None

        response_body, status_code = handle_get_chat("nonexistent-123")

        assert status_code == 404
        assert response_body["messages"] == []

    def test_get_chat_empty_session_id(self):
        """Test GET /chat with empty session_id."""
        response_body, status_code = handle_get_chat("   ")

        assert status_code == 400
        assert "session_id" in response_body["error"]


class TestLambdaHandler:
    @patch("src.handler.anthropic.Anthropic")
    @patch("src.handler.save_conversation")
    def test_lambda_handler_post_chat(self, mock_save, mock_anthropic_cls, mock_anthropic):
        """Test lambda_handler with POST /chat."""
        mock_save.return_value = True
        mock_anthropic_cls.return_value = mock_anthropic.return_value

        with patch("src.handler.get_conversation", return_value=None):
            event = {
                "requestContext": {"http": {"method": "POST"}},
                "rawPath": "/chat",
                "body": json.dumps({"session_id": "user-123", "message": "Hello"}),
            }

            result = lambda_handler(event, None)

            assert result["statusCode"] == 200
            assert result["headers"]["Access-Control-Allow-Origin"] == "*"
            body = json.loads(result["body"])
            assert body["session_id"] == "user-123"

    @patch("src.handler.get_conversation")
    def test_lambda_handler_get_chat(self, mock_get_conv, sample_conversation_messages):
        """Test lambda_handler with GET /chat/{session_id}."""
        conv = ConversationRecord(
            session_id="user-123",
            messages=sample_conversation_messages,
            created_at="2026-04-01T12:00:00Z",
            expires_at="2026-04-08T12:00:00Z",
            ttl=1234567890,
        )
        mock_get_conv.return_value = conv

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "rawPath": "/chat/user-123",
            "body": "{}",
        }

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["session_id"] == "user-123"
        assert len(body["messages"]) == 4

    def test_lambda_handler_invalid_route(self):
        """Test lambda_handler with invalid route."""
        event = {
            "requestContext": {"http": {"method": "DELETE"}},
            "rawPath": "/invalid",
            "body": "{}",
        }

        result = lambda_handler(event, None)

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "error" in body

    def test_lambda_handler_cors_headers(self):
        """Test that lambda_handler includes CORS headers."""
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "rawPath": "/chat/test",
            "body": "{}",
        }

        with patch("src.handler.get_conversation", return_value=None):
            result = lambda_handler(event, None)

            assert result["headers"]["Access-Control-Allow-Origin"] == "*"
            assert "Access-Control-Allow-Headers" in result["headers"]
            assert "Access-Control-Allow-Methods" in result["headers"]

    def test_lambda_handler_string_body(self):
        """Test lambda_handler with string body (API Gateway format)."""
        with patch("src.handler.get_conversation", return_value=None):
            with patch("src.handler.anthropic.Anthropic"):
                with patch("src.handler.save_conversation", return_value=True):
                    event = {
                        "requestContext": {"http": {"method": "POST"}},
                        "rawPath": "/chat",
                        "body": '{"session_id": "test-123", "message": "hi"}',
                    }

                    result = lambda_handler(event, None)

                    assert result["statusCode"] == 200

    def test_lambda_handler_invalid_json_body(self):
        """Test lambda_handler with invalid JSON body."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "rawPath": "/chat",
            "body": "not valid json {{{",
        }

        result = lambda_handler(event, None)

        # Should treat invalid JSON as empty body
        assert result["statusCode"] == 400


class TestDatabaseOperations:
    @patch("src.handler.dynamodb.Table")
    def test_save_conversation(self, mock_table_cls):
        """Test saving a conversation to DynamoDB."""
        mock_table = MagicMock()
        mock_table_cls.return_value = mock_table

        with patch("src.handler.get_conversations_table", return_value=mock_table):
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]

            result = save_conversation("user-123", messages)

            assert result is True
            mock_table.put_item.assert_called_once()
            call_args = mock_table.put_item.call_args
            item = call_args.kwargs["Item"]
            assert item["session_id"] == "user-123"
            assert len(item["messages"]) == 2
            assert "ttl" in item

    @patch("src.handler.dynamodb.Table")
    def test_save_conversation_failure(self, mock_table_cls):
        """Test save_conversation handles DynamoDB errors."""
        from botocore.exceptions import ClientError

        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException"}}, "PutItem"
        )

        with patch("src.handler.get_conversations_table", return_value=mock_table):
            messages = [{"role": "user", "content": "Hello"}]

            result = save_conversation("user-123", messages)

            assert result is False


class TestClaudeIntegration:
    @patch("src.handler.anthropic.Anthropic")
    def test_post_chat_uses_correct_model(self, mock_anthropic_cls, mock_anthropic):
        """Test that POST /chat uses the configured Claude model."""
        mock_anthropic_cls.return_value = mock_anthropic.return_value

        with patch("src.handler.get_conversation", return_value=None):
            with patch("src.handler.save_conversation", return_value=True):
                body = {
                    "session_id": "user-123",
                    "message": "Test message",
                }

                response_body, status_code = handle_post_chat(body)

                assert status_code == 200
                assert response_body["model"] == "claude-sonnet-4-20250514"

    @patch("src.handler.anthropic.Anthropic")
    def test_post_chat_returns_usage_stats(self, mock_anthropic_cls, mock_anthropic):
        """Test that POST /chat returns token usage stats."""
        mock_anthropic_cls.return_value = mock_anthropic.return_value

        with patch("src.handler.get_conversation", return_value=None):
            with patch("src.handler.save_conversation", return_value=True):
                body = {
                    "session_id": "user-123",
                    "message": "Test message",
                }

                response_body, status_code = handle_post_chat(body)

                assert status_code == 200
                assert "usage" in response_body
                assert "input_tokens" in response_body["usage"]
                assert "output_tokens" in response_body["usage"]
