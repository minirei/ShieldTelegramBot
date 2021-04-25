import logging
import telegram
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, PicklePersistence, Job)
import os
import time
import datetime

from backend import id_dict
from backend import get_name_options, send_temperature


#Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

GROUP, NAME, CONFIRMATION = range(3)

#bot stuff
TOKEN = '' #HIDDEN
persistence = PicklePersistence(filename='user_profiles')
updater = Updater(TOKEN, persistence=persistence)
dp = updater.dispatcher
j = updater.job_queue

#keyboards
group_keyboard = [
    ['HQ', 'VES'],
    ['Section 1', 'Section 2'],
    ['Section 3', 'Section 4']
]

group_markup = ReplyKeyboardMarkup(group_keyboard, resize_keyboard=False, one_time_keyboard=True)

temperature_keyboard =[
    ['35.0', '35.1'],
    ['35.2', '35.3'],
    ['35.4', '35.5'],
    ['35.6', '35.7'],
    ['35.8', '35.9'],
    ['36.0', '36.1'],
    ['36.2', '36.3'],
    ['36.4', '36.5'],
    ['36.6', '36.7'],
    ['36.8', '36.9'],
    ['37.0', '37.1'],
    ['37.2', '37.3'],
    ['37.4', '37.5']
]
temperature_markup = ReplyKeyboardMarkup(temperature_keyboard, resize_keyboard=False)

#non-bot functions
def facts_to_str(user_data):
    facts = []
    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])

#chat functions
def start(update, context):
    # user_data = context.user_data
    # update.message.reply_text("Debugging // stats: {}".format(facts_to_str(user_data)))
    update.message.reply_text("Which group are you in?", reply_markup=group_markup)
    return GROUP

def group(update, context):
    user = update.message.from_user
    user_data = context.user_data

    group = update.message.text
    user_data['Group'] = group
    logger.info("%s's Group: %s", user.first_name, update.message.text)

    #get name options
    name_options = get_name_options(id_dict[group][0])
    name_keyboard = name_options
    name_markup = ReplyKeyboardMarkup(name_keyboard, resize_keyboard=False, one_time_keyboard=True)

    update.message.reply_text('What is your name?', reply_markup=name_markup)
    return NAME

def name(update, context):
    user = update.message.from_user
    user_data = context.user_data
    # update.message.reply_text('debugging // your group is {}'.format(user_data['Group']))

    name = update.message.text
    user_data['Name'] = name
    logger.info("%s's Name: %s", user.first_name, update.message.text)

    reply_markup = ReplyKeyboardMarkup([["Yes", "No"]], resize_keyboard=False, one_time_keyboard=True)
    update.message.reply_text("Is this information correct?\n{}".format(facts_to_str(user_data)), reply_markup=reply_markup)

    return CONFIRMATION

def confirmation(update, context):
    chat_id = int(update.message.chat.id)
    master_ids.add(chat_id)
    reply = update.message.text
    if reply == "Yes":
        update.message.reply_text('Setup completed. Do /start to reset the bot.\n\nKey in your temperature when required.\nReminders begin at 6am & 12pm, and repeat every hour until you send your temperature.', reply_markup=temperature_markup)
        return ConversationHandler.END
    else:
        update.message.reply_text('Which group are you in?', reply_markup=group_markup)
        return GROUP

def temperature(update, context):
    user = update.message.from_user
    user_data = context.user_data
    chat_id = int(update.message.chat.id)

    temperature = update.message.text

    group = user_data['Group']
    name = user_data['Name']

    url = id_dict[group][0]
    entry_data = {
        id_dict[group][1] : name,
        id_dict[group][2] : temperature
    }

    send_temperature(url, entry_data)

    #checks whether it is AM or PM
    current_time = datetime.datetime.now()
    am_pm = int(current_time.strftime("%H"))
    #updates correspondingly (either sent_morning or sent_afternoon)
    if (0 <= am_pm < 12):
        sent_morning.add(chat_id)
    else:
        sent_afternoon.add(chat_id)

    logger.info("%s's Temperature: %s", user.first_name, update.message.text)
    update.message.reply_text('Hello {} from {}.\nYour form has been submitted.'.format(name, group))

def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation,", user.first_name)
    update.message.reply_text('You have cancelled the conversation.\n Use /start to restart.')
    return ConversationHandler.END

#debugging functions
def profile(update, context):
    user_data = context.user_data
    update.message.reply_text("Greetings {} from {}.\n".format(user_data['Name'], user_data['Group']))

def debug_scheduling(update, context):
    reply = 'master_ids = {}\nsent_morning={}\nsent_afternoon={}'.format(str(master_ids), str(sent_morning), str(sent_afternoon))
    update.message.reply_text(reply)

#scheduling
#initialise global scheduling variables: id lists
master_ids = set()
sent_morning = set()
sent_afternoon = set()

#morning
def morning_hourly(context):
    global master_ids
    global sent_morning

    #updates master_ids every hour
    for chat_id in persistence.get_user_data().keys():
        master_ids.add(int(chat_id))

    to_send_morning = [id for id in master_ids if id not in sent_morning]

    for chat_id in to_send_morning:
        context.bot.send_message(chat_id=chat_id,
                                 text = 'You are eligible for AM submission.\nPlease key in your temperature.',
                                 reply_markup=temperature_markup
                                 )

def afternoon_hourly(context):
    global master_ids
    global sent_afternoon

    #updates master_ids every hour
    for chat_id in persistence.get_user_data().keys():
        master_ids.add(int(chat_id))

    to_send_afternoon = [id for id in master_ids if id not in sent_afternoon]

    for chat_id in to_send_afternoon:
        context.bot.send_message(chat_id=chat_id,
                                 text = 'You are eligible for PM submission.\nPlease key in your temperature.',
                                 reply_markup=temperature_markup
                                 )

#initialise global scheduling variables: jobs
global job_morning_hourly
global job_afternoon_hourly

def morning_daily(context):
    global job_morning_hourly
    global job_afternoon_hourly
    global sent_morning

    try:
        job_afternoon_hourly.schedule_removal()
    except Exception:
        pass

    #resets those who have/have not sent their morning temperatures
    sent_morning = set()

    #only executes at 6.01am
    job_morning_hourly = j.run_repeating(morning_hourly, interval=3600, first=21660)

def afternoon_daily(context):
    global job_morning_hourly
    global job_afternoon_hourly
    global sent_afternoon

    try:
        job_morning_hourly.schedule_removal()
    except Exception:
        pass

    #resets those who have/have not sent their morning temperatures
    sent_afternoon = set()

    #execues at 12.01pm
    job_afternoon_hourly = j.run_repeating(afternoon_hourly, interval=3600, first=60)

def scheduling(): #executes morning_daily everyday at 12am & afternoon_daily everyday at 12pm
    j.run_daily(morning_daily, time=datetime.time(hour=16))
    j.run_daily(afternoon_daily, time=datetime.time(hour=4))

#st creed
def st_creed(update, context):
    update.message.reply_text("""We are security troopers,

Grounded in the SAF core values,

Professional in our conduct,

Upholding the highest standards of discipline.

We serve our units with pride, honour, and integrity.

We protect our camps and bases

With dedication and commitment.

We live by our motto,

Ready and vigilant.

We stand tall, we stand proud.

We will do what is right,

We stand our ground,

Never back down!""")

def main():
    conv_handler = ConversationHandler(
        entry_points = [CommandHandler('start', start)],

        states = {
            GROUP: [MessageHandler(Filters.regex('^(HQ|Section 1|Section 2|Section 3|Section 4|VES|TEST)$'), group)],
            NAME: [MessageHandler(Filters.text, name)],
            CONFIRMATION: [MessageHandler(Filters.regex('^(Yes|No)$'), confirmation)]
        },

        fallbacks = [CommandHandler('cancel', cancel)],
        allow_reentry=True,
        conversation_timeout=30,
        persistent=True,
        name="my_conversation"
    )

    profile_handler = CommandHandler('profile', profile)
    ds_handler = CommandHandler('ds', debug_scheduling)
    temperature_handler = MessageHandler(Filters.regex('^(35|36|37|37.6+|35.0|35.1|35.2|35.3|35.4|35.5|35.6|35.7|35.8|35.9|36.0|36.1|36.2|36.3|36.4|36.5|36.6|36.7|36.8|36.9|37.0|37.1|37.2|37.3|37.4|37.5)$'), temperature)
    st_handler = CommandHandler('st', st_creed)

    dp.add_handler(conv_handler)
    dp.add_handler(profile_handler)
    dp.add_handler(ds_handler)
    dp.add_handler(temperature_handler, group=1)
    dp.add_handler(st_handler)

    #executes scheduling
    scheduling()

    updater.start_polling()
    updater.idle()


    #start the webhook
    # updater.start_webhook(listen="0.0.0.0",
    #                       port=int(PORT),
    #                       url_path=TOKEN,
    #                       webhook_url=f"{URL}{TOKEN}")
    # updater.idle()

if __name__ == '__main__':
    main()
