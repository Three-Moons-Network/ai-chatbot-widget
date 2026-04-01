"""
Shared test fixtures for chatbot widget tests.
"""

import json
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_dynamodb, mock_ssm


@pytest.fixture
def aws_credentials(monkeypatch):
    """Set fake AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def mock_dynamodb_table(aws_credentials):
    """Create mock DynamoDB conversations table."""
    with mock_dynamodb():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        table = dynamodb.create_table(
            TableName="conversations",
            KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "session_id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            TimeToLiveSpecification={
                "AttributeName": "ttl",
                "Enabled": True,
            },
        )

        yield {"table": table, "dynamodb": dynamodb}


def _mock_anthropic_response(text: str = "Assistant response") -> MagicMock:
    """Build a mock that mimics anthropic.messages.create() response."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.model = "claude-sonnet-4-20250514"
    response.usage.input_tokens = 50
    response.usage.output_tokens = 35
    return response


@pytest.fixture
def mock_anthropic():
    """Mock the Anthropic client."""
    with patch("src.handler.anthropic.Anthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(
            "Thank you for your question. I'm happy to help!"
        )
        mock_client_cls.return_value = mock_client
        yield mock_client_cls


@pytest.fixture
def sample_conversation_messages():
    """Sample conversation messages for testing."""
    return [
        {
            "role": "user",
            "content": "How do I reset my password?",
            "timestamp": "2026-04-01T12:00:00Z",
        },
        {
            "role": "assistant",
            "content": "To reset your password, visit the login page and click 'Forgot Password'.",
            "timestamp": "2026-04-01T12:00:05Z",
        },
        {
            "role": "user",
            "content": "What if I don't receive the email?",
            "timestamp": "2026-04-01T12:00:10Z",
        },
        {
            "role": "assistant",
            "content": "Check your spam folder or contact support@example.com.",
            "timestamp": "2026-04-01T12:00:15Z",
        },
    ]
