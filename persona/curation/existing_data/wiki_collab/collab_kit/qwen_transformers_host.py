#!/usr/bin/env python3
"""Tiny OpenAI-compatible Qwen host backed by Hugging Face Transformers."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import time
from typing import Any


DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B"
_COMPONENTS: dict[str, tuple[Any, Any]] = {}


@dataclass(frozen=True)
class HostOptions:
    dtype: str = "auto"
    device_map: str = "auto"
    trust_remote_code: bool = True
    enable_thinking: bool = False


def _load_components(model_id: str, options: HostOptions) -> tuple[Any, Any]:
    cached = _COMPONENTS.get(model_id)
    if cached is not None:
        return cached
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "qwen_transformers_host.py requires transformers and torch. "
            "Install them in the worker environment before starting the host."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=options.trust_remote_code,
    )
    kwargs: dict[str, Any] = {
        "trust_remote_code": options.trust_remote_code,
    }
    if options.dtype:
        kwargs["torch_dtype"] = options.dtype
    if options.device_map:
        kwargs["device_map"] = options.device_map
    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    _COMPONENTS[model_id] = (tokenizer, model)
    return tokenizer, model


def _chat_prompt(tokenizer: Any, messages: list[dict[str, Any]], *, enable_thinking: bool) -> str:
    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=enable_thinking,
        )
    except TypeError:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )


def _temperature(body: dict[str, Any]) -> float:
    try:
        return float(body.get("temperature", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _max_tokens(body: dict[str, Any]) -> int:
    try:
        value = int(body.get("max_tokens", body.get("max_new_tokens", 4096)) or 4096)
    except (TypeError, ValueError):
        value = 4096
    return max(1, value)


def _generate_content(body: dict[str, Any], *, options: HostOptions) -> str:
    model_id = str(body.get("model") or os.environ.get("QWEN_MODEL") or DEFAULT_MODEL)
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("request body must include a non-empty messages list")

    tokenizer, model = _load_components(model_id, options)
    prompt = _chat_prompt(tokenizer, messages, enable_thinking=options.enable_thinking)
    inputs = tokenizer([prompt], return_tensors="pt")
    device = getattr(model, "device", None)
    if device is not None and hasattr(inputs, "to"):
        inputs = inputs.to(device)
    input_ids = inputs["input_ids"]
    input_len = len(input_ids[0])
    temp = _temperature(body)
    generate_kwargs: dict[str, Any] = {
        **inputs,
        "max_new_tokens": _max_tokens(body),
        "do_sample": temp > 0,
        "pad_token_id": getattr(tokenizer, "eos_token_id", None),
    }
    if temp > 0:
        generate_kwargs["temperature"] = temp

    output_ids = model.generate(**generate_kwargs)
    generated_ids = [row[input_len:] for row in output_ids]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()


def chat_completion(body: dict[str, Any], *, options: HostOptions) -> dict[str, Any]:
    model_id = str(body.get("model") or os.environ.get("QWEN_MODEL") or DEFAULT_MODEL)
    content = _generate_content(body, options=options)
    now = int(time.time())
    return {
        "id": f"chatcmpl-qwen-transformers-{now}",
        "object": "chat.completion",
        "created": now,
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


class QwenHandler(BaseHTTPRequestHandler):
    options = HostOptions()
    model_id = DEFAULT_MODEL

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path.rstrip("/") == "/v1/models":
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": self.model_id,
                            "object": "model",
                            "owned_by": "local-transformers",
                        }
                    ],
                },
            )
            return
        self._send_json(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "not found"}})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(size).decode("utf-8"))
            if not body.get("model"):
                body["model"] = self.model_id
            self._send_json(200, chat_completion(body, options=self.options))
        except Exception as exc:
            self._send_json(500, {"error": {"message": str(exc)}})

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.environ.get("QWEN_TRANSFORMERS_HOST_QUIET", "").lower() in {"1", "true", "yes"}:
            return
        super().log_message(fmt, *args)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("QWEN_MODEL", DEFAULT_MODEL))
    parser.add_argument("--host", default=os.environ.get("QWEN_TRANSFORMERS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("QWEN_TRANSFORMERS_PORT", "8000")))
    parser.add_argument("--dtype", default=os.environ.get("QWEN_TRANSFORMERS_DTYPE", "auto"))
    parser.add_argument("--device-map", default=os.environ.get("QWEN_TRANSFORMERS_DEVICE_MAP", "auto"))
    parser.add_argument("--no-trust-remote-code", action="store_true")
    parser.add_argument("--enable-thinking", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    options = HostOptions(
        dtype=args.dtype,
        device_map=args.device_map,
        trust_remote_code=not args.no_trust_remote_code,
        enable_thinking=args.enable_thinking,
    )
    QwenHandler.options = options
    QwenHandler.model_id = args.model
    server = ThreadingHTTPServer((args.host, args.port), QwenHandler)
    print(
        f"Qwen Transformers host listening on http://{args.host}:{args.port}/v1 "
        f"model={args.model}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
