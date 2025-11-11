"""Base Agent class for Prodigy VP agents."""

import json
import os
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables once at module level
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in your .env file")

# Initialize OpenAI client once at module level
_client = OpenAI(api_key=OPENAI_API_KEY)


class BaseAgent(ABC):
    """
    Base class for all Prodigy VP agents.
    
    Handles common infrastructure:
    - OpenAI client initialization
    - Schema loading and validation
    - LLM API calls with retry logic
    - JSON parsing with error handling
    """

    def __init__(
        self,
        agent_name: str,
        schema_file: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """
        Initialize BaseAgent.
        
        Args:
            agent_name: Name of the agent (e.g., "VP of Market & Strategy")
            schema_file: Name of schema file in /schemas/ directory
            model_name: OpenAI model to use (default: from env or gpt-4o)
            temperature: Temperature for LLM calls (default: 0.7)
        """
        self.agent_name = agent_name
        self.model = model_name or OPENAI_MODEL
        self.temperature = temperature
        self.schema_file = schema_file
        self.schema = self._load_schema(schema_file)
        self.client = _client

    def _load_schema(self, schema_file: str) -> Dict[str, Any]:
        """
        Load schema from /schemas/ directory.
        
        Args:
            schema_file: Name of schema file (e.g., "market_schema.json")
            
        Returns:
            Schema dict, or empty dict if not found
        """
        try:
            schema_path = Path(__file__).parent.parent / "schemas" / schema_file
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            warnings.warn(f"Schema file not found: {schema_file}", UserWarning)
            return {}
        except json.JSONDecodeError as e:
            warnings.warn(f"Failed to parse schema {schema_file}: {e}", UserWarning)
            return {}

    def _validate_against_schema(self, data: Dict[str, Any]) -> None:
        """
        Validate data against schema (warn but don't crash).
        
        Args:
            data: Data to validate
        """
        if not self.schema:
            return
        
        try:
            jsonschema.validate(instance=data, schema=self.schema)
        except jsonschema.ValidationError as e:
            warnings.warn(
                f"Schema validation failed for {self.agent_name}: {e.message}",
                UserWarning,
            )
        except Exception as e:
            warnings.warn(
                f"Schema validation error for {self.agent_name}: {e}",
                UserWarning,
            )

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Call LLM with retry logic and JSON parsing.
        
        Args:
            system_prompt: System prompt for LLM
            user_prompt: User prompt for LLM
            max_retries: Maximum number of retry attempts
            
        Returns:
            Parsed JSON response as dict
            
        Raises:
            RuntimeError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                )

                content = response.choices[0].message.content
                result = json.loads(content)

                # Ensure agent name is set
                result.setdefault("agent", self.agent_name)

                # Validate against schema (warn but don't crash)
                self._validate_against_schema(result)

                return result

            except json.JSONDecodeError as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Failed to parse JSON response after {max_retries} attempts: {e}"
                    )
                warnings.warn(
                    f"JSON parse error (attempt {attempt + 1}/{max_retries}): {e}",
                    UserWarning,
                )
                continue

            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"LLM API call failed after {max_retries} attempts: {e}"
                    )
                warnings.warn(
                    f"API call error (attempt {attempt + 1}/{max_retries}): {e}",
                    UserWarning,
                )
                continue

        raise RuntimeError(f"Failed to get valid response after {max_retries} attempts")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        
        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    def build_user_prompt(
        self, project_brief: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build user prompt from project brief.
        
        Args:
            project_brief: Project brief dict
            context: Optional context from other agents
            
        Returns:
            User prompt string
        """
        pass

    @abstractmethod
    def summarize(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize full report into decision summary.
        
        Args:
            report: Full agent report
            
        Returns:
            Summary dict with key fields for aggregation
        """
        pass

    def analyze(
        self, project_brief: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze project brief and return report.
        
        Args:
            project_brief: Project brief dict
            context: Optional context from other agents
            
        Returns:
            Analysis report dict
        """
        system_prompt = self.get_system_prompt()
        user_prompt = self.build_user_prompt(project_brief, context)

        return self._call_llm(system_prompt, user_prompt)

