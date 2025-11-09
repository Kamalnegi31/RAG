"""
LLM Manager - Multi-Provider Abstraction Layer
Supports: OpenAI, Anthropic, AWS Bedrock, OpenRouter
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config import get_settings

settings = get_settings()


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    OPENROUTER = "openrouter"


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion from LLM."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        """Generate streaming completion from LLM."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation."""

    def __init__(self):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
        except ImportError:
            raise ImportError("openai package not installed")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion from OpenAI."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return {
            "text": response.choices[0].message.content,
            "model": response.model,
            "tokens_used": response.usage.total_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "finish_reason": response.choices[0].finish_reason
        }

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        """Generate streaming completion from OpenAI."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider implementation."""

    def __init__(self):
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.model = settings.anthropic_model
        except ImportError:
            raise ImportError("anthropic package not installed")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion from Anthropic."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )

        return {
            "text": response.content[0].text,
            "model": response.model,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "finish_reason": response.stop_reason
        }

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        """Generate streaming completion from Anthropic."""
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text


class BedrockProvider(BaseLLMProvider):
    """AWS Bedrock provider implementation."""

    def __init__(self):
        try:
            import boto3
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=settings.bedrock_region,
                aws_access_key_id=settings.bedrock_access_key_id or settings.aws_access_key_id,
                aws_secret_access_key=settings.bedrock_secret_access_key or settings.aws_secret_access_key
            )
            self.model = settings.bedrock_model_id
        except ImportError:
            raise ImportError("boto3 package not installed")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion from Bedrock."""
        import json

        # Format for Anthropic Claude on Bedrock
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            body["system"] = system_prompt

        response = self.client.invoke_model(
            modelId=self.model,
            body=json.dumps(body)
        )

        response_body = json.loads(response['body'].read())

        return {
            "text": response_body['content'][0]['text'],
            "model": self.model,
            "tokens_used": response_body['usage']['input_tokens'] + response_body['usage']['output_tokens'],
            "prompt_tokens": response_body['usage']['input_tokens'],
            "completion_tokens": response_body['usage']['output_tokens'],
            "finish_reason": response_body.get('stop_reason', 'end_turn')
        }

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        """Generate streaming completion from Bedrock."""
        # Streaming implementation for Bedrock
        # For simplicity, using non-streaming version
        result = await self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)
        yield result["text"]


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider implementation."""

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient()
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion from OpenRouter."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://commloan.com",
                "X-Title": "CommLoan RAG"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

        data = response.json()

        return {
            "text": data['choices'][0]['message']['content'],
            "model": data['model'],
            "tokens_used": data['usage']['total_tokens'],
            "prompt_tokens": data['usage']['prompt_tokens'],
            "completion_tokens": data['usage']['completion_tokens'],
            "finish_reason": data['choices'][0]['finish_reason']
        }

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        """Generate streaming completion from OpenRouter."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        async with self.client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://commloan.com",
                "X-Title": "CommLoan RAG"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    if line.strip() == "data: [DONE]":
                        break
                    import json
                    try:
                        data = json.loads(line[6:])
                        if data['choices'][0]['delta'].get('content'):
                            yield data['choices'][0]['delta']['content']
                    except:
                        continue


class LLMManager:
    """Manages multiple LLM providers with fallback support."""

    def __init__(self):
        self.providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self._initialize_providers()
        self.default_provider = LLMProvider(settings.default_llm_provider)
        self.fallback_providers = [LLMProvider(p) for p in settings.fallback_providers_list]

    def _initialize_providers(self):
        """Initialize all configured providers."""
        if settings.openai_api_key:
            try:
                self.providers[LLMProvider.OPENAI] = OpenAIProvider()
            except Exception as e:
                print(f"Failed to initialize OpenAI: {e}")

        if settings.anthropic_api_key:
            try:
                self.providers[LLMProvider.ANTHROPIC] = AnthropicProvider()
            except Exception as e:
                print(f"Failed to initialize Anthropic: {e}")

        if settings.bedrock_region:
            try:
                self.providers[LLMProvider.BEDROCK] = BedrockProvider()
            except Exception as e:
                print(f"Failed to initialize Bedrock: {e}")

        if settings.openrouter_api_key:
            try:
                self.providers[LLMProvider.OPENROUTER] = OpenRouterProvider()
            except Exception as e:
                print(f"Failed to initialize OpenRouter: {e}")

    async def generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion with automatic fallback.

        Args:
            prompt: User prompt
            provider: Optional specific provider to use
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Dictionary with response text and metadata
        """
        providers_to_try = []

        if provider:
            providers_to_try.append(provider)
        else:
            providers_to_try.append(self.default_provider)
            providers_to_try.extend(self.fallback_providers)

        last_error = None

        for prov in providers_to_try:
            if prov not in self.providers:
                continue

            try:
                result = await self.providers[prov].generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                result["provider"] = prov.value
                return result

            except Exception as e:
                last_error = e
                print(f"Provider {prov.value} failed: {e}")
                continue

        raise Exception(f"All providers failed. Last error: {last_error}")

    async def generate_stream(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        """Generate streaming completion."""
        prov = provider or self.default_provider

        if prov not in self.providers:
            raise ValueError(f"Provider {prov.value} not available")

        async for chunk in self.providers[prov].generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield chunk

    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return [p.value for p in self.providers.keys()]
