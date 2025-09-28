"""
Google AI LLM wrapper using Gemini API
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


class GoogleLLM(LLM):
    """Google AI LLM wrapper using Gemini API"""
    
    google_api_key: str = Field(..., description="Google AI API key")
    model_name: str = Field(default="gemini-2.5-pro-preview-03-25", description="Model name")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=1024, description="Maximum tokens to generate")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    
    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        """Return LLM type"""
        return "google_gemini"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the Google AI LLM"""
        try:
            # Prepare the request payload for Gemini API
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_tokens,
                }
            }
            
            # Add stop sequences if provided
            if stop:
                payload["generationConfig"]["stopSequences"] = stop
            
            # Make the API request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
            headers = {
                "Content-Type": "application/json",
            }
            params = {
                "key": self.google_api_key
            }
            
            logger.debug(f"Making request to Google AI API: {url}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Google AI API response: {json.dumps(result, indent=2)}")
                
                # Extract the generated text
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    logger.info(f"Candidate: {json.dumps(candidate, indent=2)}")
                    
                    # Check if the response was truncated due to max tokens
                    if candidate.get("finishReason") == "MAX_TOKENS":
                        logger.warning("Response truncated due to max tokens limit")
                        return "抱歉，回應因長度限制被截斷。請嘗試更簡潔的問題。"
                    
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        logger.info(f"Parts: {json.dumps(parts, indent=2)}")
                        
                        if len(parts) > 0 and "text" in parts[0]:
                            generated_text = parts[0]["text"]
                            logger.info(f"Google AI API generated {len(generated_text)} characters")
                            return generated_text
                        else:
                            logger.warning(f"No text found in parts: {parts}")
                    else:
                        logger.warning(f"No content/parts found in candidate: {candidate}")
                else:
                    logger.warning(f"No candidates found in response: {result}")
                
                logger.warning("No generated text found in Google AI API response")
                return "抱歉，無法生成回應。"
            else:
                logger.error(f"Google AI API request failed: {response.status_code} - {response.text}")
                return f"API 請求失敗: {response.status_code}"
                
        except requests.exceptions.Timeout:
            logger.error("Google AI API request timed out")
            return "請求超時，請稍後再試。"
        except requests.exceptions.RequestException as e:
            logger.error(f"Google AI API request failed: {e}")
            return f"請求失敗: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in Google AI API call: {e}")
            return f"發生未預期的錯誤: {str(e)}"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text from messages"""
        # Convert messages to a single prompt
        prompt = ""
        for message in messages:
            if hasattr(message, 'content'):
                prompt += f"{message.content}\n"
            else:
                prompt += f"{str(message)}\n"
        
        return self._call(prompt, stop=stop, run_manager=run_manager, **kwargs)

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Get identifying parameters"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


def create_google_llm() -> GoogleLLM:
    """Create a Google LLM instance with environment variables"""
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    model_name = os.getenv("GOOGLE_LLM_MODEL", "gemini-2.5-pro-preview-03-25")
    temperature = float(os.getenv("GOOGLE_LLM_TEMPERATURE", "0.7"))
    max_tokens = int(os.getenv("GOOGLE_LLM_MAX_TOKENS", "1024"))
    
    return GoogleLLM(
        google_api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens
    )
