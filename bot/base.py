import logging

from pymongo import MongoClient
from telegram import (
    InlineKeyboardButton,
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
    get_notification,
    get_residence_info,
    get_tour_users,
    tours_to_csv,
    get_transfer_in_info,
    add_user_to_db,
)

logging.basicConfig(
    format="%(levelname)s | %(name)s | %(asctime)s | %(message)s",
    level=logging.WARN,
    filemode="a",
    filename="logs/warn.log",
    encoding="utf-8",
)
log = logging.getLogger(__name__)

TOUR_CHOOSE, TOUR_DESCRIPTION, TOUR_NAME, TOUR_PHONE, TOUR_PASSPORT, TOUR_FINISH = (
    range(6)
)
QUESTION_ASK = 6
RESIDENCE_1, RESIDENCE_2 = 7, 8
TRANSFER_1, TRANSFER_2 = 9, 10
NOTIFICATIONS_1, NOTIFICATIONS_2 = 11, 12


mongo_client = MongoClient(settings.MONGODB_CLIENT_URL)
db = mongo_client["tele2"]


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if settings.STATEMENT == "pre-release":
        add_user_to_db(db, update.message.from_user.id)
        try:
            with open("media/invitation.mov", "rb") as file:
                text = "Рады приветствовать тебя в @TELE2_RLT_BOT\nВ разделах ты можешь посмотреть подробное расписание, информацию о трансферах, проживании и многое другое.\nСмотри чек-лист, он поможет тебе ничего не забыть.\nЕсли у тебя остались вопросы, обратись к организаторам.\n\nА пока настройся на мероприятие вместе с героями Tele2!"
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

        add_user_to_db(db, update.message.from_user.id)

        already = already_signed_up_for_tour(update.effective_chat.id, db)
        if already:
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
            already = already_signed_up_for_tour(update.effective_chat.id, db)
            if already:
                await update.effective_chat.send_message(
                    f"Вы уже записались на экскурсию {already}"
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
            markup = ReplyKeyboardMarkup(
                [
                    [tour["name"]]
                    for tour in tours
                    # if not tour["name"].startswith("Прогулки в Зените")
                ]
            )
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
                # if settings.STATEMENT == "release":
                #     await start(update, context)
        case "timing_1":
            await update.effective_chat.send_message(
                "<b>Тайминг 09.04</b>\n\n"
                "<b>14:00 – 22:00</b> Сбор участников. Заселение в отели\n\n"
                "<b>19:00 – 22:00</b> Ужин в ресторане Борсалино, отель Англетер, ул. Малая Морская, д. 24",
                parse_mode=ParseMode.HTML,
            )
            # await start(update, context)
        case "transfer_1":
            await update.effective_chat.send_message(
                "Введите свои фамилию и имя: ",
            )
            return TRANSFER_1
        case "timing_2":
            await update.effective_chat.send_message(
                "<b>Тайминг 10.04</b>\n\n"
                "<b>07:00 – 09:00</b> Завтрак в отеле проживания\n\n"
                "<b>09:00 – 09:20</b> Отправление трансферов на конференцию. Манеж Первого кадетского корпуса, Университетская набережная, д. 13. Посадка у центрального входа отелей Астория и SO\n\n"
                "<b>09:30 – 09:55</b> Сбор и регистрация участников. Welcome кофе\n\n"
                "<b>09:55 – 10:00</b> Открытие конференции\n\n"
                "<b>10:00 – 11:00</b> Антон Годовиков, генеральный директор\n\n"
                "<b>11:00 – 11:50</b> Ирина Лебедева, заместитель генерального директора по коммерческой деятельности\n\n"
                "<b>11:50 – 12:10</b> Кофе-брейк\n\n"
                "<b>12:10 – 12:50</b> Ольга Свечникова, директор по маркетингу\n\n"
                "<b>12:50 – 13:15</b> Q&A. Свои вопросы можно задать в соответствующем разделе бота\n\n"
                "<b>13:15 – 14:15</b> Обед. Манеж Первого кадетского корпуса, 2-3 этаж\n\n"
                "<b>14:15 – 14:45</b> Алексей Дмитриев, технический директор\n\n"
                "<b>14:45 – 15:30</b> Елена Иванова, заместитель генерального директора по организационному развитию и управлению персоналом\n\n"
                "<b>15:30 – 16:00</b> Кофе-брейк\n\n"
                "<b>16:00 – 18:00</b> Пленарная сессия\n\n"
                "<b>18:00 – 18:15</b> Заключительное слово генерального директора\n\n"
                "<b>18:15 – 18:45</b> Отправление трансферов на ужин. STROGANOFF STEAK HOUSE, Конногвардейский бульвар, д. 4\n\n"
                "<b>19:00 – 23:00</b> Ужин\n\n"
                "<b>22:00 – 23:15</b> Трансфер в отели, время отправления шаттлов в разделе «Трансфер 10.04» ",
                parse_mode=ParseMode.HTML,
            )
            # await start(update, context)
        case "transfer_2":
            await update.effective_chat.send_message(
                "Трансфер 10.04.\n\n"
                "<b>09:00 - 09:20</b>\nОтправление трансферов на конференцию от центрального входа отелей Астория и SO по месту проживания.\n\n"
                "<b>18:15 - 18:45</b>\nОтправление трансферов от Манежа Первого кадетского корпуса на ужин.\n\n"
                "<b>22:00 - 23:15</b>\nОтправление трансферов от ресторана в отель:\n<b>22:00\n22:30\n23:00</b>",
                parse_mode=ParseMode.HTML,
            )
        case "timing_3":
            await update.effective_chat.send_message(
                "<b>Тайминг 11.04</b>\n\n"
                "<b>07:00 – 11:00</b> Завтрак в отеле проживания\n\n"
                "<b>10:30 – 17:00</b> Экскурсионная программа по предварительной записи. Выбери удобное время и программу в разделе «Запись на экскурсию». Сбор экскурсионных групп у центрального входа отеля Астория, время отправления в разделе «Трансфер 11.04»\n\n"
                "<b>13:00 – 15:00</b> Обед в отеле проживания\n\n"
                "<b>19:00 – 19:15</b> Отправление трансферов на гала-ужин. LOFT HALL, Арсенальная наб., д. 1,время отправления шаттлов в разделе «Трансфер 11.04»\n\n"
                "<b>19:30 – 20:00</b> Сбор гостей, Welcome\n\n"
                "<b>20:00 – 20:15</b> Торжественное открытие гала-ужина\n\n"
                "<b>20:15 – 21:00</b> Церемония награждения\n\n"
                "<b>21:00 – 00:30</b> Развлекательная программа\n\n"
                "<b>00:30 – 03:30</b> Караоке\n\n"
                "<b>22:00 – 04:00</b> Трансфер в отели, время отправления шаттлов в разделе «Трансфер 11.04»",
                parse_mode=ParseMode.HTML,
            )
            # await start(update, context)
        case "transfer_3":
            await update.effective_chat.send_message(
                "Трансфер 11.04.\n<b>Сбор экскурсионных групп: центральный вход отеля Астория. <u>Время отправления от отеля:</u></b>\n"
                "10:40 Доходные дома, дворы и парадные + парадная Ромашка\n"
                "11:15 Юсуповский дворец. Парадные залы и экспозиция, посвященные Г. Распутину.\n"
                "11:00 Прогулки в Зените (стадион «Газпром Арена»)\n"
                "11:45 Дворец Елисеевых. Талион Клуб.\n"
                "11:30 Прогулки в Зените (стадион «Газпром Арена»)\n"
                "12:00 Музей Фаберже\n"
                "12:30 Особняк Брусницыных\n"
                "12:40 Прогулка по Михайловскому театру\n"
                "13:50 Особняк Половцова (Дом Архитектора)\n"
                "13:30 Прогулки в Зените (стадион «Газпром Арена»)\n"
                "13:40 Доходные дома, дворы и парадные + парадная Ромашка\n"
                "14:00 Музей Фаберже\n"
                "15:15 Юсуповский дворец (парадные залы и экспозиция, посвященная Г. Распутину)\n\n"
                "<b>19:00 – 19:15 Отправление трансферов на гала-ужин. LOFT HALL, Арсенальная наб., д. 1.\nПосадка у центрального входа отелей Англетер и SO</b>\n\n"
                "<b>22:00 – 03:30 LOFT HALL, Арсенальная наб., д. 1. – Отели Астория/Англетер/SO</b>\n"
                "Отправка шаттлов каждые 30 минут.",
                parse_mode=ParseMode.HTML,
            )
            # await start(update, context)
        case "timing_4":
            await update.effective_chat.send_message(
                "<b>Тайминг 12.04</b>\n\n"
                "<b>07:00 – 11:00</b> Завтрак в отеле проживания\n\n"
                "<b>12:00</b> Выселение из отелей\n\n"
                "<b>07:00 – 00:00</b> Трансферы в аэропорт/вокзал, время отправления шаттлов в разделе «Трансфер 12.04» <b>Если ты планируешь добираться самостоятельно, не забудь сообщить организаторам.</b>",
                parse_mode=ParseMode.HTML,
            )
            # await start(update, context)
        case "transfer_4":
            await update.effective_chat.send_message(
                "Информация по трансферу в день отъезда:\nИнфо..."
            )
            # await start(update, context)
        case "contacts":
            await update.effective_chat.send_message(
                "Трансфер: Ольга Яршина +7 977 522 6352\n"
                "Экскурсии: Елена Богорад +7 911 952 4734\n"
                "Tele2: Екатерина Яркина +7 962 992 8409",
                reply_markup=ReplyKeyboardRemove(),
            )

            # if settings.STATEMENT == "release":
            #     await start(update, context)
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
    # if tour["name"].startswith("Прогулки в Зените"):
    #     context.user_data["tour_zenith"] = True

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


# async def tour_passport(
#     update: Update,
#     context: ContextTypes.DEFAULT_TYPE,
# ) -> int:
#     # Check for free places at chosen tour
#     tour = free_places_validation(db, context.user_data["tour_name"])
#     if not tour:
#         await update.message.reply_text(
#             "Набор на данную экскурсию завершен, пожалуйста, выберите другую"
#         )
#         return TOUR_CHOOSE

#     context.user_data["tour_user_passport"] = update.message.text

#     context.user_data["user_id"] = update.message.from_user.id

#     decrement_free_places(context.user_data["tour_name"], db)
#     add_tour_participant(db, context.user_data)

#     await update.message.reply_text(
#         "Ваша заявка принята.\n"
#         "<b>Актуальную</b> информацию по месту и времени экскурсии Вы сможете найти в разделе «Тайминг 11.04»\n"
#         "Информацию по трансферу до места встречи Вы сможете найти в разделе «Трансфер 11.04».\n"
#         "Обязательно ознакомьтесь с перечнем необходимых вещей для экскурсии в разделе «чек-лист».\n"
#         "Для дополнительного подтверждения с Вами может связаться ответственный по телефону.\n",
#         parse_mode=ParseMode.HTML,
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     await start(update, context)

#     return ConversationHandler.END


async def tour_finish(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    # if (
    #     "tour_zenith" in context.user_data
    #     and not "tour_user_phone" in context.user_data
    # ):
    #     context.user_data["tour_user_phone"] = update.message.text
    #     await update.message.reply_text(
    #         "(ОБЯЗАТЕЛЬНО) Укажите свои паспортные данные. Они необходимы для подачи списков на экскурсию: ",
    #         reply_markup=ReplyKeyboardRemove(),
    #     )
    #     return TOUR_PASSPORT
    # else:
    # context.user_data["tour_user_phone"] = update.message.text
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
        f"Ваша заявка принята.\n"
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
        chat_id=1080268835,  # Speaker assissnant ID
        text=f"• Вопрос:\n<b>{question.text}</b>\n\n>От пользователя: {question.from_user.id}",
        parse_mode=ParseMode.HTML,
    )
    await update.message.reply_text("Ваш вопрос спикеру принят.")
    log.info(f"Задан вопрос: {question.text} [{question.from_user.id}]")
    return ConversationHandler.END


# async def moderator_response(
#     update: Update,
#     context: ContextTypes.DEFAULT_TYPE,
# ) -> None:
#     if int(update.message.from_user.id) != int(
#         settings.MODERATOR_ID
#     ):  # or int(update.message.from_user.id) != 123456789:
#         return QUESTION_ASK

#     text = update.message.reply_to_message.text.split("> ")[0][:-2].split("\n")[1]
#     reply_text = update.message.text
#     user_id = update.message.reply_to_message.text.split("> ")[1]

#     await context.bot.send_message(
#         text="Модератор ответил на Ваш вопрос.\n",
#         chat_id=user_id,
#     )
#     await context.bot.copy_message(
#         message_id=update.message.message_id,
#         chat_id=user_id,
#         from_chat_id=update.message.chat_id,
#     )
#     await context.bot.send_message(
#         text='Если у Вас появятся новые вопросы, нажмите на кнопку "Задать вопрос"',
#         chat_id=user_id,
#     )

#     log.info(f"На вопрос {text} [{user_id}] получен ответ: {reply_text}")


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
        info = 'ФИО не найдены. Проверьте корректность внесения данных и повторите запрос в разделе "Проживание" или свяжитесь с организаторами.'

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


async def transfer_1(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    try:
        user_name = update.message.text
        log.warn(f"User input transfer 10.04: {user_name}")
        info = get_transfer_in_info(db, user_name)
        if len(info) > 0:
            for i in info:
                await update.message.reply_text(
                    f'ФИО: {i["full_name"]}\n'
                    f'Дата прибытия: {i["arrival_date"]}\n'
                    f'Время прибытия: {i["arrival_time"]}\n'
                    f'Номер самолета/поезда: {i["flight_train_number"]}\n'
                    f'Трансфер: {i["transfer"]}',
                    reply_markup=ReplyKeyboardRemove(),
                )
        else:
            await update.message.reply_text(
                'ФИО не найдены. Проверьте корректность внесения данных и повторите запрос в разделе "Трансфер" или свяжитесь с организаторами.'
            )
    except TypeError as e:
        await update.message.reply_text(
            'ФИО не найдены. Проверьте корректность внесения данных и повторите запрос в разделе "Трансфер" или свяжитесь с организаторами.'
        )
    return ConversationHandler.END


async def send_notification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if int(update.message.from_user.id) != int(settings.MODERATOR_ID):
        return

    text = get_notification(db)
    users = db["users"]
    for user in users.find({}):
        await context.bot.send_message(chat_id=user["id"], text=text)


async def tour_notifications_choose(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if int(update.message.from_user.id) != int(settings.MODERATOR_ID):
        return ConversationHandler.END

    tours = get_all_tours(db)
    markup = ReplyKeyboardMarkup([[tour["name"]] for tour in tours])
    await update.message.reply_text(
        "Выберите пользователям каких экскурсий отправить уведомление: ",
        reply_markup=markup,
    )
    return NOTIFICATIONS_1


async def tour_notifications_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    context.user_data["notification_tour_name"] = update.message.text
    await update.message.reply_text(
        f"Введите текст уведомления для пользователей, которые пойдут на экскурсию {update.message.text}: "
    )
    return NOTIFICATIONS_2


async def tour_notifications_finish(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    for user in get_tour_users(db, context.user_data["notification_tour_name"]):
        await context.bot.send_message(
            chat_id=user["user_id"], text=update.message.text
        )

    await update.message.reply_text("Рассылка уведомлений проведена.")
    return ConversationHandler.END
