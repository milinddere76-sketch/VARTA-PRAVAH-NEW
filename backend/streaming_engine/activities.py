import os, subprocess, asyncio, requests
from temporalio import activity
from video_renderer import create_video

@activity.defn
async def fetch_news_activity(channel_id: int) -> list:
    return [('ताज्या बातम्या: वार्ताप्रवाह न्यूज वर आपले स्वागत आहे.', 'Headline', 'Female', False)]

@activity.defn
async def generate_script_activity(input_data: list) -> str:
    return input_data[0][0]

@activity.defn
async def generate_voice_activity(script: str) -> str:
    return f'/app/videos/voice_{os.urandom(4).hex()}.mp3'

@activity.defn
async def generate_news_video_activity(data: tuple) -> str:
    # Forces support for the 4-item tuple (audio, ticker, anchor, breaking)
    return create_video(data)
