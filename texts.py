BUTTON_GET_VIDEO = "🎬 Забрать заказ"
BUTTON_HISTORY = "📜 Мои материалы"

BUTTON_UPLOAD = "📤 Создать ссылку"
BUTTON_ASSIGN_DIRECT = "📎 Привязать к ID"
BUTTON_CUSTOMERS_LIST = "👥 Список заказчиков"
BUTTON_CANCEL = "❌ Отмена"

CLIENT_START = (
    "Привет! ✨\n\n"
    "Здесь ты можешь забрать свои персональные фото или видео, а также "
    "пересмотреть материалы из прошлых заказов. Выбирай действие в меню:\n\n"
    "<i>Бот не собирает и не обрабатывает персональные данные, используя "
    "только системный Telegram ID для привязки материалов.</i>"
)

ADMIN_START = (
    "Привет! Ты в панели управления.\n\n"
    "Выбирай, что нужно сделать:"
)

ADMIN_PROMPT_UPLOAD = (
    "Присылай видео или фото прямо в этот чат.\n\n"
    "Я автоматически возьму название из имени файла или подписи. "
    "Если их нет, попрошу ввести название вручную."
)

ADMIN_PROMPT_TITLE = "У этого файла нет подписи или имени. Напиши для него название:"

ADMIN_PROMPT_DIRECT_ID = (
    "Напиши числовой Telegram ID заказчика (можно узнать через @userinfobot или взять из списка):"
)

ADMIN_PROMPT_DIRECT_MEDIA = "Отлично! Теперь отправь фото или видео (название подтянется из подписи или имени файла)."

ADMIN_ERR_INVALID_ID = "ID должен состоять только из цифр. Попробуй ещё раз или нажми «❌ Отмена»:"
ADMIN_ERR_NEED_MEDIA = "Отправь фото или видеофайл либо нажми «❌ Отмена»."

ADMIN_DIRECT_SUCCESS = "✅ Материал успешно привязан! Теперь он доступен у заказчика в списке."
ADMIN_ACTION_CANCELLED = "Действие отменено."

CLIENT_ASK_CODE = "Напиши мне код доступа к твоему заказу:"

ERR_CODE_NOT_FOUND = "Такого кода нет. Проверь, нет ли опечатки, и нажми «🎬 Забрать заказ», чтобы попробовать снова."
ERR_CODE_NOT_FOUND_LINK = "Похоже, ссылка недействительна или в ней ошибка."
ERR_USED_BY_OTHER = "Этот код уже кто-то активировал. Если это твой заказ — напиши автору."

MEDIA_LOADING = "Отправляю твой заказ, пару секунд..."

HISTORY_EMPTY = "У тебя пока нет сохранённых материалов."
CLIENT_HISTORY_TITLE = "📁 <b>Твои материалы:</b>\n\nВыбери нужный из списка ниже для просмотра:"

CUSTOMERS_EMPTY = "Список заказчиков пока пуст. Никто ещё не получал материалов."
CUSTOMERS_TITLE = "👥 <b>Твои заказчики:</b>\n\nВыбери нужного, чтобы посмотреть его материалы или обновить профиль:"

CUSTOMER_NO_MEDIA = "У этого заказчика не осталось сохранённых материалов."
MEDIA_DELETED_SUCCESS = "Материал удален!"

BUTTON_VIEW_MEDIA = "▶️ Посмотреть в чате"
BUTTON_NEW_LINK = "🔗 Создать новую ссылку"
BUTTON_REFRESH_USER = "🔄 Обновить данные"
BUTTON_BACK_CUSTOMERS = "◀️ Назад к заказчикам"
BUTTON_BACK_MEDIAS = "◀️ Назад к списку материалов"
BUTTON_RENAME_MEDIA = "✏️ Переименовать"
BUTTON_DELETE_CONFIRM = "🗑 Удалить"

USER_UPDATED_SUCCESS = "Данные успешно обновлены!"
USER_UPDATE_FAILED = "Не удалось обновить: пользователь ещё ни разу не запускал этого бота."

ADMIN_PROMPT_RENAME = "Напиши новое название:"
ADMIN_RENAME_SUCCESS = "✅ Название успешно обновлено!"
NEW_LINK_SUCCESS = "Новая ссылка создана!"

def media_manage_text(title: str, code: str, user_id: int, username: str | None, media_type: str) -> str:
    user_ref = f"@{username}" if username else f"ID: {user_id}"
    icon = "🎬 Видео" if media_type == "video" else "🖼 Фото"
    return (
        f"{icon}: <b>{title}</b>\n"
        f"🔑 <b>Код:</b> <code>{code}</code>\n"
        f"👤 <b>Заказчик:</b> {user_ref}\n\n"
        "Выбери действие:"
    )

def media_caption(title: str | None = None) -> str:
    if title:
        return f"✨ <b>{title}</b>\n\nТвой заказ готов!\n\n<i>Сохранение и пересылка отключены.</i>"
    return "Твой заказ готов ✨\n\n<i>Сохранение и пересылка отключены.</i>"

def admin_media_saved(code: str, link: str, title: str, media_type: str) -> str:
    icon = "🎬 Видео" if media_type == "video" else "🖼 Фото"
    return (
        f"✅ <b>{icon} «{title}» сохранено!</b>\n\n"
        f"🔑 Код: <code>{code}</code>\n\n"
        f"🔗 Ссылка для отправки:\n{link}"
    )

def admin_new_link_created(code: str, link: str, title: str, media_type: str) -> str:
    icon = "🎬 Видео" if media_type == "video" else "🖼 Фото"
    return (
        f"✅ <b>Новая ссылка для {icon} «{title}» готова!</b>\n\n"
        f"🔑 Новый код: <code>{code}</code>\n\n"
        f"🔗 Ссылка для клиента:\n{link}\n\n"
        "<i>(Ссылка одноразовая и активируется при переходе)</i>"
    )

def admin_order_activated(code: str, username: str | None, user_id: int, title: str | None = None, media_type: str = "video") -> str:
    username_text = f"@{username}" if username else "нет"
    icon = "🎬 Видео" if media_type == "video" else "🖼 Фото"
    title_line = f"{icon}: <b>{title}</b>\n" if title else ""
    return (
        "🔔 <b>Материал забрали!</b>\n\n"
        f"{title_line}"
        f"🔑 Код: <code>{code}</code>\n"
        f"🌐 Юзернейм: {username_text}\n"
        f"🆔 ID: <code>{user_id}</code>"
    )

def customer_details_title(username: str | None, user_id: int, orders_page: list, total_count: int, page: int, total_pages: int, start_idx: int) -> str:
    username_text = f"@{username}" if username else "нет"
    lines = []
    for idx, (_, _, title, m_type) in enumerate(orders_page, start=start_idx):
        media_title = title if title else "Без названия"
        icon = "🎬" if m_type == "video" else "🖼"
        lines.append(f"{idx}. {icon} {media_title}")
    media_list_text = "\n".join(lines) if lines else "Нет материалов"
    page_info = f" (Стр. {page}/{total_pages})" if total_pages > 1 else ""
    return (
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🌐 Юзернейм: {username_text}\n"
        f"📁 Всего материалов: {total_count}{page_info}\n\n"
        f"<b>Список:</b>\n{media_list_text}\n\n"
        "Выбери материал ниже для управления:"
    )