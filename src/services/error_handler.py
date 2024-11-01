from __future__ import annotations
from typing import TYPE_CHECKING
import openai
import logging
import asyncio
import aiohttp

if TYPE_CHECKING:
    from src.ui.components.chat_container import ChatContainer


class ErrorHandler:
    """A centralized error handler for the ChatApp."""

    ERROR_MESSAGES = {
        openai.APIError: "OpenAI API error occurred. Please try again later.",
        openai.RateLimitError: "Rate limit exceeded. Please wait a moment before trying again.",
        openai.APIConnectionError: "Connection to OpenAI failed. Please check your internet connection.",
        openai.BadRequestError: "Invalid request to OpenAI API. Please try again.",
        asyncio.TimeoutError: "Request timed out. Please try again.",
        aiohttp.ClientError: "Network error occurred. Please check your connection.",
        Exception: "An unexpected error occurred. Please try again.",
    }

    @staticmethod
    async def handle_error(chat_container: ChatContainer, error: Exception) -> None:
        """Handle different types of errors and display appropriate messages."""
        error_type = type(error)
        error_message = ErrorHandler.ERROR_MESSAGES.get(error_type, str(error))

        # Log the error for debugging
        logging.error(f"Error occurred: {error_type.__name__} - {str(error)}")

        # Hide thinking indicator if it's showing
        await chat_container.hide_thinking()

        # Show error message to user
        await chat_container.add_message("system", f"⚠️ {error_message}")

    @staticmethod
    async def handle_api_error(chat_container: ChatContainer, error: Exception) -> bool:
        """Specifically handle API-related errors."""
        if isinstance(error, openai.RateLimitError):
            await asyncio.sleep(1)  # Basic retry delay
            return True  # Indicate retry is possible

        await ErrorHandler.handle_error(chat_container, error)
        return False  # Indicate no retry
