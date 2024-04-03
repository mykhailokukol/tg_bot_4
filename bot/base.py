import logging

from pymongo import MongoClient
from telegram import (
    InlineKeyboardButton,
    KeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext
from telegram.constants import ParseMode

from bot.config import settings
from bot.keyboards import (
    start_keyboard,
    start_keyboard_without_tours,
    start_keyboard_pre_release,
)
from bot.services import (
    add_tour_participant,
    already_signed_up_for_tour,
    decrement_free_places,
    free_places_validation,
    get_all_tours,
    get_residence_info,
    tours_to_csv,
)

logging.basicConfig(
    format="%(levelname)s | %(name)s | %(asctime)s | %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

TOUR_CHOOSE, TOUR_DESCRIPTION, TOUR_NAME, TOUR_PHONE, TOUR_PASSPORT, TOUR_FINISH = (
    range(6)
)
QUESTION_ASK = 6
RESIDENCE_1, RESIDENCE_2 = 7, 8


mongo_client = MongoClient(settings.MONGODB_CLIENT_URL)
db = mongo_client["tele2"]


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if settings.STATEMENT == "pre-release":
        try:
            with open("media/invitation.mov", "rb") as file:
                text = "Рады приветствовать тебя в @TELE2_RLT_BOT\nСовсем скоро тут появится подробное расписание, информация о трансферах, проживании и многое другое.\nСейчас ты можешь посмотреть чек-лист, он поможет тебе ничего не забыть.\nЕсли у тебя остались вопросы, обратись к организаторам.\n\nА пока настройся на мероприятие вместе с героями Tele2!"
                markup = InlineKeyboardMarkup(start_keyboard_pre_release)
                await update.effective_chat.send_video(
                    caption=text,
                    video=file,
                    reply_markup=markup,
                    width=1920,
                    height=1080,
                )
        except Exception as e:
            log.error(e)

    elif settings.STATEMENT == "release":
        try:
            log.info(
                f"Пользователь {update.message.from_user.id} подключился к боту (или нажал /start)"
            )
        except AttributeError:
            pass

        if already_signed_up_for_tour(update.effective_chat.id, db):
            markup = InlineKeyboardMarkup(start_keyboard_without_tours)
        else:
            markup = InlineKeyboardMarkup(start_keyboard)
        await update.effective_chat.send_message(
            "Выберите раздел: ",
            reply_markup=markup,
        )


async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """No description needed"""
    await update.message.reply_text(
        "Прекращаем последнюю операцию.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def callback(
    update: Update,
    context: CallbackContext,
) -> None:
    query = update.callback_query
    answer = await query.answer()

    match query.data:
        case "tour":
            if already_signed_up_for_tour(update.effective_chat.id, db):
                await update.effective_chat.send_message(
                    "Вы уже записались на экскурсию"
                )
                return await start(update, context)

            tours = get_all_tours(db)
            if not tours:
                await update.effective_chat.send_message(
                    "Все места на экскурсии были забронированы.\n"
                    'В разделе "Контакты организаторов" обратитесь по номеру ответственного за экскурсии'
                )
                await start(update, context)
                return

            await update.effective_chat.send_message(
                "Ниже представлен список экскурсий, "
                "выберите интересующую, чтобы ознакомиться с содержанием"
            )
            markup = ReplyKeyboardMarkup([[tour["name"]] for tour in tours])
            await update.effective_chat.send_message(
                "Выберите экскурсию: ",
                reply_markup=markup,
            )
            return TOUR_DESCRIPTION
        case "question":
            await update.effective_chat.send_message(
                "Задайте свой вопрос: ", reply_markup=ReplyKeyboardRemove()
            )
            context.user_data["state"] = "question"
            return QUESTION_ASK
        case "residence":
            # from bot.keyboards import participants_keyboard

            # participants = db["participants"]
            # participants_markup = ReplyKeyboardMarkup(
            #     participants_keyboard(participants)
            # )
            await update.effective_chat.send_message(
                "Введите свои фамилию и имя: ",
                # reply_markup=participants_markup,
            )
            return RESIDENCE_2


async def callback_simple(
    update: Update,
    context: CallbackContext,
) -> None:
    query = update.callback_query
    answer = await query.answer()

    match query.data:
        case "checklist":
            with open("media/photos/3.png", "rb") as file:
                await update.effective_chat.send_photo(
                    caption="До начала конференции остаются считанные дни. Смотри чек-лист и проверь, готов ли ты действовать на опережение!\n"
                    "Рекомендуем взять с собой:\n"
                    "1. Паспорт и банковские карты\n"
                    "2. Комплект зарядных устройств, чтобы оставаться на связи\n"
                    "3. Одежду в соответствии с дресс-кодом (смотри информацию ниже). Не забудь посмотреть погоду и взять теплые вещи для прогулок по Северной столице.\n"
                    "4. Удобную обувь к твоим неповторимым образам.\n\n"
                    "Как и обещали, пара слов о дресс-коде. В дни конференции придерживайся Smart Casual, по-деловому, но без лишней строгости. "
                    "На время активной программы 11 апреля рекомендуем повседневный стиль. "
                    "В Casual прогулки и экскурсии точно пройдут с комфортом. "
                    "На гала-ужине действуй на опережение! Подбери образ, который точно скажет за тебя - ты лидер! "
                    "Дресс-код Coctail.\nА теперь действуй - собирай чемоданы и ничего не забудь!",
                    photo=file,
                )
                if settings.STATEMENT == "release":
                    await start(update, context)
        case "timing_1":
            await update.effective_chat.send_message(
                "Расписания дня приезда:\n1. ...\n2. ...\n3. ..."
            )
            await start(update, context)
        case "transfer_1":
            await update.effective_chat.send_message(
                "Информация по трансферу в день приезда:\nИнфо..."
            )
            await start(update, context)
        case "timing_2":
            await update.effective_chat.send_message(
                "Расписания 2 дня:\n1. ...\n2. ...\n3. ..."
            )
            await start(update, context)
        case "transfer_2":
            await update.effective_chat.send_message(
                "Информация по трансферу в 2 день:\nИнфо..."
            )
        case "timing_3":
            await update.effective_chat.send_message(
                "Расписания 3 дня:\n1. ...\n2. ...\n3. ..."
            )
            await start(update, context)
        case "transfer_3":
            await update.effective_chat.send_message(
                "Информация по трансферу в 3 день:\nИнфо..."
            )
            await start(update, context)
        case "timing_4":
            await update.effective_chat.send_message(
                "Расписания дня отъезда:\n1. ...\n2. ...\n3. ..."
            )
            await start(update, context)
        case "transfer_4":
            await update.effective_chat.send_message(
                "Информация по трансферу в день отъезда:\nИнфо..."
            )
            await start(update, context)
        case "contacts":
            await update.effective_chat.send_message(
                "Трансфер: Ольга Яршина +7 977 522 6352\n"
                "Экскурсии: Елена Богорад +7 911 952 4734\n"
                "Tele2: Екатерина Яркина +7 962 992 8409",
                reply_markup=ReplyKeyboardRemove(),
            )

            if settings.STATEMENT == "release":
                await start(update, context)
            return ConversationHandler.END


async def tour_choose(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    tours = get_all_tours(db)
    if not tours:
        await update.effective_chat.send_message(
            "Все места на экскурсии были забронированы.\n"
            'В разделе "Контакты организаторов" обратитесь по номеру ответственного за экскурсии'
        )
        await start(update, context)
        return ConversationHandler.END

    markup = ReplyKeyboardMarkup([[tour["name"]] for tour in tours])
    await update.effective_chat.send_message(
        "Выберите экскурсию: ",
        reply_markup=markup,
    )

    return TOUR_DESCRIPTION


async def tour_description(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    # Check for free places at chosen tour
    tour = free_places_validation(db, update.message.text)
    if not tour:
        await update.message.reply_text(
            "Набор на данную экскурсию завершен, пожалуйста, выберите другую"
        )
        return TOUR_CHOOSE

    context.user_data["tour_name"] = tour["name"]
    if tour["name"].startswith("Прогулки в Зените"):
        context.user_data["tour_zenith"] = True

    markup = ReplyKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Записаться на экскурсию"),
                InlineKeyboardButton("Назад", callback_data="tour"),
            ],
        ]
    )
    await update.message.reply_text(
        text=tour["description"], reply_markup=markup, parse_mode=ParseMode.HTML
    )
    return TOUR_NAME


async def tour_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if update.message.text == "Записаться на экскурсию":
        # Check for free places at chosen tour
        tour = free_places_validation(db, context.user_data["tour_name"])
        if not tour:
            await update.message.reply_text(
                "Набор на данную экскурсию завершен, пожалуйста, выберите другую"
            )
            return TOUR_CHOOSE

        await update.message.reply_text(
            "<b>Заполните анкету: </b>", parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(
            "(1/2) Введите свои фамилию и имя: ", reply_markup=ReplyKeyboardRemove()
        )

        return TOUR_PHONE
    else:
        await update.message.reply_text(reply_markup=ReplyKeyboardRemove(), text="🔙")
        await start(update, context)
        return ConversationHandler.END


async def tour_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    # Check for free places at chosen tour
    tour = free_places_validation(db, context.user_data["tour_name"])
    if not tour:
        await update.message.reply_text(
            "Набор на данную экскурсию завершен, пожалуйста, выберите другую"
        )
        return TOUR_CHOOSE

    context.user_data["tour_user_name"] = update.message.text

    await update.message.reply_text(
        "(2/2) Укажите свой номер телефона: ", reply_markup=ReplyKeyboardRemove()
    )

    return TOUR_FINISH


async def tour_passport(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    # Check for free places at chosen tour
    tour = free_places_validation(db, context.user_data["tour_name"])
    if not tour:
        await update.message.reply_text(
            "Набор на данную экскурсию завершен, пожалуйста, выберите другую"
        )
        return TOUR_CHOOSE

    context.user_data["tour_user_passport"] = update.message.text

    context.user_data["user_id"] = update.message.from_user.id

    print(context.user_data)

    decrement_free_places(context.user_data["tour_name"], db)
    add_tour_participant(db, context.user_data)

    await update.message.reply_text(
        "Ваша заявка принята.\n"
        "<b>Актуальную</b> информацию по месту и времени экскурсии Вы сможете найти в разделе «Тайминг 11.04»\n"
        "Информацию по трансферу до места встречи Вы сможете найти в разделе «Трансфер 11.04».\n"
        "Обязательно ознакомьтесь с перечнем необходимых вещей для экскурсии в разделе «чек-лист».\n"
        "Для дополнительного подтверждения с Вами может связаться ответственный по телефону.\n",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )
    await start(update, context)

    return ConversationHandler.END


async def tour_finish(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    if (
        "tour_zenith" in context.user_data
        and not "tour_user_phone" in context.user_data
    ):
        context.user_data["tour_user_phone"] = update.message.text
        await update.message.reply_text(
            "(ОБЯЗАТЕЛЬНО) Укажите свои паспортные данные. Они необходимы для подачи списков на экскурсию: ",
            reply_markup=ReplyKeyboardRemove(),
        )
        return TOUR_PASSPORT
    else:
        context.user_data["tour_user_phone"] = update.message.text

    # Check for free places at chosen tour
    tour = free_places_validation(db, context.user_data["tour_name"])
    if not tour:
        await update.message.reply_text(
            "Набор на данную экскурсию завершен, пожалуйста, выберите другую"
        )
        return TOUR_CHOOSE

    context.user_data["user_id"] = update.message.from_user.id

    log.info(
        f"Пользователь {context.user_data['user_id']} "
        f"записался на экскурсию {context.user_data['tour_name']}"
    )

    decrement_free_places(context.user_data["tour_name"], db)
    add_tour_participant(db, context.user_data)

    await update.message.reply_text(
        "Ваша заявка принята.\n"
        "<b>Актуальную</b> информацию по месту и времени экскурсии Вы сможете найти в разделе «Тайминг 11.04»\n"
        "Информацию по трансферу до места встречи Вы сможете найти в разделе «Трансфер 11.04».\n"
        "Обязательно ознакомьтесь с перечнем необходимых вещей для экскурсии в разделе «чек-лист».\n"
        "Для дополнительного подтверждения с Вами может связаться ответственный по телефону.\n",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )
    await start(update, context)

    return ConversationHandler.END


async def question_ask(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    question = update.message
    if question.text.startswith("/"):
        await update.message.reply_text(
            "Прекращаем последнюю операцию.", reply_markup=ReplyKeyboardRemove()
        )
        return await start(update, context)
    await context.bot.send_message(
        chat_id=settings.MODERATOR_ID,
        text=f"Ответьте на вопрос: \n{question.text}\n\n> {question.from_user.id}",
    )
    await update.message.reply_text(
        "Ваш вопрос направлен модератору. Пожалуйста, дождитесь ответа"
    )
    log.info(f"Задан вопрос: {question.text} [{question.from_user.id}]")
    return ConversationHandler.END


async def moderator_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if int(update.message.from_user.id) != int(settings.MODERATOR_ID):
        return QUESTION_ASK

    text = update.message.reply_to_message.text.split("> ")[0][:-2].split("\n")[1]
    reply_text = update.message.text
    user_id = update.message.reply_to_message.text.split("> ")[1]

    await context.bot.send_message(
        text="Модератор ответил на Ваш вопрос.\n",
        chat_id=user_id,
    )
    await context.bot.copy_message(
        message_id=update.message.message_id,
        chat_id=user_id,
        from_chat_id=update.message.chat_id,
    )
    await context.bot.send_message(
        text='Если у Вас появятся новые вопросы, нажмите на кнопку "Задать вопрос"',
        chat_id=user_id,
    )

    log.info(f"На вопрос {text} [{user_id}] получен ответ: {reply_text}")


# async def residence_second_name(
#     update: Update,
#     context: ContextTypes.DEFAULT_TYPE,
# ) -> int:
#     print("residence_second_name")
#     user_name = update.message.text
#     if user_name.lower().startswith("щербакова елена"):
#         context.user_data["residence_name"] = user_name
#         await update.message.reply_text(
#             "Введите отчество: ", reply_markup=ReplyKeyboardRemove()
#         )
#     return RESIDENCE_2


async def residence(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    print("residence")
    try:
        user_name = update.message.text
        info = get_residence_info(db, user_name, "hotel_website")
        # for i in info: reply_text
        await update.message.reply_text(
            f"<b>{user_name}</b>\n" "Детали проживания: ",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        log.info(f"У {user_name} просмотрены детали проживания")
    except TypeError:
        info = "Данные ФИО не найдены. Проверьте, пожалуйста, на корректность отправленные данные и повторите запрос в разделе «Проживание» или задайте вопрос в разделе «Задать вопрос»"

    await update.message.reply_text(text=info)

    if settings.STATEMENT == "release":
        await start(update, context)
    return ConversationHandler.END


async def download_tours_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if int(update.message.from_user.id) == int(settings.MODERATOR_ID):
        await tours_to_csv(db, update)
