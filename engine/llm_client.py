
import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL


def send_message(prompt: str) -> str:
    """
    Send a prompt to a local AI model through Ollama.
    Returns the model's response.
    """

    url = f"{OLLAMA_BASE_URL}/api/chat"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=120
        )

        response.raise_for_status()
        data = response.json()

        return data["message"]["content"]

    except requests.exceptions.Timeout:
        raise RuntimeError("The Ollama request timed out.")

    except requests.exceptions.HTTPError as error:
        status = error.response.status_code
        raise RuntimeError(
            f"Ollama returned HTTP {status}. "
            "Check that the model is installed."
        )

    except (KeyError, ValueError):
        raise RuntimeError("Invalid response received from Ollama.")

    except requests.exceptions.RequestException:
        raise RuntimeError("Could not connect to Ollama.")
