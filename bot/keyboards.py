from telegram import InlineKeyboardButton

start_keyboard = [
    [
        InlineKeyboardButton("Проживание", callback_data="residence"),
        InlineKeyboardButton("Чек-лист", callback_data="checklist"),
    ],
    [
        InlineKeyboardButton("Тайминг 09.04", callback_data="timing_1"),
        InlineKeyboardButton("Трансфер 8-9.04", callback_data="transfer_1"),
    ],
    [
        InlineKeyboardButton("Тайминг 10.04", callback_data="timing_2"),
        InlineKeyboardButton("Трансфер 10.04", callback_data="transfer_2"),
    ],
    [
        InlineKeyboardButton("Тайминг 11.04", callback_data="timing_3"),
        InlineKeyboardButton("Трансфер 11.04", callback_data="transfer_3"),
    ],
    [
        InlineKeyboardButton("Тайминг 12.04", callback_data="timing_4"),
        InlineKeyboardButton("Трансфер 12.04", callback_data="transfer_4"),
    ],
    [
        InlineKeyboardButton("Записаться на экскурсию", callback_data="tour"),
    ],
    [
        InlineKeyboardButton("Контакты организаторов", callback_data="contacts"),
    ],
    [
        InlineKeyboardButton("Задать вопрос", callback_data="question"),
    ],
]
start_keyboard_without_tours = start_keyboard[:-4] + start_keyboard[-2:]
start_keyboard_pre_release = [
    [
        InlineKeyboardButton("Чек-лист", callback_data="checklist"),
    ],
    [
        InlineKeyboardButton("Проживание", callback_data="residence"),
    ],
    [
        InlineKeyboardButton("Трансфер 8-9.04", callback_data="transfer_1"),
    ],
    [
        InlineKeyboardButton("Тайминг 09.04", callback_data="timing_1"),
    ],
    [
        InlineKeyboardButton("Трансфер 10.04", callback_data="transfer_2"),
    ],
    [
        InlineKeyboardButton("Тайминг 10.04", callback_data="timing_2"),
    ],
    [
        InlineKeyboardButton("Тайминг 11.04", callback_data="timing_3"),
    ],
    [
        InlineKeyboardButton("Трансфер 11.04", callback_data="transfer_3"),
    ],
    [
        InlineKeyboardButton("Тайминг 12.04", callback_data="timing_4"),
    ],
    # [
    #     InlineKeyboardButton("Записаться на экскурсию", callback_data="tour"),
    # ],
    [
        InlineKeyboardButton("Контакты организаторов", callback_data="contacts"),
    ],
    [
        InlineKeyboardButton("Задать вопрос спикеру", callback_data="question"),
    ],
]


def participants_keyboard(participants):
    return [
        [InlineKeyboardButton(participant["name"])]
        for participant in participants.find().limit(100)
    ]
