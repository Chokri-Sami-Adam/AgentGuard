
import requests

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_BASE_URL
)


def send_message(prompt: str) -> str:
    """
    Send a prompt to an AI model through OpenRouter.
    Returns the model's response.
    """

    url = f"{OPENROUTER_BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "AgentGuard"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:
        raise RuntimeError("The AI API request timed out.")

    except requests.exceptions.HTTPError as error:
        status = error.response.status_code
        raise RuntimeError(
            f"OpenRouter returned HTTP {status}. "
            "Check your API key, model and account credits."
        )

    except (KeyError, IndexError, ValueError):
        raise RuntimeError("Invalid response received from OpenRouter.")

    except requests.exceptions.RequestException:
        raise RuntimeError("Could not connect to OpenRouter.")
