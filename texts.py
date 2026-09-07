BUTTON_GET_VIDEO = "🎬 Получить видео"
BUTTON_HISTORY = "📜 Мои видео"

BUTTON_UPLOAD = "📤 Создать ссылку"
BUTTON_ASSIGN_DIRECT = "📎 Привязать к ID"
BUTTON_CUSTOMERS_LIST = "👥 Список заказчиков"
BUTTON_CANCEL = "❌ Отмена"

CLIENT_START = (
    "Привет! ✨\n\n"
    "Здесь ты можешь забрать своё персональное видео или пересмотреть "
    "ролики из прошлых заказов. Выбирай нужное действие в меню:\n\n"
    "<i>Бот не собирает и не обрабатывает персональные данные, используя "
    "только системный Telegram ID для привязки роликов.</i>"
)

ADMIN_START = (
    "Привет! Ты в панели управления.\n\n"
    "Выбирай, что нужно сделать:"
)

ADMIN_PROMPT_UPLOAD = (
    "Присылай видео прямо в этот чат.\n\n"
    "Я автоматически возьму название из имени файла или подписи. "
    "Если их нет, попрошу ввести название вручную."
)

ADMIN_PROMPT_TITLE = "У этого видео нет имени файла или подписи. Напиши для него название:"

ADMIN_PROMPT_DIRECT_ID = (
    "Напиши числовой Telegram ID заказчика (можно узнать через @userinfobot или взять из списка):"
)

ADMIN_PROMPT_DIRECT_VIDEO = "Отлично! Теперь отправь видео (название подтянется из имени файла или подписи)."

ADMIN_ERR_INVALID_ID = "ID должен состоять только из цифр. Попробуй ещё раз или нажми «❌ Отмена»:"
ADMIN_ERR_NEED_VIDEO = "Отправь именно видеофайл или нажми «❌ Отмена»."

ADMIN_DIRECT_SUCCESS = "✅ Видео успешно привязано! Теперь оно доступно у заказчика в «Моих видео»."
ADMIN_ACTION_CANCELLED = "Действие отменено."

CLIENT_ASK_CODE = "Напиши мне код доступа к твоему видео:"

ERR_CODE_NOT_FOUND = "Такого кода нет. Проверь, нет ли опечатки, и нажми «🎬 Получить видео», чтобы попробовать снова."
ERR_CODE_NOT_FOUND_LINK = "Похоже, ссылка недействительна или в ней ошибка."
ERR_USED_BY_OTHER = "Этот код уже кто-то активировал. Если это твой заказ — напиши автору."

VIDEO_LOADING = "Отправляю твоё видео, пару секунд..."

HISTORY_EMPTY = "У тебя пока нет сохранённых видео."
CLIENT_HISTORY_TITLE = "🎬 <b>Твои видео:</b>\n\nВыбери ролик из списка ниже, чтобы посмотреть его:"

CUSTOMERS_EMPTY = "Список заказчиков пока пуст. Никто ещё не получал видео."
CUSTOMERS_TITLE = "👥 <b>Твои заказчики:</b>\n\nВыбери нужного, чтобы посмотреть его видео или обновить профиль:"

CUSTOMER_NO_VIDEOS = "У этого заказчика не осталось сохранённых видео."
VIDEO_DELETED_SUCCESS = "Видео удалено!"

BUTTON_NEW_LINK = "🔗 Создать новую ссылку"
BUTTON_REFRESH_USER = "🔄 Обновить данные"
BUTTON_BACK_CUSTOMERS = "◀️ Назад к заказчикам"
BUTTON_BACK_VIDEOS = "◀️ Назад к списку видео"
BUTTON_RENAME_VIDEO = "✏️ Переименовать"
BUTTON_DELETE_CONFIRM = "🗑 Удалить видео"

USER_UPDATED_SUCCESS = "Данные успешно обновлены!"
USER_UPDATE_FAILED = "Не удалось обновить: пользователь ещё ни разу не запускал этого бота."

ADMIN_PROMPT_RENAME = "Напиши новое название для этого видео:"
ADMIN_RENAME_SUCCESS = "✅ Название видео успешно обновлено!"
NEW_LINK_SUCCESS = "Новая ссылка создана!"

def video_manage_text(title: str, code: str, user_id: int, username: str | None) -> str:
    user_ref = f"@{username}" if username else f"ID: {user_id}"
    return (
        f"🎬 <b>Видео:</b> {title}\n"
        f"🔑 <b>Код:</b> <code>{code}</code>\n"
        f"👤 <b>Заказчик:</b> {user_ref}\n\n"
        "Выбери действие с роликом:"
    )

def video_caption(title: str | None = None) -> str:
    if title:
        return f"🎬 <b>{title}</b>\n\nТвоё видео готово ✨\n\n<i>Сохранение и пересылка отключены. Приятного просмотра!</i>"
    return "Твоё видео готово ✨\n\n<i>Сохранение и пересылка отключены. Приятного просмотра!</i>"

def admin_video_saved(code: str, link: str, title: str) -> str:
    return (
        f"✅ <b>Видео «{title}» сохранено!</b>\n\n"
        f"🔑 Код: <code>{code}</code>\n\n"
        f"🔗 Ссылка для отправки:\n{link}"
    )

def admin_new_link_created(code: str, link: str, title: str) -> str:
    return (
        f"✅ <b>Новая ссылка для видео «{title}» готова!</b>\n\n"
        f"🔑 Новый код: <code>{code}</code>\n\n"
        f"🔗 Ссылка для клиента:\n{link}\n\n"
        "<i>(Ссылка одноразовая и активируется при переходе)</i>"
    )

def admin_order_activated(code: str, username: str | None, user_id: int, title: str | None = None) -> str:
    username_text = f"@{username}" if username else "нет"
    title_line = f"🎬 Видео: <b>{title}</b>\n" if title else ""
    return (
        "🔔 <b>Видео забрали!</b>\n\n"
        f"{title_line}"
        f"🔑 Код: <code>{code}</code>\n"
        f"🌐 Юзернейм: {username_text}\n"
        f"🆔 ID: <code>{user_id}</code>"
    )

def customer_details_title(username: str | None, user_id: int, orders_page: list, total_count: int, page: int, total_pages: int, start_idx: int) -> str:
    username_text = f"@{username}" if username else "нет"
    lines = []
    for idx, (_, _, title) in enumerate(orders_page, start=start_idx):
        video_title = title if title else "Без названия"
        lines.append(f"{idx}. {video_title}")
    videos_list_text = "\n".join(lines) if lines else "Нет видео"
    page_info = f" (Стр. {page}/{total_pages})" if total_pages > 1 else ""
    return (
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🌐 Юзернейм: {username_text}\n"
        f"🎬 Всего видео: {total_count}{page_info}\n\n"
        f"<b>Список видео:</b>\n{videos_list_text}\n\n"
        "Выбери видео ниже для управления:"
    )