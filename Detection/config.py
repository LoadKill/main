from dotenv import load_dotenv
import os
import requests


def get_cctv_stream_url():
    load_dotenv()
    api_key = os.getenv('ITS_API_KEY')
    api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=126.8&maxX=127.2&minY=37.4&maxY=37.7&getType=json"
    response = requests.get(api_url).json()

    return response['response']['data'][0]['cctvurl']