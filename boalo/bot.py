import datetime
import pytz
import os

import botogram
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import scoped_session

from boalo import models


try:
    env = os.environ
    api_key = env["BOT_API_KEY"]
    engine_uri = env["ENGINE_URI"]
    admin_id = int(env["TELEGRAM_ADMIN_ID"])
except:
    print('REQUIRED ENV VARS NOT PRESENT')
    exit(1)

bot = botogram.create(api_key)
db = create_engine(engine_uri)
models.Base.metadata.create_all(db)
sr = scoped_session(sessionmaker(bind=db))


def db_query(session, model, *filters, one=False):
    q = session.query(model)
    for filter_ in filters:
        q = q.filter(filter_)
    if one:
        try:
            return q.one()
        except Exception as e:
            return None
    else:
        return list(q)

def add(session, obj):
    session.add(obj)
    session.commit()


def get_user(chat):
    return db_query(sr(), models.User,
           models.User.id == chat.id,
           one=True)


def check_user(chat):
    user = get_user(chat)
    if user and user.activated and not user.banned:
        sr.remove()
        return True
    elif user is None:
        add(sr(), models.User(id=chat.id, name=chat.name,
                              username=chat.username))
        sr.remove()
        chat.send((
            "Hi! Admin has been informed.\n"
            "They will contact you eventually."))
        buttons = botogram.Buttons()
        buttons[0].callback("Add them", "user_add", str(chat.id))
        buttons[0].callback("Ban them", "user_ban", str(chat.id))
        bot.chat(admin_id).send(
            f"{chat.name}, @{chat.username} wants to join.\n",
            attach=buttons)
    elif user.banned:
        chat.send("You've been banned from this bot.")
        sr.remove()
    else:
        chat.send("Please be patient!")
        sr.remove()
    return False

def check_admin(chat):
    return chat.id == admin_id

@bot.callback("user_add")
def user_add_callback(query, data, chat, message):
    if not check_admin(chat):
        return

    user = db_query(sr(), models.User,
                 models.User.id == data,
                 one=True)
    user.activated = True
    sr().commit()
    bot.chat(user.id).send("Now we're talking!", attach=menu())
    sr.remove()

@bot.callback("user_ban")
def user_ban_callback(query, data, chat, message):
    if not check_admin(chat):
        return

    user = db_query(sr(), models.User,
                 models.User.id == data,
                 one=True)
    user.banned = True
    sr().commit()
    bot.chat(user.id).send("You got yourself banned. :(")
    sr.remove()


def menu(rows=None, user=None):
    buttons = botogram.Buttons()
    if rows:
        for i in range(len(rows)):
            for button in row:
                buttons[i].callback(*button)
        lr = len(rows)
    else:
        lr = 0
    if user and user.vpn_username and user.vpn_password:
        buttons[lr].callback("vpn info", "vpn_info_callback")
        lr += 1
    info = db_query(sr(), models.Info)
    for i in range(len(info)):
        buttons[lr + int(i / 2)].callback(info[i].title, "info_callback", info[i].title)
    return buttons


@bot.command("start")
def start_command(chat, message, args):
    """
    nothing special just the begining
    """
    chat.send("Hey hello")

    if not check_user(chat):
        return

    sr.remove()


@bot.command("info")
def info_command(chat, message, args):
    """
    all the small things
    """
    if not check_user(chat):
        return

    chat.send("How can I help you?", attach=menu(user=get_user(chat)))
    sr.remove()

@bot.callback("info_callback")
def info_callback(query, data, chat, message):
    info = db_query(sr(), models.Info,
                 models.Info.title == data,
                 one=True)
    chat.send(info.text)
    sr.remove()

@bot.callback("vpn_info_callback")
def vpn_info_callback(query, data, chat, message):
    user = get_user(chat)
    host = db_query(sr(), models.Info,
                    models.Info.title == "host",
                    one=True)
    chat.send(f"{host.text}\n{user.vpn_info}")
    sr.remove()

@bot.message_matches("addinfo .+")
def addinfo_command(chat, message):
    """
    ADMINONLY addinfo title text
    """
    if not check_admin(chat):
        return

    split = message.text.split()
    if len(split) < 3:
        chat.send("`addinfo TITLE TEXT'")
        return
    title = split[1]
    text = message.text[len('addinfo  ') + len(title):]
    add(sr(), models.Info(title=title, text=text))
    sr.remove()

@bot.command("vpn")
def vpn_command(chat, message, args):
    """
    manage your vpn here
    """
    if not check_user(chat):
        return

    if len(args) > 0:
        return add_vpn(chat, message, args)

    user = get_user(chat)
    if user.vpn_username and user.vpn_password:
        chat.send("Check out info menu!", attach=menu(user=user))
        chat.send(user.vpn_info)
    else:
        chat.send((
            "Choose your username and password with the following format:\n"
            "`/vpn USERNAME PASSWORD`"))
    sr.remove()

def add_vpn(chat, message, args):
    if len(args) != 2:
        chat.send((
            "You must enter exactly two args.\n"
            "`/vpn USERNAME PASSWORD`"))
        return
    user = get_user(chat)
    username, password = args[0], args[1]
    if db_query(sr(), models.User,
                  models.User.vpn_username == username,
                  one=True):
        chat.send((
            "A User with this username already exists.\n"
            "Choose another username\n"
            "`/vpn USERNAME PASSWORD`"))
        sr.remove()
        return
    if len(password) < 8:
        chat.send((
            "Password is too short choose a longer one.\n"
            "`/vpn USERNAME PASSWORD`"))
        sr.remove()
        return
    user.vpn_username = username
    user.vpn_password = password
    user.add_vpn()
    sr().commit()
    chat.send((
        "Successfully registered user!\n"
        "Use info menu to get vpn info."), attach=menu(user=user))
    sr.remove()

def total_invoices(user):
    invoices = db_query(sr(), models.Invoice,
                     models.Invoice.paid == False,
                     models.Invoice.user_id == user.id)
    return sum([i.fee for i in invoices]), invoices

@bot.command("pay")
def pay_command(chat, message, args):
    """
    pay your debt here :P
    """
    if not check_user(chat):
        return

    user = get_user(chat)
    total, _ = total_invoices(user)
    card = db_query(sr(), models.Info,
                    models.Info.title == 'card'
                    , one=True)
    if total >= 5:
        chat.send((
            f"Please transfer {total - user.credit:.2f} Tomans"
            " to the following card, And then send a photo of recepit here.\n"
            f"\n{card.text}"))
    else:
        chat.send(f"You may pay {total - user.credit:.2f} Tomans.\n"
                  "But it's not nesseccary as it's under 5 Tomans")
    sr.remove()

@bot.timer(3600)
def check_payments(bot):
    today = datetime.datetime.now(pytz.timezone('Asia/Tehran'))
    if today.hour != 21:
        return
    users = db_query(sr(), models.User)
    for user in users:
        debt, invoices = total_invoices(user)
        if debt >= 5:
            for invoice in invoices:
                if invoice.date + datetime.timedelta(days=3) < today.date():
                    user.lock_vpn()
            sr().commit()
            bot.chat(user.id).send((
                "Your vpn account has been locked.\n"
                "Please pay to unlock."))
    sr.remove()

@bot.process_message
def forward_screenshots(chat, message):
    if not check_user(chat):
        return

    if message.photo or message.document:
        bot.chat(admin_id).send((
            f"{chat.name}, @{chat.username} PAID!\n"
            f"Submit it via `payfor {chat.id} AMOUNT`"))
        message.forward_to(admin_id)
        chat.send("Your message has been forwarded to the admin.")
        return True

@bot.message_matches("payfor (\d+) (\w+)")
def payfor_command(chat, message):
    """
    ADMINONLY submit someone's payment
    """
    if not check_admin(chat):
        return

    args = message.text.split()[1:]
    if len(args) != 2:
        chat.send((
            "You must enter exactly two args.\n"
            "`payfor UID AMOUNT`"))
        return
    uid, amount = args[0], args[1]
    user = db_query(sr(), models.User,
                  models.User.id == uid,
                  one=True)
    if user is None:
        chat.send((
            "Wrong UID...\n"
            "`payfor UID AMOUNT`"))
        sr.remove()
        return
    try:
        amount = float(amount)
        if amount <= 0:
            raise
    except:
        chat.send("Amount must be a positive number.")
        sr.remove()
        return
    user.credit += amount
    invoices = db_query(sr(), models.Invoice,
                     models.Invoice.paid == False,
                     models.Invoice.user_id == user.id)
    paid_invoices, paid, total = [], 0, 0
    for invoice in invoices:
        if invoice.fee <= user.credit:
            invoice.paid = True
            user.credit -= invoice.fee
            paid_invoices.append(invoice)
            paid += invoice.fee
        total += invoice.fee
    if len(paid_invoices) == len(invoices):
        user.unlock_vpn()

    sr().commit()
    chat.send(
        f"Successfully paid for user {user.name}, @{user.username}\n",
        attach=menu(user=user))
    bot.chat(user.id).send((f"You have paid for {len(paid_invoices)} invoices "
                            f"for a total of {paid} Tomans "
                            f"and owe {total - paid} Tomans.\n"
                            f"You have {user.credit} Tomans in your account."))
    sr.remove()

@bot.message_matches("charge (\d+)")
def charge_command(chat, message):
    """
    ADMINONLY charge people and get rich
    """
    if not check_admin(chat):
        return

    args = message.text.split()[1:]
    if len(args) != 1:
        chat.send("Use like `charge SERVER_FEE`")
        return
    try:
        server_fee = float(args[0])
    except:
        chat.send("Mount must be a positive number.")
        return
    active_users = db_query(sr(), models.User,
                         models.User.activated == True,
                         models.User.banned == False,
                         models.User.locked == False)
    fee = float(f'{server_fee / len(active_users):.2f}')
    today = datetime.datetime.now(pytz.timezone('Asia/Tehran')).date()
    for user in active_users:
        add(sr(), models.Invoice(user_id=user.id,
                                 fee=fee,
                                 date=today))
    chat.send((f"Successfully created {fee} Tomans invoice"
               f" for {len(active_users)} users."))
    sr.remove()

@bot.message_matches("list")
def list_command(chat, message):
    """
    ADMINONLY list all users
    """
    if not check_admin(chat):
        return

    users = db_query(sr(), models.User,
                     models.User.banned == False)
    msg = "```" + \
        "\n".join([(f"{user.name}, @{user.username}, {user.id}, {user.credit}, "
        f"A:{int(user.activated)}, L:{int(user.locked)}") for user in users]) \
        + "```"
    chat.send(msg)
    sr.remove()

@bot.message_matches("del \d+")
def del_command(chat, message):
    """
    ADMINONLY del a user
    """
    if not check_admin(chat):
        return

    uid = message.split()[1]
    user = db_query(sr(), models.User,
                    models.User.id == uid,
                    one=True)
    if user is None:
        chat.send("User not exists.")
        return

    user.lock_vpn()
    user.activated = False
    sr().commit()
    chat.send(f'User {user.name}, @{user.username} deactivated and locked')
    sr.remove()

@bot.message_matches("sendtoall .+")
def sendtoall_command(chat, message):
    """
    ADMINONLY send message to all active users
    """
    if not check_admin(chat):
        return

    msg = message.text[len("sendtoall "):]
    for user in db_query(sr(), models.User,
                         models.User.activated == True):
        try:
            bot.chat(user.id).send(msg)
        except Exception as e:
            print(str(e))
            exp.append(user)
    chat.send(f"Sent message to all users. {exp} problems.")
    sr.remove()
