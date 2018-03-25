from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from django.shortcuts import reverse
from django.core.exceptions import ObjectDoesNotExist
from .app_settings import BOT_ID
from web.models import PendingGroup, Group
import logging
# set logger
logger = logging.getLogger(__name__)


def get_id(bot, update):
    logger.info('chat_id:{} requested their chat id. chat type: {}'.format(
                    update.message.chat.id, update.message.chat.type))

    chat = bot.get_chat(update.message.chat_id)
    our_bot = bot.getMe()
    update.message.reply_text('chat_id: {0}\nchat_type: {1}\nbot_id: {2}'.format(chat.id, chat.type, our_bot.id))


def _group_admins(bot, chat_id):
    """get bot, chat_id
    return: tuple (user Object, user object) => (our_bot, creatorUser)"""
    # تمام ادمین‌های گروه رو دریافت میکنیم
    admins = bot.getChatAdministrators(chat_id)

    our_bot = None
    group_creator = None

    # به ازای هر ادمین موجود در گروه
    for admin in admins:
        # اگر این ادمین ما بودیم
        if admin.user.id == BOT_ID:
            # یعنی ربات ما دسترسی ادمین داشته و می‌توانیم ادامه دهیم
            our_bot = admin
        # اگر ادمین اصلی بود
        if admin.status == 'creator':
            group_creator = admin

    return our_bot, group_creator


def _hit_database(model, chat_id):
    result = None
    try:
        result = model.objects.get(chat_id=chat_id)
    except ObjectDoesNotExist:
        pass
    return result


def register(bot, update):
    # پاسخ گویی تنها به سوپر گروه ها
    if update.message.chat.type != 'supergroup':
        return

    # TODO check for is active or more i think req.
    # بررسی وجود گروه در لیست اصلی سایت
    main_group = _hit_database(Group, update.message.chat_id)
    # در صورتی که در لیست اصلی سایت موجود باشه پیغام مربوطه ارسال میکنیم و روند ثبت گروه جدید رو متوقف میکنیم
    if main_group is not None:
        update.message.reply_text('گروه شما در لیست گروه‌های تایید شده سایت قرار دارد و نیازی به ثبت مجدد نمی‌باشد.')
        return

    # بررسی وجود گروه در لیست انتظار سایت
    # در صورتی که گروه در لیست انتظار سایت قرار داشت پیغام مربوطه را ارسال میکنیم و از ادامه فرایند ثبت باز میگردیم.
    pending_group = _hit_database(PendingGroup, update.message.chat_id)
    if pending_group is not None:
        update.message.reply_text(
            'گروه شما در انتظار تایید توسط مدیران قرار دارد، از شکیبایی شما سپاس گذاریم.')
        return

    # در صورتی که تا این قسمت پیش آمده باشیم یعنی گروه باید فرایند ثبت نام را انجام دهد
    # بررسی دسترسی ادمین به بات
    # ثبت گروه در لیست انتظار

    our_bot, group_creator = _group_admins(bot, update.message.chat_id)
    # اگر بات ما دسترسی ادمین نداشت پیغام خطا و توقف فرایند
    if our_bot is None:
        update.message.reply_text('''لطفا ربات تلگرامی ما را ادمین نمایید و دسترسی‌های های خواسته شده را به ربات بدهید.
        دسترسی invite users via link''')
        return

    # اگه بات ما دسترسی به لینک گروه نداشت پیغام خطا و توقف فرایند
    if not our_bot.can_invite_users:
        update.message.reply_text('دسترسی invite users via link برای ربات فراهم نیست، بعد از فراهم کردن این دسترسی مجددا تلاش نمایید.')
        return

    # اضافه کردن گروه به لیست انتظار
    chat = update.message.chat
    PendingGroup.objects.create(title=chat.title, chat_id=chat.id, admin_id=group_creator.user.id,
                                admin_username=group_creator.user.name)
    update.message.reply_text('گروه شما در لیست انتظار قرار گرفت، بعد از تایید توسط مدیران به سایت اضافه می‌گردد.')


def start(bot, update):
    logger.info('start commands from. chat_id: {0}, chat_type: {1}'.format(
                    update.message.chat.id, update.message.chat.type))

    if update.message.chat.type == 'supergroup':
        reply_keyboard = [['/register', '/help']]
    else:
        reply_keyboard = [['/get_id', '/github', '/help']]
    
    text = '''سلام!
    بعد یه فکر برای یه پیغام خوشگل میکنم 😂😂😂😂😂😂'''
    bot.sendMessage(update.message.chat_id, text=text,
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard))


def get_help(bot, update):
    help_url = 'https://www.{0}{1}'.format('parand-computer.ir', reverse('web:help'))
    keyboard = [[InlineKeyboardButton('📘 مطالعه بیشتر', help_url)]]
    keyboard_markup = InlineKeyboardMarkup(keyboard)

    help_text = '''جهت اضافه شدن گروه به سایت باید مراحل زیر را انجام دهید
    ۱- گروه را به سوپرگروه ارتقا دهید.
    ۲- ربات تلگرام را به گروه اضافه نمایید.
    ۳- ربات را ادمین گروه کرده و دسترسی invite users via link را به ربات بدهید
    ۴- دستور /register را وارد نمایید تا درخواست شما ثبت گردد.
    گروه شما بعد از تایید توسط ادمین به سایت اضافه خواهد شد.
    
    🔴 توجه: جهت تسریع در روند ثبت حتما قبل از ارسال درخواست نام گروه را به نام درس به همراه نام استاد مربوطه تغییر دهید.'''

    bot.sendMessage(update.message.chat_id, text=help_text, reply_markup=keyboard_markup)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)
