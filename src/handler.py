"""
AI Chatbot Widget — Lambda Handler

Provides two endpoints:
  - POST /chat: Send a message, get AI response, store in DynamoDB
  - GET /chat/{session_id}: Retrieve full conversation history

Conversations are stored in DynamoDB with automatic TTL-based expiration.
Each conversation includes message history from Claude API.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Any

import anthropic
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))
CONVERSATION_TTL_HOURS = int(os.environ.get("CONVERSATION_TTL_HOURS", "168"))  # 7 days

SYSTEM_PROMPT = """You are a helpful, friendly customer support assistant for a small business.
Answer questions clearly and concisely. If you don't know something, say so honestly.
Be warm and professional in tone. Keep responses to 2-3 sentences when possible."""

# AWS Service clients
dynamodb = boto3.resource("dynamodb")
ssm = boto3.client("ssm")

# Cache SSM parameters
_ssm_cache: dict[str, Any] = {}


def get_ssm_param(param_name: str, decrypt: bool = True) -> str:
    """Fetch SSM parameter with caching."""
    if param_name in _ssm_cache:
        return _ssm_cache[param_name]

    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=decrypt)
        value = response["Parameter"]["Value"]
        _ssm_cache[param_name] = value
        return value
    except ClientError as exc:
        logger.error(f"Failed to fetch SSM parameter {param_name}: {exc}")
        raise


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str


@dataclass
class ConversationRecord:
    """A conversation with full history."""

    session_id: str
    messages: list[dict[str, Any]]
    created_at: str
    expires_at: str
    ttl: int


@dataclass
class ChatResponse:
    """Response to a chat request."""

    session_id: str
    user_message: str
    assistant_message: str
    message_count: int
    model: str
    usage: dict[str, int]


# ---------------------------------------------------------------------------
# DynamoDB helpers
# ---------------------------------------------------------------------------


def get_conversations_table() -> Any:
    """Get DynamoDB conversations table."""
    try:
        return dynamodb.Table("conversations")
    except Exception as exc:
        logger.error(f"Failed to get conversations table: {exc}")
        raise


def get_conversation(session_id: str) -> ConversationRecord | None:
    """Retrieve a conversation from DynamoDB."""
    try:
        table = get_conversations_table()
        response = table.get_item(Key={"session_id": session_id})
        item = response.get("Item")

        if not item:
            return None

        return ConversationRecord(
            session_id=item["session_id"],
            messages=item.get("messages", []),
            created_at=item.get("created_at", ""),
            expires_at=item.get("expires_at", ""),
            ttl=item.get("ttl", 0),
        )
    except ClientError as exc:
        logger.error(f"Failed to get conversation {session_id}: {exc}")
        return None


def save_conversation(session_id: str, messages: list[dict[str, Any]]) -> bool:
    """Save or update a conversation in DynamoDB."""
    try:
        table = get_conversations_table()
        now = int(time.time())
        ttl = now + (CONVERSATION_TTL_HOURS * 3600)

        from datetime import datetime, timedelta

        created_at = datetime.utcnow().isoformat() + "Z"
        expires_at = (datetime.utcnow() + timedelta(hours=CONVERSATION_TTL_HOURS)).isoformat() + "Z"

        table.put_item(
            Item={
                "session_id": session_id,
                "messages": messages,
                "created_at": created_at,
                "expires_at": expires_at,
                "ttl": ttl,
                "updated_at": created_at,
            }
        )
        return True
    except ClientError as exc:
        logger.error(f"Failed to save conversation {session_id}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Claude integration
# ---------------------------------------------------------------------------


def call_claude(messages: list[dict[str, str]]) -> tuple[str, dict[str, int]]:
    """
    Call Claude API with conversation messages.

    Returns (response_text, usage_dict)
    """
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    response_text = response.content[0].text
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    return response_text, usage


# ---------------------------------------------------------------------------
# Request handlers
# ---------------------------------------------------------------------------


def handle_post_chat(body: dict[str, Any]) -> tuple[dict, int]:
    """
    Handle POST /chat request.

    Expects:
      - session_id: str (unique identifier for this conversation)
      - message: str (user message)

    Returns (response_dict, status_code)
    """
    session_id = body.get("session_id", "").strip()
    user_message = body.get("message", "").strip()

    # Validate input
    if not session_id:
        return {"error": "session_id is required"}, 400
    if not user_message:
        return {"error": "message is required and cannot be empty"}, 400
    if len(user_message) > 10_000:
        return {"error": "message exceeds maximum length of 10,000 characters"}, 400

    # Retrieve or initialize conversation
    conversation = get_conversation(session_id)
    if conversation:
        messages = conversation.messages
        logger.info(f"Retrieved conversation {session_id} with {len(messages)} messages")
    else:
        messages = []
        logger.info(f"Starting new conversation {session_id}")

    # Add user message
    messages.append({"role": "user", "content": user_message})

    # Call Claude
    try:
        assistant_response, usage = call_claude(messages)
    except anthropic.APIError as exc:
        logger.error(f"Claude API error: {exc}")
        return {"error": "AI service temporarily unavailable. Please retry."}, 502
    except Exception as exc:
        logger.error(f"Unexpected error calling Claude: {exc}")
        return {"error": "Internal server error"}, 500

    # Add assistant response
    messages.append({"role": "assistant", "content": assistant_response})

    # Save to DynamoDB
    if not save_conversation(session_id, messages):
        logger.warning(f"Failed to save conversation {session_id}")

    logger.info(
        "Chat request processed",
        extra={
            "session_id": session_id,
            "message_count": len(messages),
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
        },
    )

    response = ChatResponse(
        session_id=session_id,
        user_message=user_message,
        assistant_message=assistant_response,
        message_count=len(messages),
        model=ANTHROPIC_MODEL,
        usage=usage,
    )

    return asdict(response), 200


def handle_get_chat(session_id: str) -> tuple[dict, int]:
    """
    Handle GET /chat/{session_id} request.

    Returns full conversation history.
    Returns (response_dict, status_code)
    """
    session_id = session_id.strip()

    if not session_id:
        return {"error": "session_id is required"}, 400

    conversation = get_conversation(session_id)

    if not conversation:
        return {
            "session_id": session_id,
            "messages": [],
            "created_at": None,
            "expires_at": None,
            "note": "No conversation found for this session_id",
        }, 404

    # Format messages with timestamps
    formatted_messages = []
    for msg in conversation.messages:
        formatted_messages.append({
            "role": msg.get("role", ""),
            "content": msg.get("content", ""),
            "timestamp": msg.get("timestamp", ""),
        })

    logger.info(
        "Retrieved conversation",
        extra={
            "session_id": session_id,
            "message_count": len(formatted_messages),
        },
    )

    return {
        "session_id": session_id,
        "messages": formatted_messages,
        "created_at": conversation.created_at,
        "expires_at": conversation.expires_at,
    }, 200


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict, context: Any) -> dict:
    """
    AWS Lambda handler for API Gateway (HTTP API v2).

    Supports two routes:
      - POST /chat — send message, get response
      - GET /chat/{session_id} — retrieve history

    Returns:
      - 200/404 with JSON body on success
      - 400 on validation errors
      - 502 on AI service errors
      - 500 on unexpected failures
    """
    http_method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")

    logger.info(
        "Chat request received",
        extra={
            "method": http_method,
            "path": path,
        },
    )

    try:
        # Parse body for POST requests
        body = event.get("body", "{}")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {}
        elif not isinstance(body, dict):
            body = {}

        # Route based on method and path
        if http_method == "POST" and path == "/chat":
            response_body, status_code = handle_post_chat(body)

        elif http_method == "GET" and path.startswith("/chat/"):
            # Extract session_id from path
            session_id = path.split("/chat/")[-1]
            response_body, status_code = handle_get_chat(session_id)

        else:
            response_body = {
                "error": f"Not found: {http_method} {path}",
                "supported_routes": [
                    "POST /chat",
                    "GET /chat/{session_id}",
                ],
            }
            status_code = 404

        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            },
            "body": json.dumps(response_body),
        }

    except Exception:
        logger.exception("Unexpected error in lambda_handler")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"}),
        }
