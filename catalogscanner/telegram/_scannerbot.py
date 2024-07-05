import asyncio
import logging
from functools import reduce
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from telegram import Document, File, PhotoSize, Update, Video
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes, ExtBot, MessageHandler, filters

from catalogscanner.common import ScanResult
from catalogscanner.scanner import scan_media
from catalogscanner.telegram.common import TG_MAX_DOWNLOAD_SIZE, sel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class ScannerBot:
    def __init__(self, admins: list[int | str] = [], local_mode: bool = False) -> None:
        self.logger = logging.getLogger(__name__)
        self.local_mode = local_mode
        self.admins = [int(admin) for admin in admins]

        self.bot: ExtBot = None  # type: ignore[type-arg, assignment]

    def setup_hooks(self, application: Application) -> None:  # type: ignore[type-arg]
        file_filter = filters.PHOTO | filters.VIDEO | filters.Document.IMAGE | filters.Document.VIDEO
        admin_filter = None

        if self.admins:
            user_filters = [filters.User(user) for user in self.admins]
            multi_user_filter = user_filters[0]
            if len(user_filters) > 1:
                multi_user_filter = reduce(lambda x, y: x | y, user_filters)  # type: ignore[arg-type, return-value]

            admin_filter = filters.ChatType.PRIVATE & multi_user_filter
            file_filter = admin_filter & file_filter

        application.add_handler(CommandHandler("start", self.start, filters=admin_filter, block=False))
        application.add_handler(MessageHandler(file_filter, self.receive_media, block=False))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Received start command from: {update.effective_user.full_name}")

        text = """<b>Animal Crossing: New Horizons Catalog Scanner Bot</b>

        👋 Hello! I'm here to extract all your Items, DIY Recipes, Critters, Music and Reactions from your Animal Crossing: New Horizons screenshots and videos.

        🎉 You can then import them to your preferred ACNH cataloging tool.

        <a href="https://telegra.ph/Animal-Crossing-New-Horizons-Catalog-Scanner-07-05"><b>➡️➡️ Instructions ⬅️⬅️</b></a>"""

        await update.message.reply_text(sel(text), parse_mode="HTML")

    async def prepare_file_for_download(self, media: PhotoSize | Video | Document) -> File:
        if not media.file_size:
            raise ValueError("File size is not available")
        elif not self.local_mode and media.file_size > TG_MAX_DOWNLOAD_SIZE:
            raise ValueError("File size is too large")

        file = await media.get_file()
        if not file.file_path:
            raise ValueError("File name is not available")
        elif Path(file.file_path).suffix not in [".jpg", ".jpeg", ".mp4"]:
            raise ValueError("File type is not supported, supported types are: jpg, jpeg, mp4")

        return file

    async def download_file(self, file: File, destination: Path | None = None) -> Path:
        path = Path(file.file_path)  # type: ignore[arg-type]
        if self.local_mode and path.exists():
            return path

        if not destination:
            raise ValueError("Destination path is not provided")

        out = BytesIO()
        await file.download_to_memory(out)
        out.seek(0)
        hash = sha256(out.getvalue()).hexdigest()
        destination = destination / f"{hash}{path.suffix}"
        destination.write_bytes(out.getvalue())
        return destination

    async def get_file(self, media: PhotoSize | Video | Document, destination: Path | None = None) -> Path:
        file = await self.prepare_file_for_download(media)
        return await self.download_file(file, destination=destination)

    async def process_media(self, update: Update, photo: PhotoSize | Video | Document) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Processing media from: {update.effective_user.full_name}, type: {type(photo).__name__}")

        reply_message_id = update.message.message_id
        answer = await update.message.reply_text("Processing media...", reply_to_message_id=reply_message_id)

        with TemporaryDirectory() as temp_dir:
            path = await self.get_file(photo, destination=Path(temp_dir))
            self.logger.info(f"File saved at: {path}")

            try:
                result = await self.scan_media(path)
            except AssertionError as e:
                self.logger.error(f"Failed to scan media, error: {e}")
                await answer.edit_text(f"Failed to scan media! {e.args[0]}")
                return
            except Exception as e:
                self.logger.error(f"Failed to scan media, error: {e}")
                await answer.edit_text("Failed to scan media!")
                return
            self.logger.info("Media scanned!")

            if not result:
                await answer.edit_text("No results found!")

            result_file = Path(temp_dir) / "result.txt"
            result_file.write_text("\n".join(result.items))

            caption = f"Mode: {result.mode.name}\nLocale: {result.locale}\nTotal: {len(result.items)}\nUnmatched: {len(result.unmatched)}"

            try:
                await answer.delete()
            except BadRequest:
                pass

            await update.message.reply_document(result_file, caption=caption)

    async def scan_media(self, path: Path) -> ScanResult:
        return await asyncio.to_thread(scan_media, path)

    async def receive_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Received media from: {update.effective_user.full_name}")

        media = update.message.effective_attachment
        if isinstance(media, (list, tuple)):
            await self.process_media(update, media[-1])
        elif isinstance(media, (Video, Document)):
            await self.process_media(update, media)
        else:
            self.logger.error(f"Unsupported media type: {type(media).__name__}")

    async def post_init(self, app: Application) -> None:  # type: ignore[type-arg]
        self.app = app
        self.bot = app.bot

        await self.bot.set_my_commands([("start", "Start the bot")])

        for admin in self.admins:
            try:
                await self.bot.send_message(admin, "Bot started!")
            except BadRequest as e:
                self.logger.error(f"Failed to send message to admin: {admin}, error: {e}")

    async def post_stop(self, app: Application) -> None:  # type: ignore[type-arg]
        for admin in self.admins:
            try:
                await self.bot.send_message(admin, "Bot stopped!")
            except BadRequest as e:
                self.logger.error(f"Failed to send message to admin: {admin}, error: {e}")
