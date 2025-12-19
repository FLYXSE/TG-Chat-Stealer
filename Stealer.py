import os
import re
import asyncio
from datetime import timezone
import logging

from pyrogram import Client
from pyrogram.enums import ChatType
from tqdm import tqdm

from config import API_ID, API_HASH

# ---------------------------
# Подавляем фоновые ошибки Pyrogram
logging.getLogger("pyrogram").setLevel(logging.CRITICAL)
# ---------------------------

EXPORT_DIR = "exports"

def chat_folder_name(chat) -> str:
    """Генерируем безопасное имя папки: Name | @UserName | ID"""
    name = chat.title or getattr(chat, "first_name", "") or ""
    username = f"@{chat.username}" if chat.username else ""
    chat_id = str(chat.id)
    parts = [name, username, chat_id]
    folder_name = " | ".join(filter(None, parts))
    return re.sub(r'[\\/:*?"<>|]', "_", folder_name)

def safe_filename(text: str) -> str:
    """Делаем безопасное имя файла"""
    return re.sub(r'[\\/:*?"<>|]', "_", text or "")

app = Client(
    name="userbot_export",
    api_id=API_ID,
    api_hash=API_HASH,
    workdir=".",
    no_updates=True,
    sleep_threshold=30
)

async def export_chat(chat):
    """Экспорт одного чата в TXT с медиа"""
    folder = chat_folder_name(chat)
    chat_dir = os.path.join(EXPORT_DIR, folder)
    media_dir = os.path.join(chat_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    txt_path = os.path.join(chat_dir, "chat.txt")

    total = await app.get_chat_history_count(chat.id)

    with open(txt_path, "w", encoding="utf-8") as f:
        with tqdm(total=total, desc=f"Экспорт: {folder}", unit="msg") as pbar:
            async for msg in app.get_chat_history(chat.id):
                pbar.update(1)
                if not msg.date:
                    continue

                date = msg.date.astimezone(timezone.utc)
                timestamp = date.strftime("%d.%m.%y %H:%M")
                sender = msg.from_user.first_name if msg.from_user else "Deleted"

                content = ""

                if msg.text:
                    content = msg.text
                else:
                    # Медиа: Photo, Video, Audio, Voice, Document
                    media = msg.photo or msg.video or msg.audio or msg.voice or msg.document
                    if media:
                        # Определяем расширение
                        ext = ""
                        if hasattr(media, "file_name") and media.file_name:
                            ext = os.path.splitext(media.file_name)[1]
                        elif hasattr(media, "mime_type") and media.mime_type:
                            ext = "." + media.mime_type.split("/")[-1]

                        # Уникальное имя
                        fname = f"{msg.id}_{type(media).__name__}_{media.file_unique_id[:8]}{ext}"
                        path = await msg.download(file_name=os.path.join(media_dir, fname))
                        content = fname if path else "[media error]"

                f.write(f"{sender}, [{timestamp}] {content}\n")

async def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    print("🚀 Экспорт чатов в TXT с медиа\n")

    async for dialog in app.get_dialogs():
        chat = dialog.chat
        if chat.type not in (ChatType.PRIVATE, ChatType.GROUP):
            continue
        if chat.username:
            continue  # пропускаем публичные
        try:
            await export_chat(chat)
        except Exception as e:
            print(f"❌ Ошибка в чате {chat.id}: {e}")

    print("\n✅ Экспорт завершён.")

async def runner():
    async with app:
        await main()

if __name__ == "__main__":
    asyncio.run(runner())