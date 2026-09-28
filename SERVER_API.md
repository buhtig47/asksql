# Server API

`VannaFastAPIServer` and `VannaFlaskServer` expose the same HTTP endpoints. The paths below are the only ones that exist. `/vanna/query` and `/vanna/health` were never part of Vanna, which answers [vanna-ai/vanna#997](https://github.com/vanna-ai/vanna/issues/997).

| Method | Path | What it does |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/` | Built-in chat page (`<vanna-chat>` web component) |
| `POST` | `/api/vanna/v2/chat_poll` | Send a message, get the whole answer as one JSON response |
| `POST` | `/api/vanna/v2/chat_sse` | Send a message, get the answer streamed as Server-Sent Events |
| `WS` | `/api/vanna/v2/chat_websocket` | Same over a WebSocket |

## Start a server

```python
from vanna.servers.fastapi import VannaFastAPIServer

server = VannaFastAPIServer(agent)   # agent = vanna.Agent(...)
server.run(host="127.0.0.1", port=8000)
```

`run()` binds to `0.0.0.0` (all network interfaces) unless you pass `host`.

## `GET /health`

```bash
curl http://localhost:8000/health
```

```json
{"status": "healthy", "service": "vanna"}
```

## `POST /api/vanna/v2/chat_poll`

Request body:

| Field | Type | |
|---|---|---|
| `message` | string | Required. The user's question. |
| `conversation_id` | string | Optional. Pass the ID from a previous response to continue that conversation. |
| `request_id` | string | Optional. For tracing. |
| `metadata` | object | Optional. Passed to your `UserResolver` via `RequestContext.metadata`. |

Cookies, headers and query parameters of the HTTP request are also passed to your `UserResolver`. That's where authentication happens.

```bash
curl -X POST http://localhost:8000/api/vanna/v2/chat_poll \
  -H "Content-Type: application/json" \
  -d '{"message": "What were total sales last month?"}'
```

Response:

```json
{
  "chunks": [
    {
      "rich": {"id": "78b9...", "type": "text", "lifecycle": "create", "data": {"content": "Total sales were ...", "markdown": true}},
      "simple": {"type": "text", "text": "Total sales were ..."},
      "conversation_id": "conv_0a2c12a4",
      "request_id": "9f3a...",
      "timestamp": 1790000000.0
    }
  ],
  "conversation_id": "conv_0a2c12a4",
  "request_id": "9f3a...",
  "total_chunks": 6
}
```

Each chunk is one UI component: text, a status update, a table (`dataframe`), a chart, and so on. `rich` is for UIs that render components. `simple` is a plain-text fallback, and it's `null` for purely visual updates such as progress indicators. To get just the text answer:

```python
answer = "\n".join(c["simple"]["text"] for c in body["chunks"] if c.get("simple") and "text" in c["simple"])
```

## `POST /api/vanna/v2/chat_sse`

Same request body. The response is `text/event-stream`: one `data: {chunk JSON}` event per chunk, ending with `data: [DONE]`.

```bash
curl -N -X POST http://localhost:8000/api/vanna/v2/chat_sse \
  -H "Content-Type: application/json" \
  -d '{"message": "What were total sales last month?"}'
```

## CORS

By default the FastAPI server allows requests from any origin, but **without credentials**. Browsers won't send cookies cross-origin, and pages on other sites can't read cookie-authenticated answers.

If your frontend is on a different origin and uses cookie auth, list its origins. Credentials are then allowed for those origins only:

```python
VannaFastAPIServer(agent, config={
    "cors": {"allow_origins": ["https://app.example.com"]}
})
```

Setting `allow_origins=["*"]` together with `allow_credentials=True` lets *any* website act as your logged-in users, so the server warns if you do it. To turn CORS off entirely (same-origin only): `config={"cors": {"enabled": False}}`.
