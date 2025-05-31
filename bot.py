from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from twilio.rest import Client
from keep_alive import keep_alive
from datetime import timedelta
import time
import logging

logging.basicConfig(level=logging.INFO)

# Admin system
ADMIN_IDS = [6165060012]
user_permissions = {6165060012: float("inf")}
user_used_free_plan = set()

# Twilio session
user_clients = {}
user_available_numbers = {}
user_purchased_numbers = {}

# Permission check decorator
def permission_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        expire_time = user_permissions.get(user_id, 0)
        if time.time() > expire_time:
            keyboard = [
                [InlineKeyboardButton("30 Minute - $FREE", callback_data="PLAN:30m")],
                [InlineKeyboardButton("1 Day - $2", callback_data="PLAN:1d")],
                [InlineKeyboardButton("7 Day - $10", callback_data="PLAN:7d")],
                [InlineKeyboardButton("15 Day - $15", callback_data="PLAN:15d")],
                [InlineKeyboardButton("30 Day - $20", callback_data="PLAN:30d")],
            ]
            await (update.message or update.callback_query).reply_text(
                "Bot à¦à¦° Subscription à¦•à¦¿à¦¨à¦¾à¦° à¦œà¦¨à§à¦¯ à¦¨à¦¿à¦šà§‡à¦° à¦¬à¦¾à¦Ÿà¦¨à§‡ à¦•à§à¦²à¦¿à¦• à¦•à¦°à§à¦¨:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        return await func(update, context)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "à¦¸à§à¦¬à¦¾à¦—à¦¤à¦® ðŸŒ¸ã€Œ* ð™ð˜¼ð™Žð™† ãƒ¡ ð™ð™ð™€ð˜¼ð™Žð™ð™ð™€ ã€-à¦ ðŸ¤ à¦•à¦¾à¦œ à¦•à¦°à¦¾à¦° à¦œà¦¨à§à¦¯ à¦¨à¦¿à¦šà§‡à¦° à¦•à¦®à¦¾à¦¨à§à¦¡ à¦—à§à¦²à§‹ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à¦¤à§‡ à¦ªà¦°à¦¬à§‡à¦¨!\n\n"
        "/login <SID> <TOKEN>\n"
        "/buy_number (Area Code)  \n"
        "/show_messages\n"
        "/delete_number\n"
        "/my_numbers\n"
        " ðŸ›‚SUPPORT : @permission_required"
    )

# Admin permission grant
async def grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("âŒ à¦†à¦ªà¦¨à¦¿ à¦à¦‡ à¦•à¦®à¦¾à¦¨à§à¦¡ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à¦¤à§‡ à¦ªà¦¾à¦°à¦¬à§‡à¦¨ à¦¨à¦¾à¥¤")
        return
    if len(context.args) != 2:
        await update.message.reply_text("à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦°: /grant <user_id> <duration> (à¦¯à§‡à¦®à¦¨ 3d)")
        return
    try:
        target_id = int(context.args[0])
        duration = context.args[1].lower()
        if duration.endswith("mo"):
            seconds = int(duration[:-2]) * 2592000
        else:
            unit_map = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
            unit = duration[-1]
            amount = int(duration[:-1])
            seconds = amount * unit_map[unit]
        user_permissions[target_id] = time.time() + seconds
        await update.message.reply_text(f"âœ… {target_id} à¦•à§‡ {duration} à¦¸à¦®à§Ÿà§‡à¦° à¦œà¦¨à§à¦¯ à¦ªà¦¾à¦°à¦®à¦¿à¦¶à¦¨ à¦¦à§‡à¦“à§Ÿà¦¾ à¦¹à§Ÿà§‡à¦›à§‡à¥¤")
    except:
        await update.message.reply_text("âŒ à¦­à§à¦² à¦«à¦°à¦®à§à¦¯à¦¾à¦Ÿà¥¤ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à§à¦¨ m, h, d, w, mo")

# Active user list
async def active_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("âŒ à¦†à¦ªà¦¨à¦¿ à¦à¦‡ à¦•à¦®à¦¾à¦¨à§à¦¡ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à¦¤à§‡ à¦ªà¦¾à¦°à¦¬à§‡à¦¨ à¦¨à¦¾à¥¤")
        return
    now = time.time()
    active = {uid: exp for uid, exp in user_permissions.items() if exp > now or exp == float("inf")}
    if not active:
        await update.message.reply_text("à¦•à§‹à¦¨à§‹ Active Permission à¦‡à¦‰à¦œà¦¾à¦° à¦¨à§‡à¦‡à¥¤")
        return

    msg = "âœ… Active Permission à¦‡à¦‰à¦œà¦¾à¦° à¦²à¦¿à¦¸à§à¦Ÿ âœ…\n\n"
    for uid, exp in active.items():
        try:
            user = await context.bot.get_chat(uid)
            name = user.full_name
            username = f"@{user.username}" if user.username else "N/A"
        except:
            name = "Unknown"
            username = "N/A"

        duration = "Unlimited" if exp == float("inf") else str(timedelta(seconds=int(exp - now)))
        msg += (
            f"ðŸ‘¤ Name: {name}\n"
            f"ðŸ†” ID: {uid}\n"
            f"ðŸ”— Username: {username}\n"
            f"â³ Time Left: {duration}\n\n"
            f"_________________________\n"
        )
    await update.message.reply_text(msg)

# Twilio login
@permission_required
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦°: /login <SID> <AUTH_TOKEN>")
        return
    sid, token = context.args
    try:
        client = Client(sid, token)
        client.api.accounts(sid).fetch()
        user_clients[update.effective_user.id] = client
        await update.message.reply_text("âœ… à¦²à¦—à¦‡à¦¨ à¦¸à¦«à¦² à¦¹à§Ÿà§‡à¦›à§‡!")
    except Exception as e:
        logging.exception("Login error:")
        await update.message.reply_text(f"à¦²à¦—à¦‡à¦¨ à¦¹à§Ÿà¦¨à¦¿ à¦†à¦ªà¦¨à¦¾à¦° Token à¦¨à¦·à§à¦Ÿ à¦¹à§Ÿà§‡à¦›à§‡ ðŸ¥²")

# Buy number
@permission_required
async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = user_clients.get(user_id)

    if not client:
        await update.message.reply_text("âš ï¸ à¦†à¦—à§‡ /login à¦•à¦°à§à¦¨à¥¤")
        return

    try:
        if context.args:
            area_code = context.args[0]
            numbers = client.available_phone_numbers("CA").local.list(area_code=area_code, limit=10)
        else:
            numbers = client.available_phone_numbers("CA").local.list(limit=10)

        if not numbers:
            await update.message.reply_text("à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦ªà¦¾à¦“à§Ÿà¦¾ à¦¯à¦¾à§Ÿà¦¨à¦¿à¥¤")
            return

        user_available_numbers[user_id] = [n.phone_number for n in numbers]
        keyboard = [[InlineKeyboardButton(n.phone_number, callback_data=f"BUY:{n.phone_number}")] for n in numbers]
        keyboard.append([InlineKeyboardButton("Cancel âŒ", callback_data="CANCEL")])

        await update.message.reply_text(
            "à¦¨à¦¿à¦šà§‡à¦° à¦¨à¦¾à¦®à§à¦¬à¦¾à¦°à¦—à§à¦²à§‹ à¦ªà¦¾à¦“à§Ÿà¦¾ à¦—à§‡à¦›à§‡:\n\n" + "\n".join(user_available_numbers[user_id]),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.exception("Buy number error:")
        await update.message.reply_text(f"à¦¸à¦®à¦¸à§à¦¯à¦¾: à¦¦à§Ÿà¦¾ à¦•à¦°à§‡ à¦†à¦ªà¦¨à¦¾à¦° à¦†à¦—à§‡à¦° à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦¡à¦¿à¦²à§‡à¦Ÿ à¦•à¦°à§à¦¨ à¦…à¦¥à¦¬à¦¾ Token à¦šà§‡à¦žà§à¦œ à¦•à¦°à§à¦¨")


# Show messages
@permission_required
async def show_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("âš ï¸ à¦†à¦—à§‡ /login à¦•à¦°à§à¦¨à¥¤")
        return
    try:
        msgs = client.messages.list(limit=20)
        incoming = [msg for msg in msgs if msg.direction == "inbound"]
        if not incoming:
            await update.message.reply_text("à¦•à§‹à¦¨à§‹ Incoming Message à¦ªà¦¾à¦“à§Ÿà¦¾ à¦¯à¦¾à§Ÿà¦¨à¦¿à¥¤")
            return
        output = "\n\n".join([f"From: {m.from_}\nTo: {m.to}\nBody: {m.body}" for m in incoming[:5]])
        await update.message.reply_text(output)
    except Exception as e:
        logging.exception("Show messages error:")
        await update.message.reply_text(f"à¦¸à¦®à¦¸à§à¦¯à¦¾: à¦†à¦ªà¦¨à¦¾à¦° Token à¦ à¦¸à¦®à¦¸à§à¦¯à¦¾ à¦¦à§Ÿà¦¾ à¦•à¦°à§‡ Token à¦šà§‡à¦žà§à¦œ à¦•à¦°à§à¦¨")

# Delete number
@permission_required
async def delete_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("âš ï¸ à¦†à¦—à§‡ /login à¦•à¦°à§à¦¨à¥¤")
        return
    try:
        numbers = client.incoming_phone_numbers.list(limit=1)
        if not numbers:
            await update.message.reply_text("à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦–à§à¦à¦œà§‡ à¦ªà¦¾à¦“à§Ÿà¦¾ à¦¯à¦¾à§Ÿà¦¨à¦¿à¥¤")
            return
        numbers[0].delete()
        await update.message.reply_text("âœ… à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦¡à¦¿à¦²à¦¿à¦Ÿ à¦¹à§Ÿà§‡à¦›à§‡à¥¤")
    except Exception as e:
        logging.exception("Delete number error:")
        await update.message.reply_text(f"à¦¡à¦¿à¦²à¦¿à¦Ÿ à¦¹à§Ÿà¦¨à¦¿ à¦†à¦ªà¦¨à¦¾à¦° Token à¦ à¦¸à¦®à¦¸à§à¦¯à¦¾ à¦¦à§Ÿà¦¾ à¦•à¦°à§‡ Token à¦šà§‡à¦žà§à¦œ à¦•à¦°à§à¦¨ ")

# My numbers
@permission_required
async def my_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("âš ï¸ à¦†à¦—à§‡ /login à¦•à¦°à§à¦¨à¥¤")
        return
    try:
        numbers = client.incoming_phone_numbers.list()
        if not numbers:
            await update.message.reply_text("à¦†à¦ªà¦¨à¦¾à¦° à¦•à§‹à¦¨à§‹ à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦¨à§‡à¦‡à¥¤")
            return
        keyboard = [[InlineKeyboardButton(n.phone_number, callback_data=f"DELETE:{n.phone_number}")] for n in numbers]
        await update.message.reply_text("à¦†à¦ªà¦¨à¦¾à¦° à¦¨à¦¾à¦®à§à¦¬à¦¾à¦°à¦—à§à¦²à§‹:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.exception("My numbers error:")
        await update.message.reply_text(f"à¦¸à¦®à¦¸à§à¦¯à¦¾: à¦†à¦ªà¦¨à¦¾à¦° Token à¦ à¦¸à¦®à¦¸à§à¦¯à¦¾ à¦¦à§Ÿà¦¾ à¦•à¦°à§‡ Token à¦šà§‡à¦žà§à¦œ à¦•à¦°à§à¦¨ ")

# Admin Management
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("âŒ à¦†à¦ªà¦¨à¦¿ à¦à¦‡ à¦•à¦®à¦¾à¦¨à§à¦¡ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à¦¤à§‡ à¦ªà¦¾à¦°à¦¬à§‡à¦¨ à¦¨à¦¾à¥¤")
        return
    try:
        new_admin = int(context.args[0])
        if new_admin not in ADMIN_IDS:
            ADMIN_IDS.append(new_admin)
            user_permissions[new_admin] = float("inf")
            await update.message.reply_text(f"âœ… {new_admin} à¦à¦–à¦¨ Admin!")
        else:
            await update.message.reply_text("à¦‡à¦‰à¦œà¦¾à¦° à¦‡à¦¤à¦¿à¦®à¦§à§à¦¯à§‡à¦‡ Adminà¥¤")
    except:
        await update.message.reply_text("âŒ à¦¸à¦ à¦¿à¦•à¦­à¦¾à¦¬à§‡ user_id à¦¦à¦¿à¦¨à¥¤")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS or len(ADMIN_IDS) <= 1:
        await update.message.reply_text("âŒ à¦à¦‡ à¦•à¦®à¦¾à¦¨à§à¦¡ à¦†à¦ªà¦¨à¦¾à¦° à¦œà¦¨à§à¦¯ à¦¨à¦¾à¥¤")
        return
    try:
        target_id = int(context.args[0])
        if target_id in ADMIN_IDS and target_id != user_id:
            ADMIN_IDS.remove(target_id)
            user_permissions.pop(target_id, None)
            await update.message.reply_text(f"âœ… {target_id} à¦•à§‡ Admin à¦¥à§‡à¦•à§‡ à¦¸à¦°à¦¾à¦¨à§‹ à¦¹à§Ÿà§‡à¦›à§‡à¥¤")
        else:
            await update.message.reply_text("âŒ à¦­à§à¦² à¦†à¦‡à¦¡à¦¿à¥¤")
    except:
        await update.message.reply_text("âŒ à¦¸à¦ à¦¿à¦•à¦­à¦¾à¦¬à§‡ user_id à¦¦à¦¿à¦¨à¥¤")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("âŒ à¦†à¦ªà¦¨à¦¿ à¦à¦‡ à¦•à¦®à¦¾à¦¨à§à¦¡ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à¦¤à§‡ à¦ªà¦¾à¦°à¦¬à§‡à¦¨ à¦¨à¦¾à¥¤")
        return
    msg = "ðŸ›¡ï¸ Admin List:\n\n"
    for aid in ADMIN_IDS:
        try:
            user = await context.bot.get_chat(aid)
            msg += f"{user.full_name} â€” @{user.username or 'N/A'} (ID: {aid})\n"
        except:
            msg += f"Unknown (ID: {aid})\n"
    await update.message.reply_text(msg)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("âŒ à¦†à¦ªà¦¨à¦¿ à¦à¦‡ à¦•à¦®à¦¾à¦¨à§à¦¡ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à¦¤à§‡ à¦ªà¦¾à¦°à¦¬à§‡à¦¨ à¦¨à¦¾à¥¤")
        return
    msg = " ".join(context.args)
    success = fail = 0
    for uid in user_permissions:
        try:
            await context.bot.send_message(chat_id=uid, text=msg)
            success += 1
        except:
            fail += 1
    await update.message.reply_text(f"âœ… à¦ªà¦¾à¦ à¦¾à¦¨à§‹ à¦¹à§Ÿà§‡à¦›à§‡: {success}, âŒ à¦¬à§à¦¯à¦°à§à¦¥: {fail}")

# Button callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("BUY:"):
        number = data.split("BUY:")[1]
        client = user_clients.get(user_id)
        if not client:
            await query.edit_message_text("âš ï¸ à¦†à¦—à§‡ /login à¦•à¦°à§à¦¨à¥¤")
            return
        try:
            purchased = client.incoming_phone_numbers.create(phone_number=number)
            await query.edit_message_text(f"âœ… à¦†à¦ªà¦¨à¦¾à¦° à¦¨à¦¾à¦®à§à¦¬à¦¾à¦°à¦Ÿà¦¿ à¦•à¦¿à¦¨à¦¾ à¦¹à§Ÿà§‡à¦›à§‡: {purchased.phone_number}")
        except Exception as e:
            await query.edit_message_text(f"à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦•à§‡à¦¨à¦¾ à¦¯à¦¾à§Ÿà¦¨à¦¿ à¦¦à§Ÿà¦¾ à¦•à¦°à§‡ à¦†à¦ªà¦¨à¦¾à¦° à¦†à¦—à§‡à¦° à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦¡à¦¿à¦²à§‡à¦Ÿ à¦•à¦°à§à¦¨ à¦…à¦¥à¦¬à¦¾ à¦†à¦ªà¦¨à¦¾à¦° Token à¦ à¦¸à¦®à¦¸à§à¦¯à¦¾ à¦¦à§Ÿà¦¾ à¦•à¦°à§‡ Token à¦šà§‡à¦žà§à¦œ à¦•à¦°à§à¦¨")

    elif data.startswith("DELETE:"):
        number = data.split("DELETE:")[1]
        client = user_clients.get(user_id)
        try:
            nums = client.incoming_phone_numbers.list(phone_number=number)
            if nums:
                nums[0].delete()
                await query.edit_message_text(f"âœ… à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° {number} à¦¡à¦¿à¦²à¦¿à¦Ÿ à¦¹à§Ÿà§‡à¦›à§‡à¥¤")
            else:
                await query.edit_message_text("à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦ªà¦¾à¦“à§Ÿà¦¾ à¦¯à¦¾à§Ÿà¦¨à¦¿à¥¤")
        except Exception as e:
            await query.edit_message_text(f"à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦¡à¦¿à¦²à¦¿à¦Ÿ à¦•à¦°à¦¾ à¦¯à¦¾à§Ÿà¦¨à¦¿ à¦†à¦ªà¦¨à¦¾à¦° Token à¦ à¦¸à¦®à¦¸à§à¦¯à¦¾ à¦¦à§Ÿà¦¾ à¦•à¦°à§‡ Token à¦šà§‡à¦žà§à¦œ à¦•à¦°à§à¦¨ ")

    elif data == "CANCEL":
        await query.edit_message_text("à¦¨à¦¾à¦®à§à¦¬à¦¾à¦° à¦¨à¦¿à¦°à§à¦¬à¦¾à¦šà¦¨ à¦¬à¦¾à¦¤à¦¿à¦² à¦•à¦°à¦¾ à¦¹à§Ÿà§‡à¦›à§‡à¥¤")

    elif data.startswith("PLAN:"):
        plan = data.split(":")[1]
        username = f"@{query.from_user.username}" if query.from_user.username else "N/A"
        prices = {
            "30Minute": (1800, "30 Minute", "$FREE"),
            "1d": (86400, "1 Day", "$2"),
            "7d": (604800, "7 Day", "$10"),
            "15d": (1296000, "15 Day", "$15"),
            "30d": (2592000, "30 Day", "$20")
        }
        if plan == "30m":
            if user_id in user_used_free_plan:
                await query.edit_message_text("à¦†à¦ªà¦¨à¦¿ à¦‡à¦¤à¦¿à¦®à¦§à§à¦¯à§‡à¦‡ à¦«à§à¦°à¦¿ à¦ªà§à¦²à¦¾à¦¨ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à§‡à¦›à§‡à¦¨à¥¤à¦¦à§Ÿà¦¾ à¦•à¦°à§‡ à¦…à¦¨à§à¦¯ Plan Choose à¦•à¦°à§à¦¨")
                return
            user_used_free_plan.add(user_id)
            user_permissions[user_id] = time.time() + 1800
            await query.edit_message_text("âœ… à¦†à¦ªà¦¨à¦¿ à§©à§¦ à¦®à¦¿à¦¨à¦¿à¦Ÿà§‡à¦° à¦œà¦¨à§à¦¯ à¦«à§à¦°à¦¿ à¦ªà§à¦²à¦¾à¦¨ à¦à¦•à¦Ÿà¦¿à¦­ à¦•à¦°à§‡à¦›à§‡à¦¨à¥¤ à¦®à¦¨à§‡ à¦°à¦¾à¦–à¦¬à§‡à¦¨ à¦à¦Ÿà¦¿ à¦¶à§à¦§à§ à¦à¦•à¦¬à¦¾à¦°à§‡à¦° à¦œà¦¨à§à¦¯à¦‡ à¦ªà§à¦°à¦¯à§‹à¦œà§à¦¯ ðŸŸ¢ðŸ”µ ")
            return
        if plan in prices:
            _, label, cost = prices[plan]
            msg = (
                f"Please send {cost} to Binance Pay ID: 905282228\n"
                f"à¦ªà§‡à¦®à§‡à¦¨à§à¦Ÿ à¦•à¦°à¦¾à¦° à¦ªà¦° à¦ªà§à¦°à§à¦­ à¦ªà¦¾à¦ à¦¾à¦¨ Admin à¦•à§‡ @permission_required  \n\n"
                f"User ID: {user_id}\nUsername: {username}\nPlan: {label} - {cost}"
            )
            await query.edit_message_text(msg)

# Start bot
def main():
    keep_alive()
    TOKEN ="8018963341:AAFBirbNovfFyvlzf_EBDrBsv8qPW5IpIDA"
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("grant", grant))
    app.add_handler(CommandHandler("active_users", active_users))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("buy_number", buy_number))
    app.add_handler(CommandHandler("show_messages", show_messages))
    app.add_handler(CommandHandler("delete_number", delete_number))
    app.add_handler(CommandHandler("my_numbers", my_numbers))
    app.add_handler(CommandHandler("add_admin", add_admin))
    app.add_handler(CommandHandler("remove_admin", remove_admin))
    app.add_handler(CommandHandler("list_admins", list_admins))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()



from datetime import datetime, timedelta

user_access = {}  # Dictionary to track access times

@bot.message_handler(commands=['free'])
def handle_free(message):
    if str(message.from_user.id) != "6734281256":
        bot.reply_to(message, "Unauthorized access.")
        return

    try:
        _, user_id_str, duration_str = message.text.split()
        user_id = int(user_id_str)
        amount = int(duration_str[:-1])
        unit = duration_str[-1]

        if unit == 'h':
            expiry = datetime.now() + timedelta(hours=amount)
        elif unit == 'd':
            expiry = datetime.now() + timedelta(days=amount)
        elif unit == 'm':
            expiry = datetime.now() + timedelta(minutes=amount)
        elif unit == 'o':  # 'mo' interpreted as '1mo' -> '1o'
            expiry = datetime.now() + timedelta(days=30 * amount)
        else:
            bot.reply_to(message, "Invalid duration format. Use h/d/m/mo.")
            return

        user_access[user_id] = expiry
        bot.reply_to(message, f"User {user_id} granted free access until {expiry}.")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}\nUse format: /free <chat_id> <duration>, e.g., /free 123456 1d")
