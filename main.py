import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.config import settings
from bot.base import (
    download_tours_data,
    # residence_second_name,
    start,
    callback,
    callback_simple,
    cancel,
    question_ask,
    moderator_response,
    tour_choose,
    tour_description,
    tour_name,
    tour_passport,
    tour_phone,
    tour_finish,
    residence,
    transfer_1,
    send_notification,
)
from bot.base import (
    TOUR_PASSPORT,
    QUESTION_ASK,
    TOUR_CHOOSE,
    TOUR_DESCRIPTION,
    TOUR_NAME,
    TOUR_PHONE,
    TOUR_FINISH,
    RESIDENCE_1,
    RESIDENCE_2,
    TRANSFER_1,
    TRANSFER_2,
)

logging.basicConfig(
    format="%(levelname)s | %(name)s | %(asctime)s | %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)


def main() -> None:
    app = ApplicationBuilder().token(settings.TG_TOKEN).build()

    question_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback, pattern="question"),
        ],
        states={
            QUESTION_ASK: [MessageHandler(filters.TEXT, question_ask)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(question_conv_handler)
    app.add_handler(MessageHandler(filters.REPLY, moderator_response))
    tour_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback, pattern="tour"),
        ],
        states={
            TOUR_CHOOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tour_choose)],
            TOUR_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, tour_description)
            ],
            TOUR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tour_name)],
            TOUR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tour_phone)],
            TOUR_PASSPORT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, tour_passport)
            ],
            TOUR_FINISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, tour_finish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(tour_conv_handler)
    residence_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback, pattern="residence"),
        ],
        states={
            # RESIDENCE_1: [
            #     MessageHandler(filters.TEXT & ~filters.COMMAND, residence_second_name)
            # ],
            RESIDENCE_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, residence)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(residence_conv_handler)
    transfer_1_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback_simple, pattern="transfer_1"),
        ],
        states={
            TRANSFER_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_1)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(transfer_1_conv_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        CallbackQueryHandler(
            callback_simple,
            pattern="checklist|timing_1|transfer_1|timing_2|transfer_2|timing_3|transfer_3|timing_4|transfer_4|contacts",
        )
    )
    app.add_handler(CommandHandler("download", download_tours_data))
    app.add_handler(CommandHandler("send", send_notification))

    app.run_polling()


if __name__ == "__main__":
    main()
