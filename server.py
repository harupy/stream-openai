from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import requests
import openai
import os
import json

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_API_KEY is not None, "Please set OPENAI_API_KEY environment variable"

openai.api_key = OPENAI_API_KEY
app = FastAPI()


def get_response_openai(prompt: str):
    openai_model = "gpt-3.5-turbo"
    max_responses = 1
    temperature = 0.7
    max_tokens = 512
    prompt = prompt
    response = openai.ChatCompletion.create(
        model=openai_model,
        temperature=temperature,
        max_tokens=max_tokens,
        n=max_responses,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        messages=[
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )

    for chunk in response:
        current_content = chunk["choices"][0]["delta"].get("content", "")
        yield current_content


PREFIX = b"data: "
PREFIX_LEN = len(PREFIX)


def translate_stream_chunk(chunk: bytes) -> bytes:
    d = json.loads(chunk)
    d["candidates"] = d.pop("choices")
    return json.dumps(d).encode()


def get_response_openai_raw(prompt: str):
    response = requests.post(
        # Obtained by probing arg and kwargs passed to `requests.Session.request` using `mock.patch`
        "https://api.openai.com/v1/chat/completions",
        **{
            "headers": {
                "X-OpenAI-Client-User-Agent": json.dumps(
                    {
                        "bindings_version": "0.27.8",
                        "httplib": "requests",
                        "lang": "python",
                        "lang_version": "3.10.8",
                        "platform": "Linux-5.15.0-78-generic-x86_64-with-glibc2.31",
                        "publisher": "openai",
                        "uname": "Linux 5.15.0-78-generic #85~20.04.1-Ubuntu SMP Mon Jul 17 09:42:39 UTC 2023 x86_64",
                    }
                ),
                "User-Agent": "OpenAI/v1 PythonBindings/0.27.8",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            "json": (
                {
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 512,
                    "n": 1,
                    "top_p": 1,
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                }
            ),
            "files": None,
            "stream": True,
            "timeout": 600,
            "proxies": {},
        },
    )
    # print(response.headers)

    # How the OpenAI Python SDK processes a stream response:
    # https://github.com/openai/openai-python/blob/b82a3f7e4c462a8a10fa445193301a3cefef9a4a/openai/api_requestor.py#L100
    # response.raise_for_status()
    for chunk in response.iter_lines():
        chunk = chunk.strip()
        if chunk == b"data: [DONE]":
            return

        if chunk.startswith(PREFIX):
            chunk = chunk[PREFIX_LEN:]

        if chunk:
            print(chunk)
            print("----")
            yield translate_stream_chunk(chunk)
            yield b"\n\n"


# Example of a stream chunk
{
    "id": "chatcmpl-xxx",
    "object": "chat.completion.chunk",
    "created": 1691497452,
    "model": "gpt-3.5-turbo-0613",
    "choices": [
        {
            "index": 0,
            "delta": {"content": " set"},
            "finish_reason": None,
        }
    ],
}


# Example of a non-stream response
{
    "id": "chatcmpl-xxx",
    "object": "chat.completion",
    "created": 1691498057,
    "model": "gpt-3.5-turbo-0613",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "...",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 93,
        "total_tokens": 105,
    },
}


class Payload(BaseModel):
    prompt: str
    stream: bool = False


@app.post("/stream-chat", response_model=str)
def chat(payload: Payload):
    if payload.stream:
        return StreamingResponse(
            get_response_openai_raw(payload.prompt), media_type="text/event-stream"
        )
    else:
        pass
