import os
from openai import OpenAI
from dotenv import load_dotenv
import base64
from prompt import PROMPT_TEXT

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


# 로컬 이미지 열기
def analyze_image(img_path):

    with open(img_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    prompt = PROMPT_TEXT

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                },
            ],
        }],
    )

    text = response.output[0].content[0].text

    return text