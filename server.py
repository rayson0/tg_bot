import logging
from random import *

import pymorphy3
import requests
from googletrans import Translator
from telegram import *
from telegram.ext import *

from database import DB

# объявление констант
BOT_TOKEN = '7128081432:AAFQRGW5gIKmPp8CsO5Y_cNvbHD7s5rrPAU'
API_URL = 'https://dog.ceo/api'
PART_OF_URL = {
    'all_breeds': '/breeds/list/all',
    'random_img': '/images/random'
}
correct_breeds = {
    'mush': 'malamute'
}
GAMES = ['Игра "Угадай-ка породу"', 'Получить фото по породе']
DB = DB('db/database.db')

response = requests.get(API_URL + PART_OF_URL['all_breeds']).json()
DB.create_table(tuple(map(lambda x: (x,), response['message'].keys())))

breads_game1 = {
    'correct': [],
    'choice': []
}
is_game1 = False
is_game2 = False

# процесс логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


# функция для перевода слова/нескольких слов
async def translate_breed(words, lang='ru'):
    morph = pymorphy3.MorphAnalyzer()

    translator = Translator()
    res = await translator.translate(words, dest=lang)

    return list(map(lambda x: morph.parse(x.text)[0].word, res)) if type(res) == list else res.text.lower()


def main():
    # Создаём объект Application.
    application = Application.builder().token(BOT_TOKEN).build()

    # Создаём обработчик сообщений типа filters.TEXT
    # После регистрации обработчика в приложении
    # эта асинхронная функция будет вызываться при получении сообщения
    # с типом "текст", т. е. текстовых сообщений.
    text_handler = MessageHandler(filters.TEXT, answer_for_buttons)

    # Регистрируем обработчик в приложении.
    application.add_handler(CommandHandler('start', start))
    application.add_handler(text_handler)

    # Запускаем приложение.
    application.run_polling()


async def start(update, context, greeting=True):
    user = update.effective_user
    reply_keyboard = [GAMES + ['История результатов']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    if greeting:
        message = (f'Привет, {user.first_name}! Я бот, который ассоциируется '
                   'с собаками. Ты можешь опробовать мои функции прямо сейчас!')
    else:
        message = 'Теперь ты в главном меню!'
    await update.message.reply_text(
        message,
        reply_markup=markup
    )


async def show_results(update, context, all=False):
    results = DB.get_results(update.effective_user.id, all)
    message = f'Статистика {'последних 3 или менее' if not all else 'всех'} игр:\n\n'
    for get_points, all_points, date_time in results:
        date = '.'.join(date_time.split()[0].split('-')[::-1])
        time = date_time.split()[1][:date_time.split()[1].rindex('.')]
        message += f'Дата: {date}\nВремя: {time}\nРезультат: {get_points}/{all_points}\n\n'
    if not all:
        message += 'Если нужна полная статистика, нажми нужную кнопку в меню'

    reply_keyboard = [['В главное меню']] if all else [['Показать всю историю', 'В главное меню']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    await update.message.reply_text(message,
                                    reply_markup=markup)


async def rules_choice_breed_of_dog(update, context):
    global is_game1
    user = update.effective_user
    reply_keyboard = [['Готов!']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    is_game1 = True
    await update.message.reply_text(
        f'{user.first_name}, ты попал в игру "Угадай-ка породу"! Сейчас я тебя ознакомлю с форматом игры:\n\n' +
        'Каждый раз перед тобой будет появляться фото собаки, и из 4 предложенных вариантов пород тебе нужно ' +
        'выбрать одну. После выбора породы бот напишет тебе, был ли ты прав или нет. Количество верных и ' +
        'неверных ответов будет сохранено, и после окончания игры можно посмотреть итоговую статистику.\n\n' +
        'А теперь не тормози и вперед отгадывать!',
        reply_markup=markup)


async def choice_breed_of_dog(update, context):
    need_breeds = DB.get_breads(4)
    need_breeds_ru = await translate_breed(need_breeds)
    choice_breed = choice(need_breeds)

    breads_game1['correct'] = breads_game1.get('correct', []) + [await translate_breed(choice_breed)]

    response = requests.get(f'{API_URL}/breed/{choice_breed}{PART_OF_URL['random_img']}').json()

    if response['status'] == 'error':
        message = ('Прости! Возникли неполадки! В данный момент не получится поиграть((\n\n'
                   'Предлагаю вернуться в главное меню!')

        reply_keyword = [['В главное меню']]
        markup = ReplyKeyboardMarkup(reply_keyword, one_time_keyboard=False)
        await update.message.reply_text(message,
                                        reply_markup=markup)
    else:
        image = response['message']

        reply_keyword = [need_breeds_ru[:2], need_breeds_ru[2:]]
        markup = ReplyKeyboardMarkup(reply_keyword, one_time_keyboard=False)
        await context.bot.send_photo(update.message.chat_id,
                                     image,
                                     caption='Кто это?',
                                     reply_markup=markup)


async def is_correct_choice_bread(update, context):
    breads_game1['choice'] = breads_game1.get('choice', []) + [update.message.text.lower()]
    if breads_game1['correct'][-1].lower() == breads_game1['choice'][-1].lower():
        message = 'Молодец! Верный ответ!\n\nПродолжим игру?'
    else:
        message = f'''К сожалению, неверно. Верный ответ - {breads_game1['correct'][-1]}
                    \n\nПродолжим игру?'''
    reply_keyword = [['Да!', 'Нет!']]
    markup = ReplyKeyboardMarkup(reply_keyword, one_time_keyboard=False)
    await update.message.reply_text(message,
                                    reply_markup=markup)


async def exit_game1(update, context):
    global is_game1
    get_points = sum(map(lambda i: breads_game1['correct'][i] == breads_game1['choice'][i],
                         range(len(breads_game1['correct']))))
    all_points = len(breads_game1['correct'])
    breads_game1.clear()
    is_game1 = False

    DB.write_result(update.effective_user.id, get_points, all_points)

    user = update.effective_user
    message = (f'Тогда завершаем игру!\n\n{user.first_name}, ты показал хороший результат! ' +
               f'Твоя статистика: {get_points}/{all_points}\n\nПредлагаю сыграть снова!')

    reply_keyboard = [GAMES + ['История результатов']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    await update.message.reply_text(
        message,
        reply_markup=markup
    )


async def get_photo_of_dog(update, context, bread=False):
    user = update.effective_user
    message = f'{user.first_name}, выбери породу собаки из предложенных или напиши самостоятельно'

    random_list_or_breeds = DB.get_breads(4)
    random_list_or_breeds_ru = await translate_breed(random_list_or_breeds)
    reply_keyboard = [random_list_or_breeds_ru[:2], random_list_or_breeds_ru[2:], ['В главное меню']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

    if bread:
        response = requests.get(f'{API_URL}/breed/{bread}{PART_OF_URL['random_img']}').json()
        if response['status'] == 'error':
            print(bread)
            message = 'Ой! Произошла ошибка! Давай попробуем выбрать снова!'
            await update.message.reply_text(message,
                                            reply_markup=markup)
        else:
            image = response['message']
            message = 'Держи заветное фото!\n\n' + message
            await context.bot.send_photo(update.message.chat_id,
                                         image,
                                         caption=message,
                                         reply_markup=markup)
    else:
        await update.message.reply_text(message,
                                        reply_markup=markup)


async def answer_for_buttons(update, context):
    global is_game1, is_game2
    if update.message.text == GAMES[0]:
        await rules_choice_breed_of_dog(update, context)
    elif update.message.text == GAMES[1]:
        await get_photo_of_dog(update, context)
        is_game2 = True
    elif update.message.text == 'История результатов':
        await show_results(update, context)
    elif update.message.text == 'Показать всю историю':
        await show_results(update, context, all=True)
    elif update.message.text == 'В главное меню':
        await start(update, context, greeting=False)
    elif update.message.text == 'Готов!':
        await choice_breed_of_dog(update, context)
    elif is_game1 and update.message.text:
        if update.message.text == 'Да!':
            await choice_breed_of_dog(update, context)
        elif update.message.text == 'Нет!':
            await exit_game1(update, context)
        else:
            await is_correct_choice_bread(update, context)
    elif is_game2 and update.message.text:
        await get_photo_of_dog(update, context, bread=await translate_breed(update.message.text, lang='en'))


if __name__ == '__main__':
    main()
