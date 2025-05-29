import os
from openai import OpenAI
from dotenv import load_dotenv
import base64

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


# 로컬 이미지 열기
def analyze_image(img_path):

    with open(img_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    prompt = """
    다음 이미지를 분석해서 차량의 불법 적재 여부를 아래 기준에 따라 판정해줘.

    1. 먼저 '적재불량 차량'인지 여부를 "예" 또는 "아니오"로 명확히 판단해줘.
    2. 만약 '적재불량 차량'이면, 어떤 유형(아래 6가지 중 하나 이상)인지와, 적재불량의 구체적 위험 내용을 반드시 포함해 설명해줘.
    3. 차량이 적재불량이 아니라면 "적재불량이 아닙니다"라고 명확히 답해줘.
    4. 만약 이미지 품질, 각도, 가림, 해상도 등으로 판정이 어려우면 "판단이 어렵습니다"라고만 답변해줘.
    5. 아래 유형 이외에 다른 위험 적재가 있으면 "기타"로 분류해줘.

    [적재불량 차량 세부 유형]
    1. 편중적재 : 적재물이 한쪽으로 쏠린 차량
    2. 결속상태불량 : 덮개, 끈, 로프 등으로 고정이 불충분한 차량
    3. 적재함 청소 불량 : 적재함 내부에 이물질 또는 잡물이 남아있는 차량
    4. 덮개 미설치 : 흙, 자갈 등 덮개 없이 운반하는 차량
    5. 액체 방류 : 기름, 물 등 액체가 흘러내릴 우려가 있는 차량
    6. 기타 적재물 낙하 우려 차량

    **[답변 예시]**
    - 적재불량 여부: 예
    - 적재불량 유형: 결속상태불량, 덮개 미설치
    - 적재물 위험 설명: 적재물이 확실히 고정되어 있지 않고, 덮개가 없어 낙하 위험이 있음.

    또는

    - 적재불량 여부: 아니오
    - 적재불량 유형: 없음
    - 적재물 위험 설명: 해당 없음

    또는

    - 판단이 어렵습니다 (설명 생략)
    """

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