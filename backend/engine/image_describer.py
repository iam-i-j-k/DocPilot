import os
import re
import base64
import json
from typing import Any
from groq import Groq

class ImageDescriber:
    """
    Engine class that leverages Groq vision LLM to provide alternative descriptions of PDF images.
    Implements tool calling, text sanitization, error recovery and fallbacks.
    """

    def __init__(self, api_key: str = None):
        """
        Initializes the Groq client. Uses GROQ_API_KEY environment variable if not passed.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        # Note: Do not launch client at module import time; lazy-initialize to prevent startup crashes.
        self._client = None

    @property
    def client(self) -> Groq:
        """
        Property to support lazy initialization of the Groq client.
        """
        if not self._client:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is not defined in the environment or parameters.")
            self._client = Groq(api_key=self.api_key)
        return self._client

    def describe(self, image_path: str) -> str:
        """
        Performs image analysis via Groq vision models.
        First tries structured tool selection. Falls back to plain text prompting on errors, and 
        recovers descriptions from Groq's validation error 'failed_generation' field if present.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Selected image not found: {image_path}")
        
        # Determine image mime-type
        mime_type = "image/png"
        if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
            mime_type = "image/jpeg"

        # Encode image to Base64
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        image_data_url = f"data:{mime_type};base64,{encoded_image}"
        
        # Tool definition schema for structured visual description
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "submit_image_description",
                    "description": "Submits a professional description of the contents of an image.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Rigorous markdown description of objects, layouts, charts, and visible texts."
                            }
                        },
                        "required": ["description"]
                    }
                }
            }
        ]

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please provide an accurate and clean outline/description of the visual content in this image."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ]

        # Use Groq's recommended Llama-3.2 vision model
        model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

        try:
            # Step 1: Attempt structured Tool selection API call
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "submit_image_description"}},
                temperature=0.2
            )

            # Retrieve the tool outputs
            choice = response.choices[0]
            if choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                arguments = json.loads(tool_call.function.arguments)
                description = arguments.get("description", "")
                return self.sanitize(description)
            
            # Simple fallback content if tool calls is empty
            if choice.message.content:
                return self.sanitize(choice.message.content)

        except Exception as e:
            # Step 2: Extract from 'failed_generation' inside the exception if model validation failed
            recovered_desc = self._attempt_recovery_from_error(e)
            if recovered_desc:
                return self.sanitize(recovered_desc)

            # Step 3: Fall back to plain text vision call on general tool call error
            try:
                plain_response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.2
                )
                text_content = plain_response.choices[0].message.content or ""
                return self.sanitize(text_content)
            except Exception as final_err:
                # Return graceful fallback string is everything fails
                return f"[Image description unavailable: {str(final_err)}]"

        return "[No description extracted]"

    def sanitize(self, text: str, collapse_newlines: bool = True) -> str:
        """
        Collapses all carriage carriage returns and newlines into spaces, and reduces multiple 
        consecutive spaces down to a single whitespace character. Returns trimmed text.
        """
        def sanitize(self, text: str, collapse_newlines: bool = True) -> str:
            if not text:
                return ""
            if collapse_newlines:
                text = text.replace("\r\n", " ").replace("\n", " ")
                text = re.sub(r"\s+", " ", text)
            return text.strip()

    def _attempt_recovery_from_error(self, exc: Exception) -> str:
        """
        Attempts to parse error object attributes or JSON body to extract 'failed_generation'.
        """
        try:
            # Groq errors have 'body' or 'message' string representations of JSON
            exc_str = str(exc)
            
            # 1. Regex search for failed_generation inside error message
            match = re.search(r'"failed_generation"\s*:\s*"([^"]+)"', exc_str)
            if match:
                return match.group(1)
            
            # 2. Try JSON loading from error body properties if present
            if hasattr(exc, "body") and exc.body:
                if isinstance(exc.body, dict):
                    err_json = exc.body
                else:
                    err_json = json.loads(str(exc.body))
                
                # Dig nested properties
                if "error" in err_json and isinstance(err_json["error"], dict):
                    failed_gen = err_json["error"].get("failed_generation")
                    if failed_gen:
                        return str(failed_gen)
        except Exception:
            pass
        return ""
