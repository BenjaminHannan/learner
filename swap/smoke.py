"""One tool-call request against the local vLLM server: shows whether the tool parser and the thinking switch work."""
import json, sys, time, urllib.request
kw = json.loads(sys.argv[1])
tools = [{"type": "function", "function": {"name": "find_user_id_by_email", "description": "Find a user id by email.",
          "parameters": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}}}]
body = {"model": "m", "max_tokens": 2048, "tools": tools, "chat_template_kwargs": kw,
        "messages": [{"role": "system", "content": "You are a store agent. Use tools to look up users."},
                     {"role": "user", "content": "Hi, I want to return something. My email is noah.brown7922@example.com."}]}
t = time.time()
r = json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:8000/v1/chat/completions", json.dumps(body).encode(),
                                                             {"Content-Type": "application/json"}), timeout=600).read())
m = r["choices"][0]["message"]
print(json.dumps({"secs": round(time.time() - t, 2), "tool_calls": m.get("tool_calls"), "content": (m.get("content") or "")[:300],
                  "reasoning_chars": len(m.get("reasoning_content") or m.get("reasoning") or ""), "usage": r.get("usage")}))
