"""
LLM Orchestration service for phi2 integration.
Handles prompt construction, model inference, and JSON output parsing.
"""
from typing import Dict, List, Any, Optional
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from src.config import settings
from src.utils.logging_config import logger


class LLMOrchestrator:
    """
    Orchestrates LLM interactions for meal plan generation.
    Uses phi2 model with strict numeric provenance rules.
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize LLM orchestrator.
        
        Args:
            model_name: Name of the model to load (default from settings)
        """
        self.model_name = model_name or settings.MODEL_NAME
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading LLM model: {self.model_name} on {self.device}")
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Set padding token if not set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                trust_remote_code=True
            ).to(self.device)
            
            self.model.eval()
            
            logger.info(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_new_tokens: int = None
    ) -> str:
        """
        Call the LLM with cursor-style messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (default from settings)
            max_new_tokens: Maximum tokens to generate (default from settings)
            
        Returns:
            Generated text
        """
        temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_new_tokens = max_new_tokens if max_new_tokens is not None else settings.LLM_MAX_NEW_TOKENS
        
        # Format messages into prompt
        prompt = self._format_messages(messages)
        
        logger.debug(f"Calling LLM with temperature={temperature}, max_tokens={max_new_tokens}")
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode
            generated_text = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            )
            
            logger.debug(f"Generated {len(generated_text)} characters")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Format cursor-style messages into a single prompt.
        
        Args:
            messages: List of message dicts
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n".join(prompt_parts)
    
    def parse_json_output(self, text: str) -> Optional[Dict]:
        """
        Parse JSON from LLM output.
        
        Args:
            text: Generated text
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Try to find JSON in the output
        # Look for content between { and }
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            logger.error("No JSON found in output")
            return None
        
        json_str = text[start_idx:end_idx + 1]
        
        try:
            parsed = json.loads(json_str)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.debug(f"Failed JSON string: {json_str[:500]}")
            return None
