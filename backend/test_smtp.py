import asyncio
import os
from config import settings
from utils.email import send_email

async def test_smtp():
    print(f"SMTP_HOST: {settings.get('smtp.host')}")
    print(f"SMTP_PORT: {settings.get('smtp.port')}")
    print(f"SMTP_USER: {settings.get('smtp.user')}")
    print(f"SMTP_FROM: {settings.get('smtp.from_email')}")
    
    try:
        await send_email(
            to="talhafarooqgtx960@gmail.com",
            subject="Test from Accura",
            text_body="This is a test email to verify SMTP configuration.",
        )
        print("Test email sent successully!")
    except Exception as e:
        print(f"Failed to send test email: type={type(e).__name__}, error={e}")

if __name__ == "__main__":
    asyncio.run(test_smtp())
