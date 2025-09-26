"""
Grok LLM wrapper using OpenRouter API
"""
import os
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.schema import BaseMessage
import requests
from pydantic import Field

logger = logging.getLogger(__name__)


class GrokLLM(LLM):
    """Grok LLM wrapper using OpenRouter API"""
    
    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    model_name: str = Field(default="x-ai/grok-4-fast:free", description="Model name")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=1024, description="Maximum tokens to generate")  # 減少到1024
    top_p: float = Field(default=0.9, description="Top-p for generation")
    frequency_penalty: float = Field(default=0.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, description="Presence penalty")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    
    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        """Return LLM type"""
        return "grok_openrouter"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the Grok LLM via OpenRouter"""
        try:
            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
                "frequency_penalty": self.frequency_penalty,
                "presence_penalty": self.presence_penalty,
            }
            
            # Add stop sequences if provided
            if stop:
                payload["stop"] = stop
            
            # Override with any additional kwargs
            payload.update(kwargs)
            
            # Make the API request
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/opensource4you/community-ai-agent",
                "X-Title": "Community AI Agent"
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            if "choices" not in result or not result["choices"]:
                raise ValueError("No choices in response")
            
            content = result["choices"][0]["message"]["content"]
            
            # Log usage if available
            if "usage" in result:
                usage = result["usage"]
                logger.info(f"Grok API usage - Tokens: {usage.get('total_tokens', 'N/A')}")
            
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API request failed: {e}")
            raise Exception(f"Failed to call Grok LLM: {e}")
        except Exception as e:
            logger.error(f"Error calling Grok LLM: {e}")
            raise Exception(f"Error calling Grok LLM: {e}")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Generate response from messages"""
        # Convert messages to prompt string
        prompt_parts = []
        for message in messages:
            if hasattr(message, 'content'):
                prompt_parts.append(message.content)
            else:
                prompt_parts.append(str(message))
        
        prompt = "\n".join(prompt_parts)
        return self._call(prompt, stop=stop, run_manager=run_manager, **kwargs)

    @classmethod
    def from_environment(cls) -> "GrokLLM":
        """Create GrokLLM instance from environment variables"""
        # Ensure .env is loaded for local/dev and tests
        try:
            load_dotenv()
        except Exception:
            pass

        api_key = os.getenv("OPENROUTER_API_KEY")
        # For non-networked tests, allow a dummy key to enable object creation
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not set; using dummy key for local tests. API calls will fail.")
            api_key = "DUMMY_KEY_FOR_LOCAL_TESTS"
        
        model_name = os.getenv("OPENROUTER_MODEL", "x-ai/grok-4-fast:free")
        temperature = float(os.getenv("OPENROUTER_TEMPERATURE", "0.7"))
        max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "1024"))  # 減少到1024
        
        return cls(
            openrouter_api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available models from OpenRouter"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get("data", [])
            
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []

    def test_connection(self) -> bool:
        """Test connection to OpenRouter API"""
        try:
            # Simple test with minimal prompt
            test_response = self._call("Hello, this is a test.", max_tokens=10)
            return bool(test_response and len(test_response.strip()) > 0)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "timeout": self.timeout
        }
