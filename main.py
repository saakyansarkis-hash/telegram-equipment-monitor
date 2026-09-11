import os
from telethon import TelegramClient, events

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
client = TelegramClient("monitor", api_id, api_hash)
keywords = [
"нужен экскаватор-погрузчик",
"ищу экскаватор-погрузчик",
"экскаватор-погрузчик",
"нужен каток",
"нужен самосвал",
"нужны самосвалы",
"ищу самосвал",
"требуется самосвал",
"нужен мини-погрузчик",
"нужен мини погрузчик",
"ищу мини-погрузчик",
"ищу мини погрузчик",
"требуется мини-погрузчик",]
@client.on(events.NewMessage)
async def handler(event):
   text = (event.message.message or "").lower()
  for word in keywords:
       if word in text:
         print("Найдена заявка:")
         print(event.message.message)
         break
client.start()
client.run_until_disconnected()
