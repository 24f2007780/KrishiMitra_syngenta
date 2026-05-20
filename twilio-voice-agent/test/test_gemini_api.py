import os
from dotenv import load_dotenv
from google import genai

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    load_dotenv(os.path.join(_ROOT, ".env"))
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY/GOOGLE_API_KEY is missing or empty")

    client = genai.Client(api_key=api_key)

    print("Listing models...")
    for m in client.models.list():
        name = getattr(m, "name", None)
        methods = getattr(m, "supported_methods", None)
        print(f"- {name} | methods={methods}")

    print("\nTesting generateContent with gemini-2.5-flash...")
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello in one short sentence."
    )
    print("Response:", getattr(resp, "text", None))


if __name__ == "__main__":
    main()
