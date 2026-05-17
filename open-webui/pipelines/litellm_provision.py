"""Per-user LiteLLM virtual key injection pipeline"""
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
import requests
import os


class Pipeline:
    class Valves(BaseModel):
        BACKEND_URL: str = "http://backend:8000"
        LITELLM_URL: str = "http://litellm:4000"
        INTERNAL_SECRET: str = ""

    def __init__(self):
        self.name = "LiteLLM Provision"
        self.valves = self.Valves(
            BACKEND_URL=os.getenv("BACKEND_URL", "http://backend:8000"),
            LITELLM_URL=os.getenv("LITELLM_URL", "http://litellm:4000"),
            INTERNAL_SECRET=os.getenv("INTERNAL_SECRET", ""),
        )

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass

    def _get_virtual_key(self, email: str) -> str:
        headers = {}
        if self.valves.INTERNAL_SECRET:
            headers["x-internal-secret"] = self.valves.INTERNAL_SECRET
        resp = requests.post(
            f"{self.valves.BACKEND_URL}/auth/provision",
            json={"email": email},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["litellm_key"]

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        user = body.get("user", {})
        email = user.get("email", "anonymous@precise.co.th")

        virtual_key = self._get_virtual_key(email)

        import openai
        client = openai.OpenAI(
            base_url=f"{self.valves.LITELLM_URL}/v1",
            api_key=virtual_key,
        )

        # strip pipeline-specific fields
        payload = {k: v for k, v in body.items() if k not in ("user", "metadata")}
        payload["model"] = model_id.replace("litellm_provision.", "")

        response = client.chat.completions.create(**payload)
        return response
