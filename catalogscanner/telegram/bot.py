import argparse
import logging
from uuid import uuid4

from telegram import Update
from telegram.ext import ApplicationBuilder, PicklePersistence

from catalogscanner.telegram._scannerbot import ScannerBot
from catalogscanner.telegram.common import TG_BASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def bot_main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    # Typical local path: "http://localhost:8081/bot"
    parser.add_argument("--base-url", default=TG_BASE_URL, help="Base URL for the bot API")
    parser.add_argument("--local-mode", action="store_true", help="Run the bot in local mode", default=False)
    parser.add_argument("--admins", required=True, help="List of admin ids, separated by commas.")

    sub_parsers = parser.add_subparsers()
    webhook_parser = sub_parsers.add_parser("webhook")
    webhook_parser.add_argument("--webhook-url", required=True)
    webhook_parser.add_argument("--webhook-path", default="")
    webhook_parser.add_argument("--listen", default="0.0.0.0")
    webhook_parser.add_argument("--port", type=int, default=8433)

    webhook_parser.set_defaults(webhook=True)

    args = parser.parse_args()

    bot = ScannerBot(admins=args.admins.split(","), local_mode=args.local_mode)

    persistence = PicklePersistence(filepath="scanner_bot.dat")
    app = (
        ApplicationBuilder()
        .token(args.token)
        .persistence(persistence)
        .arbitrary_callback_data(True)
        .post_init(bot.post_init)
        .post_stop(bot.post_stop)
        .base_url(args.base_url)
        .local_mode(args.local_mode)
        .build()
    )

    bot.setup_hooks(app)

    if hasattr(args, "webhook"):
        app.run_webhook(
            listen=args.listen,
            port=args.port,
            webhook_url=args.webhook_url,
            url_path=args.webhook_path,
            secret_token=uuid4().hex,
        )
    else:
        app.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    try:
        bot_main()
    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main()
