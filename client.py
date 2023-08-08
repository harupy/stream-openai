import requests
import json
from typing import Any


# mlflow.gateway.query
def query(data: dict[str, Any]):
    stream = data.get("stream", False)
    url = "http://127.0.0.1:8000/stream-chat"
    return requests.post(
        url,
        stream=stream,
        json=data,
    )


data = {
    "prompt": "What is MLflow?",
    "stream": True,
}
for idx, chunk in enumerate(query(data).iter_lines()):
    if chunk:
        print(idx, json.loads(chunk))
