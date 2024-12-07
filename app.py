from quart import Quart, request, jsonify
from src.chat_server.chat_service import InjectiveChatService
app = Quart(__name__)
chat_service = InjectiveChatService()


@app.route("/chat", methods=["POST"])
async def chat_endpoint():
    try:
        data = await request.get_json()
        if not data or "message" not in data:
            return (
                jsonify(
                    {
                        "type": "error",
                        "error": "No message provided",
                        "content": "Please provide a message to continue our conversation.",
                        "session_id": data.get("session_id", "default"),
                    }
                ),
                400,
            )

        response = await chat_service.get_response(
            message=data["message"], session_id=data.get("session_id", "default")
        )

        return jsonify(response)

    except Exception as e:
        return (
            jsonify(
                {
                    "type": "error",
                    "error": str(e),
                    "content": "I apologize, but I encountered an error. Please try again.",
                    "session_id": data.get("session_id", "default")
                    if data
                    else "default",
                }
            ),
            500,
        )


@app.route("/history", methods=["GET"])
async def history_endpoint():
    session_id = request.args.get("session_id", "default")
    return jsonify(
        {"history": chat_service.conversation_manager.get_history(session_id)}
    )


@app.route("/clear", methods=["POST"])
async def clear_endpoint():
    session_id = request.args.get("session_id", "default")
    chat_service.conversation_manager.clear_history(session_id)
    return jsonify({"status": "success"})


if __name__ == "__main__":
    import asyncio
    from hypercorn.config import Config as HyperConfig
    from hypercorn.asyncio import serve

    config = HyperConfig()
    config.bind = ["0.0.0.0:5000"]
    asyncio.run(serve(app, config))
