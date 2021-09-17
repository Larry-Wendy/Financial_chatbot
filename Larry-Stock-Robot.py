# Import necessary modules
import telegram, os
import logging
import re
import random
import ast
import http.client
from telegram import ReplyKeyboardMarkup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)
from rasa_nlu.training_data import load_data
from rasa_nlu.model import Trainer
from rasa_nlu import config
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates
import numpy as np

conn = http.client.HTTPSConnection("alpha-vantage.p.rapidapi.com")

headers = {
    'x-rapidapi-host': "alpha-vantage.p.rapidapi.com",
    'x-rapidapi-key': "3e2ecfd2demsh841f6770595e572p1f164djsn178a694fcafb"
    }

# train rasa interpreter
trainer = Trainer(config.load("config_spacy.yml"))
# Load the training data
training_data = load_data('Larry-Stock-rasa.md')
# Create an interpreter by training the model
interpreter = trainer.train(training_data)

# global variable declaration
params = []
pointlist = []
name_temp = None
# define the states
INIT = 0
STOCK_FUC = 1
PLOT_FUC = 2
CURRENCY_FUC = 3
state = INIT
# cannot understand
default = "Sorry, I don't understand what you mean. If you want to begin a new function, just choose one!"
# chit chat reply
rules = {'i wish (.*)': ['What would it mean if {0}', 
                         'Why do you wish {0}', 
                         "What's stopping you from realising {0}"
                        ], 
         'do you remember (.*)': ['Did you think I would forget {0}', 
                                  "Why haven't you been able to forget {0}", 
                                  'What about {0}', 
                                  'Yes .. and?'
                                 ], 
         'do you think (.*)': ['if {0}? Absolutely.', 
                               'No chance.'
                              ], 
         'if (.*)': ["Do you really think it's likely that {0}", 
                     'Do you wish that {0}', 
                     'What do you think about {0}', 
                     'Really--if {0}'
                    ]
        }
# response rules
response = [
    "I'm sorry, I couldn't find anything like that. ╮(๑•́ ₃•̀๑)╭",
    "Great! Here are some brief information~Daily Prices(open, high, low, close) and Volumes~ about {}",
    "Great! Here are some brief information about Realtime Currency Exchange Rate:"
]
# ****************************************

bot = telegram.Bot(token='1921761187:AAF8CB0YZRBVI_-LtD967nD5bE_kNodM8vQ')
updater = Updater(token='1921761187:AAF8CB0YZRBVI_-LtD967nD5bE_kNodM8vQ', request_kwargs={'proxy_url': 'http://127.0.0.1:7890'})

dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# start dictation
def start(update, context):
     update.message.reply_text(
        "Hi! My name is Larry_Stock_Robot, an intelligent financial chat robot. I can help you search for information about any stocks or FX currencies.\n"
        "Now you can choose Stock fuction or Currency Exchange fuction to begin my service!\n"
        "Welcome to chat with me! (๑•ᴗ•๑)♡ "
        )

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# Case conversion dictation
def caps(update, context):
    print(type(context.args))
    text_caps = ' '.join(context.args).upper()
    return text_caps

caps_handler = CommandHandler('caps', caps)
dispatcher.add_handler(caps_handler)

# unknown dictation
def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=default)

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

# ****************************************
def replace_pronouns(message):
    
    message = message.lower()
    
    if ' me ' in message:
        # Replace 'me' with 'you'
        return re.sub(' me ', ' you ', message)
    if 'my' in message:
        # Replace 'my' with 'your'
        return re.sub('my', 'your', message)
    if ' your ' in message:
        # Replace 'your' with 'my'
        return re.sub(' your ', ' my ', message)
    if ' you ' in message:
        # Replace 'you' with 'me'
        return re.sub(' you ', ' me ', message)
    
    return message

def match_rule(update, context, message):
    
    for pattern, value in rules.items():
        # Create a match object
        match = re.search(pattern, message)
        # 如果匹配成功
        if match is not None:
            # Choose a random response
            response = random.choice(rules[pattern])
            # 如果需要人称替换
            if '{0}' in response:
                phrase = re.search(pattern, message).group(1)
                phrase = replace_pronouns(phrase)
                # 回复消息
                update.message.reply_text(response.format(phrase))
            else:
                # 回复消息
                update.message.reply_text(response)
            return True
        
    return False

# 提取股票名或货币名
def find_name(message):
    flag=0  #0为股票，1为货币
    name = None
    name_words = []
    
    # Create a pattern for finding capitalized words
    name_pattern = re.compile("[A-Z]{1}[A-Z]+")
    name_pattern_currency = re.compile("[A-Z]+ to [A-Z]+")
    name_intraday = re.compile("intraday|in one day|in a day|one day|within a day")
    name_daily = re.compile("daily|diurnal|day to day|in days")
    name_weekly = re.compile("weekly|week to week|in weeks")
    name_monthly = re.compile("monthly|month to month|in months")
    name_price = re.compile("price|price-change")
    name_volume = re.compile("volume|volume-change") 
    name_stock = re.compile("stock|stocks|Stock|Stocks")
    name_currency = re.compile("currency|currencis|Currency|Currencies")
    name_high = re.compile("high|High|highest|Highest|top|Top")
    name_low = re.compile("low|Low|lowest|Lowest|bottom|Bottom")
    
    if name_pattern_currency.search(message):
        flag = 1
    
    if name_intraday.search(message):
        name_words.append('intraday')
    elif name_daily.search(message):
        name_words.append('daily')
    elif name_weekly.search(message):
        name_words.append('weekly')
    elif name_monthly.search(message):
        name_words.append('monthly')
    
    if name_price.search(message):
        name_words.append('price')
    elif name_volume.search(message):
        name_words.append('volume')
    
    if name_high.search(message):
        name_words.append('high')
    elif name_low.search(message):
        name_words.append('low')
    
    if name_stock.search(message) and not name_pattern.search(message):
        name_words.append('stock')
    elif name_currency.search(message) and not name_pattern.search(message):
        name_words.append('currency')
    # Get the matching words in the string
    name_words += name_pattern.findall(message)
    '''
    # Create a pattern for checking if the keywords occur
    name_keyword = re.compile("name|call|movie|TV series|tv series|television show|drama|show", re.I)
    
    if name_keyword.search(message) or name_words:
        name_new_pattern = re.compile("[0-9]{1}[0-9]*")
        name_words += name_new_pattern.findall(message)
    '''    
    if len(name_words) > 0:
        # Return the name if the keywords are present
        name = ' '.join(name_words)
     
    return flag, name

# 自动将股票名转换大写
def turn_name(message):
    if "name*" in message:
        index = message.index("name*") + len("name*")
        name = message[index:].upper()
        name_list = name.split(' ')
        
        for i in range(len(name_list)):
            if name_list[i] == '':
                continue
            else:
                index = i
                break
                
        newname = '%20'.join(name_list[index:])
        return newname
# work_function_choose
def choose_function_work(update, context, name):
    print("work_function_choose")
    global state
    print(name)
    if name == None:
        update.message.reply_text(default)
        return 0
    if name == 'stock':
        update.message.reply_text(
            "Great! Remember that the stock's name should be all made up of capital letters.\n"
            "For example 'search AAPL'.")
        state = STOCK_FUC
    elif name == 'currency':
        update.message.reply_text(
            "Perfect! You can search the realtime exchange rate for any pair of digital currency (e.g.Bitcoin) and physical currency (e.g.USD).\n"
            "Remember that you are supposed to use 'to' to connect two currencies.\n"
            "For example 'search JPY to USD'.")
        state = CURRENCY_FUC
    return 0

# work_stock_search
def search_stock_work(update, context, name):
    print("work_stock_search")
    print(name)
    global name_temp
    name_temp = name
    if name == None:
        update.message.reply_text(default)
        return params
    # 获得api数据
    conn.request("GET", "/query?function=TIME_SERIES_DAILY&symbol="+name+"&outputsize=compact&datatype=json", headers=headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    
    # 将字符串转换为字典格式
    data = ast.literal_eval(data)
    # 搜索错误时返回
    if len(data) <= 1:
        update.message.reply_text(response[0])
        return []
    
    # params存放搜索结果
    keys = list(data["Time Series (Daily)"].keys())
    params = data["Time Series (Daily)"][keys[0]]
    update.message.reply_text(response[1].format(name)+'@'+keys[0]+':')
    update.message.reply_text(
        "The day open price: " +params['1. open']+'\n'
        "The day highest price: "+params['2. high']+'\n'
        "The day lowest price: "+params['3. low']+'\n'
        "The day close price: "+params['4. close']+'\n'
        "The day trading volume: "+params['5. volume'])
    update.message.reply_text("Do you want to draw stock trend charts about "+name+" ?")
    # 更新params    
    return params 

# work_currency_search
def search_currency_work(update, context, name):
    print("work_currency_search")
    print(name)
    name=str(name).split()
    if name == None:
        update.message.reply_text(default)
        return params
    # 获得api数据
    conn.request("GET", "/query?to_currency="+name[1]+"&function=CURRENCY_EXCHANGE_RATE&from_currency="+name[0], headers=headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    params = data
    data = eval(data)
    # 搜索错误时返回
    if list(data.keys())[0]=="Error Message":
        update.message.reply_text(response[0])
        return []
    
    print(params)
    update.message.reply_text(response[2])
    update.message.reply_text(
        "The exchange rate is "+data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]+'.\n'
        "That means 1 "+name[0]+" can exchange "+data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]+' '+name[1]+':)')

    # 更新params    
    return params 

# work_digitalcurrency_search
def search_digitalcurrency_work(update, context, name):
    print("work_digitalcurrency_search")
    print(name)
    name=str(name).split()
    if name == None:
        update.message.reply_text(default)
        return []
    # 获得api数据
    conn.request("GET", "/query?from_currency="+name[0]+"&function=CURRENCY_EXCHANGE_RATE&to_currency="+name[1], headers=headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    params = data
    data = eval(data)
    # 搜索错误时返回
    if list(data.keys())[0]=="Error Message":
        update.message.reply_text(response[0])
        return []

    update.message.reply_text(response[2])
    update.message.reply_text(
        "The exchange rate is "+data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]+'.\n'
        "That means 1 "+name[0]+" can exchange "+data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]+' '+name[1]+':)')

    # 更新params    
    return params 

# work_plot
def plot_work(update, context, name, name_temp):
    print("work_plot")
    print(name_temp)
    name=str(name).split()
    print(name)
    if len(name)<=1:
        update.message.reply_text(default)
        return params
    
    if name[0]=='intraday':
        conn.request("GET", "/query?interval=5min&function=TIME_SERIES_INTRADAY&symbol=" + name_temp + "&datatype=json&output_size=compact", headers=headers)
    elif name[0]=='daily':
        conn.request("GET", "/query?function=TIME_SERIES_DAILY&symbol=" + name_temp + "&outputsize=compact&datatype=json", headers=headers)
    elif name[0]=='weekly':
        conn.request("GET", "/query?function=TIME_SERIES_WEEKLY&symbol=" + name_temp + "&datatype=json", headers=headers)
    elif name[0]=='monthly':
        conn.request("GET", "/query?symbol=" + name_temp + "&function=TIME_SERIES_MONTHLY&datatype=json", headers=headers)
    
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    print(data)
    data = ast.literal_eval(data)
    # 搜索错误时返回
    if len(data) <= 1:
        update.message.reply_text(response[0])
        return [] 
    
    price,volume,date = [],[],[]
    if name[0]=='intraday':
        data = data["Time Series (5min)"]
    elif name[0]=='daily':
        data = data["Time Series (Daily)"]
    elif name[0]=='weekly':
        data = data["Weekly Time Series"]
    elif name[0]=='monthly':
        data = data["Monthly Time Series"]
    
    keys = list(data.keys())
    for i in keys[:50]:
        price.append(float(data[i]["1. open"]))
        volume.append(float(data[i]["5. volume"]))
        date.append(i)
    
    # find highpoint and lowpoint
    pointlist=[]

    if name[0]=='intraday':
        print(date)
        dates = [datetime.strptime(d, '%Y-%m-%d %H:%M:%S') for d in date]
        print(dates)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())
        plt.xticks(dates[0::10])
    else:
        dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in date]
        print(dates)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())
        plt.xticks(dates[0::10])
    if name[1]=='price':
        pointlist.append(max(price))
        pointlist.append(date[price.index(max(price))])
        pointlist.append(min(price))
        pointlist.append(date[price.index(min(price))])
        #x=np.arange(0,50)
        if name[0]=='intraday':
            plt.title(name_temp+' price '+name[0]+' '+date[0][0:10])
        else:
            plt.title(name_temp+' price '+name[0])
        plt.grid()
        plt.ylabel("open price")
        plt.xlabel("time range")
        plt.plot(dates, price)
        plt.savefig('price_plot.png')
        update.message.reply_photo(open('./price_plot.png','rb'))
        os.remove('./price_plot.png')
        
    elif name[1]=='volume':
        pointlist.append(max(volume))
        pointlist.append(date[volume.index(max(volume))])
        pointlist.append(min(volume))
        pointlist.append(date[volume.index(min(volume))])
        if name[0]=='intraday':
            plt.title(name_temp+' volume '+name[0]+' '+date[0][0:10])
        else:
            plt.title(name_temp+' volume '+name[0])
        plt.grid()
        plt.ylabel("trading volume")
        plt.xlabel("time range")
        plt.plot(dates,volume,color='r')
        plt.savefig('volume_plot.png')
        update.message.reply_photo(open('./volume_plot.png','rb'))
        os.remove('./volume_plot.png')
    plt.show()
    
    print(pointlist)
    update.message.reply_text("You can search the highest point or the lowest point in the chart~")
    return pointlist

# work_find_point
def find_point_work(update, context, name, pointlist):
    print(pointlist)
    if name == None:
        update.message.reply_text(default)
        return []
    if name == 'high':
        update.message.reply_text("Highest point is "+str(pointlist[0])+" at "+pointlist[1])
    elif name == 'low':
        update.message.reply_text("Lowest point is "+str(pointlist[2])+" at "+pointlist[3])
    return 0

# understand messages and reply
def respond(update, context, message):
    target = interpreter.parse(message)
    global pointlist
    global params
    global state
    
    # remove the punctuation
    r = '[’!"#$%&\'()+,-./:;<=>?@[\\]^_`{|}~]+'
    message = re.sub(r,'',message)
    print(message)
    # params test
    print(params)
    
    flag = 0
    name = None
    if(target['entities'] is not None):
        flag, name = find_name(message)
        if name == None:
            name = turn_name(message)
        elif len(name.split()) >= 3:
            update.message.reply_text(response[0])
            return []
    print(name)
    message = message.lower()
    
    print(target['intent']['name'])
    # search info according to the intent
    if target['intent']['name'] == 'work_function_search':
        choose_function_work(update, context, name)
    elif target['intent']['name'] == 'work_stock_search' and (state == STOCK_FUC or state == PLOT_FUC):
        params = search_stock_work(update, context, name)
    
    elif target['intent']['name'] == 'work_currency_search' and state == CURRENCY_FUC:
        params = search_currency_work(update, context, name)    
    
    elif target['intent']['name'] == 'work_digitalcurrency_search'and state == CURRENCY_FUC:
        params = search_digitalcurrency_work(update, context, name) 
    
    elif target['intent']['name'] == 'affirm' and (state == STOCK_FUC or state == PLOT_FUC):
        update.message.reply_text("Great, I could draw price-change and volume-change charts with intraday, daily, weekly and monthly, choose one!")
        state = PLOT_FUC
        
    elif target['intent']['name'] == 'deny' and (state == STOCK_FUC or state == PLOT_FUC):
        update.message.reply_text("Okay-_-")
        state == STOCK_FUC
        
    elif target['intent']['name'] == 'work_plot' and state == PLOT_FUC:       
        pointlist = plot_work(update, context, name, name_temp)
        
    elif target['intent']['name'] == 'work_find_point' and state == PLOT_FUC:       
        find_point_work(update, context, name, pointlist)
    
    elif target['intent']['name'] == 'greet':
        # greet消息
        greet = [
                    "Hello~",
                    "Hey!", 
                    "Hi~",
                    "Hey there~"
                ]
        update.message.reply_text(random.choice(greet))
    
    elif target['intent']['name'] == 'bot_challenge':
        # bot challenge消息
        bot = [
                "I'm Larry_Stock_Robot. I can help you search for information about any stocks or FX currencies.", 
                "My name is Larry_Stock_Robot. I can help you search for information about any stocks or FX currencies.",
                "My name is Larry_Stock_Robot, you can call me Larry. I can help you search for information about any stocks or FX currencies."
              ]
        update.message.reply_text(random.choice(bot))
    
    elif target['intent']['name'] == 'mood_great':
        # mood great消息
        great = [
                    "Great!",
                    "Yeah!",
                    "Cheers!"
                ]
        update.message.reply_text(random.choice(great))
    
    elif target['intent']['name'] == 'thanks':
        # thank消息
        thank = [
                    "I am glad I can help.",
                    "You are welcome.",
                    "So kind of you.",
                    "It is my pleasure."
                ]
        update.message.reply_text(random.choice(thank))
    
    elif target['intent']['name'] == 'goodbye':
        # goodbye消息
        bye = [
                "bye ~",
                "goodbye ~",
                "see you around ~",
                "see you later ~",
                "see you ~"
              ]
        update.message.reply_text(random.choice(bye))
    
    else:
        update.message.reply_text(default)

# 消息回复功能
def msg(update, context):
    message = update.message.text
    
    result = match_rule(update, context, message)
    
    if result == False:
        respond(update, context, message)
    
    
msg_handler = MessageHandler(Filters.text, msg)
dispatcher.add_handler(msg_handler)
#**************************************************************************

# 启停
updater.start_polling()
#updater.idle()

# inline
from telegram import InlineQueryResultArticle, InputTextMessageContent
def inline_caps(update, context):
    query = update.inline_query.query
    if not query:
        return
    results = list()
    results.append(
        InlineQueryResultArticle(
            id=query.upper(),
            title='Caps',
            input_message_content=InputTextMessageContent(query.upper())
        )
    )
    context.bot.answer_inline_query(update.inline_query.id, results)

from telegram.ext import InlineQueryHandler
inline_caps_handler = InlineQueryHandler(inline_caps)
dispatcher.add_handler(inline_caps_handler)
