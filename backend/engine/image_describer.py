import os
import re
import base64
import json
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
        # Lazy-initialize to prevent startup crashes if key is missing at import time.
        self._client = None

    @property
    def client(self) -> Groq:
        """
        Lazy initialization of the Groq client.
        """
        if not self._client:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is not defined in the environment or parameters.")
            self._client = Groq(api_key=self.api_key)
        return self._client

    def describe(self, image_path: str) -> str:
        """
        Performs image analysis via Groq vision model.
        Step 1: Structured tool call.
        Step 2: Recover description from failed_generation in error body.
        Step 3: Plain text vision call fallback.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Selected image not found: {image_path}")

        # Determine mime type
        mime_type = "image/png"
        if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
            mime_type = "image/jpeg"

        # Encode image to Base64
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        image_data_url = f"data:{mime_type};base64,{encoded_image}"

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
                                "description": (
                                    "Rigorous description of objects, layouts, charts, "
                                    "and visible texts in the image."
                                )
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
                        "text": (
                            "Please provide an accurate and detailed description of the visual "
                            "content in this image. Avoid using apostrophes or single quotes."
                        )
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

        model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

        try:
            # Step 1: Structured tool call
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "submit_image_description"}},
                temperature=0.2
            )

            choice = response.choices[0]

            if choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                arguments = json.loads(tool_call.function.arguments)
                description = arguments.get("description", "")
                return self.sanitize(description)

            # Tool call was skipped, model replied in plain text
            if choice.message.content:
                return self.sanitize(choice.message.content)

        except Exception as e:
            # Step 2: Groq's tool_use_failed error contains the actual description
            # in the failed_generation field — recover it before falling back
            recovered_desc = self._attempt_recovery_from_error(e)
            if recovered_desc:
                return self.sanitize(recovered_desc)

            # Step 3: Plain text vision call — no tools
            try:
                plain_response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.2
                )
                text_content = plain_response.choices[0].message.content or ""
                return self.sanitize(text_content)
            except Exception as final_err:
                return f"[Image description unavailable: {str(final_err)}]"

        return "[No description extracted]"

    def sanitize(self, text: str, collapse_newlines: bool = True) -> str:
        """
        Collapses carriage returns and newlines into spaces, reduces multiple
        consecutive spaces to a single whitespace character. Returns trimmed text.
        """
        if not text:
            return ""
        if collapse_newlines:
            text = text.replace("\r\n", " ").replace("\n", " ")
            text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _attempt_recovery_from_error(self, exc: Exception) -> str:
        """
        Attempts to extract a usable description from Groq's failed_generation
        error field, which contains the model output that failed JSON validation.
        """
        try:
            # Primary: parse from exc.body if it's a structured dict
            if hasattr(exc, "body") and exc.body:
                err_json = exc.body if isinstance(exc.body, dict) else json.loads(str(exc.body))
                if "error" in err_json and isinstance(err_json["error"], dict):
                    failed_gen = err_json["error"].get("failed_generation")
                    if failed_gen:
                        # failed_generation is a JSON array string:
                        # [{"name": "submit_image_description", "parameters": {"description": "..."}}]
                        try:
                            parsed = json.loads(failed_gen)
                            if isinstance(parsed, list) and parsed:
                                desc = parsed[0].get("parameters", {}).get("description", "")
                                if desc:
                                    return desc
                        except json.JSONDecodeError:
                            pass
                        # If JSON parse fails, return the raw string for sanitize to clean
                        return str(failed_gen)

            # Fallback: regex search directly on the stringified exception
            exc_str = str(exc)
            match = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)+)"', exc_str)
            if match:
                return match.group(1).replace('\\"', '"').replace("\\'", "'")

        except Exception:
            pass

        return ""