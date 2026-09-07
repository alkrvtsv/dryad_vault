from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
import texts
from config import ADMIN_ID, PAGE_SIZE

def get_client_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BUTTON_GET_VIDEO)],
            [KeyboardButton(text=texts.BUTTON_HISTORY)]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BUTTON_UPLOAD)],
            [KeyboardButton(text=texts.BUTTON_ASSIGN_DIRECT)],
            [KeyboardButton(text=texts.BUTTON_CUSTOMERS_LIST)]
        ],
        resize_keyboard=True
    )

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.BUTTON_CANCEL)]],
        resize_keyboard=True
    )

def get_user_keyboard(user_id: int):
    return get_admin_keyboard() if user_id == ADMIN_ID else get_client_keyboard()

def build_pagination_row(prev_callback: str, next_callback: str, current_page: int, total_pages: int):
    row = []
    if current_page > 1:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=prev_callback))
    row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=next_callback))
    return row

def build_customers_keyboard(customers, page: int = 1):
    total_pages = (len(customers) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    start_idx = (page - 1) * PAGE_SIZE
    current_items = customers[start_idx:start_idx + PAGE_SIZE]

    inline_keyboard = []
    for user_id, username, count in current_items:
        display_name = f"@{username}" if username else f"ID: {user_id}"
        button_text = f"👤 {display_name} ({count} 🎬)"
        inline_keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"cust:{user_id}:1")])

    if total_pages > 1:
        row = build_pagination_row(f"cust_p:{page-1}", f"cust_p:{page+1}", page, total_pages)
        inline_keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def build_customer_videos_keyboard(orders, user_id: int, page: int = 1):
    total_pages = (len(orders) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    start_idx = (page - 1) * PAGE_SIZE
    current_items = orders[start_idx:start_idx + PAGE_SIZE]

    inline_keyboard = []
    for idx, (code, _, title) in enumerate(current_items, start=start_idx + 1):
        video_title = title if title else f"Видео #{idx} (без названия)"
        if len(video_title) > 25:
            video_title = video_title[:22] + "..."
        button_text = f"🎬 {idx}. {video_title}"
        inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"vopt:{code}:{user_id}:{page}")
        ])

    if total_pages > 1:
        row = build_pagination_row(f"cvid_p:{user_id}:{page-1}", f"cvid_p:{user_id}:{page+1}", page, total_pages)
        inline_keyboard.append(row)

    inline_keyboard.append([
        InlineKeyboardButton(text=texts.BUTTON_REFRESH_USER, callback_data=f"refresh:{user_id}:{page}")
    ])
    inline_keyboard.append([
        InlineKeyboardButton(text=texts.BUTTON_BACK_CUSTOMERS, callback_data="back_customers:1")
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard), current_items, total_pages, page, start_idx + 1

def build_video_actions_keyboard(code: str, user_id: int, page: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BUTTON_NEW_LINK, callback_data=f"newlink:{code}:{user_id}:{page}")],
        [InlineKeyboardButton(text=texts.BUTTON_RENAME_VIDEO, callback_data=f"ren:{code}:{user_id}:{page}")],
        [InlineKeyboardButton(text=texts.BUTTON_DELETE_CONFIRM, callback_data=f"del:{code}:{user_id}:{page}")],
        [InlineKeyboardButton(text=texts.BUTTON_BACK_VIDEOS, callback_data=f"cust:{user_id}:{page}")]
    ])

def build_client_history_keyboard(orders, page: int = 1):
    total_pages = (len(orders) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    start_idx = (page - 1) * PAGE_SIZE
    current_items = orders[start_idx:start_idx + PAGE_SIZE]

    inline_keyboard = []
    for idx, (code, _, title) in enumerate(current_items, start=start_idx + 1):
        video_title = title if title else f"Видео #{idx}"
        if len(video_title) > 28:
            video_title = video_title[:25] + "..."
        button_text = f"▶️ {video_title}"
        inline_keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"my_v:{code}")])

    if total_pages > 1:
        row = build_pagination_row(f"my_p:{page-1}", f"my_p:{page+1}", page, total_pages)
        inline_keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)