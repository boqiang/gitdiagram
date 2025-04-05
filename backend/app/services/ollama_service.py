from typing import AsyncGenerator, Literal
import aiohttp
import json
import os
from app.utils.format_message import format_user_message


class OllamaService:
    def __init__(self):
        self.base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("MODEL", "deepseek-r1")

    def call_o3_api(
        self,
        system_prompt: str,
        data: dict,
        api_key: str | None = None,  # Not used for Ollama but kept for interface compatibility
        reasoning_effort: Literal["low", "medium", "high"] = "low",  # Maps to temperature
    ) -> str:
        """
        Makes an API call to Ollama and returns the response.

        Args:
            system_prompt (str): The instruction/system prompt
            data (dict): Dictionary of variables to format into the user message
            api_key (str | None): Not used for Ollama
            reasoning_effort (str): Maps to temperature settings

        Returns:
            str: Ollama's response text
        """
        # Create the user message with the data
        user_message = format_user_message(data)

        # Map reasoning effort to temperature
        temperature = {
            "low": 0.1,
            "medium": 0.5,
            "high": 0.9
        }.get(reasoning_effort, 0.1)

        try:
            print(f"Making non-streaming API call to Ollama model: {self.model}")

            # Make synchronous HTTP request to Ollama
            import requests
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"<system>\n{system_prompt}\n</system>\n\n{user_message}",
                    "temperature": temperature,
                    "stream": False
                }
            )

            if response.status_code != 200:
                raise ValueError(f"Ollama API returned status code {response.status_code}: {response.text}")

            result = response.json()
            return result.get("response", "")

        except Exception as e:
            print(f"Error in Ollama API call: {str(e)}")
            raise

    async def call_o3_api_stream(
        self,
        system_prompt: str,
        data: dict,
        api_key: str | None = None,  # Not used for Ollama but kept for interface compatibility
        reasoning_effort: Literal["low", "medium", "high"] = "low",  # Maps to temperature
    ) -> AsyncGenerator[str, None]:
        """
        Makes a streaming API call to Ollama and yields the responses.

        Args:
            system_prompt (str): The instruction/system prompt
            data (dict): Dictionary of variables to format into the user message
            api_key (str | None): Not used for Ollama
            reasoning_effort (str): Maps to temperature settings

        Yields:
            str: Chunks of Ollama's response text
        """
        # Create the user message with the data
        user_message = format_user_message(data)

        # Map reasoning effort to temperature
        temperature = {
            "low": 0.1,
            "medium": 0.5,
            "high": 0.9
        }.get(reasoning_effort, 0.1)

        payload = {
            "model": self.model,
            "prompt": f"<system>\n{system_prompt}\n</system>\n\n{user_message}",
            "temperature": temperature,
            "stream": True
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Error response: {error_text}")
                        raise ValueError(
                            f"Ollama API returned status code {response.status}: {error_text}"
                        )

                    line_count = 0
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if not line:
                            continue

                        line_count += 1

                        try:
                            data = json.loads(line)
                            content = data.get("response", "")
                            if content:
                                yield content
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e} for line: {line}")
                            continue

                    if line_count == 0:
                        print("Warning: No lines received in stream response")

        except aiohttp.ClientError as e:
            print(f"Connection error: {str(e)}")
            raise ValueError(f"Failed to connect to Ollama API: {str(e)}")
        except Exception as e:
            print(f"Unexpected error in streaming API call: {str(e)}")
            raise

    def count_tokens(self, prompt: str) -> int:
        """
        Counts the number of tokens in a prompt.
        Note: This is a rough estimation for Ollama models.

        Args:
            prompt (str): The prompt to count tokens for

        Returns:
            int: Estimated number of input tokens
        """
        # Simple word-based estimation (not perfect but good enough)
        # Most LLMs use subword tokenization where 1 token ≈ 4 characters
        return len(prompt) // 4 