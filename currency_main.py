from aiohttp import web, ClientSession
from aiohttp_cors import setup as cors_setup, ResourceOptions
from xml.dom import minidom
from loguru import logger
from datetime import datetime
import json
import aioredis


routes = web.RouteTableDef()
currency_lst = minidom.parse('list_currencies.asp')


def currency_dict(doc: minidom.Document):
    """
    Обрабатывает XML документ
    """
    items = doc.firstChild.getElementsByTagName('Item')
    dct = {}

    for item in items:
        try:
            _id = item.attributes['ID'].value
            name = item.getElementsByTagName('Name')[0].firstChild.data
            symbol = item.getElementsByTagName('ISO_Char_Code')[0].firstChild.data
            dct.update({symbol: (name, _id)})
        except AttributeError:
            pass

    return dct


def currency_list(curr_dct: dict):
    lst = []
    for key in curr_dct.keys():
        lst.append([key, curr_dct[key][0]])

    return lst


currency_dct = currency_dict(currency_lst)
currency_lst = currency_list(currency_dct)


def custom_json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False)


@routes.get('/api/list_currency')
async def get_currency_list(request: web.Request):
    """
    Возвращает список валют, который содержит все доступные валюты в формате [('RUB', 'Рубль'), ..]
    """
    logger.info(request)
    return web.json_response(currency_lst, dumps=custom_json_dumps, status=200)


def currency_processing(doc: minidom.Document):
    """
    Обрабатывает полученные данные
    Возвращает стоимость для первой даты, стоимость для второй даты, разница между второй и первой
    """
    first = doc.firstChild.firstChild.getElementsByTagName('Value')[0].firstChild.data
    last = doc.lastChild.lastChild.getElementsByTagName('Value')[0].firstChild.data
    # Деньги надо обрабатывать в минимальной единице (копейки), а не переводить во float, но этого здесь нет,
    # так как сайт ЦБ предоставляет и так округленные данные

    return first, last


@routes.get('/api/exchange_rate_difference')
async def get_exchange_rate_difference(request: web.Request):
    """
    Возвращает разницу курса относительно рубля между двумя датами за выбранную дату
    GET параметры: символьный код продукта, дата 1, дата 2
    Например: api/exchange_rate_difference?date_one=2021-01-15&date_second=2021-04-15&symb=USD"
    Возвращает курс за первую дату, курс за вторую дату и разницу между ними
    """
    logger.info(request)
    args = request.query
    logger.info(args)
    try:
        title = currency_dct.get(args.get("symb"))[0]
        currency_id = currency_dct.get(args.get("symb"))[1]
    except TypeError:
        return web.json_response({'Ошибка': 'Обменный курс не найден'}, status=404)
    try:
        date_one = args.get("date_one")
        date_one = datetime.strptime(date_one, '%Y-%m-%d').strftime('%d/%m/%Y')
        date_two = args.get("date_two")
        date_two = datetime.strptime(date_two, '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return web.json_response({'error': 'Error in parameters'}, status=422)
    exchange_api_link = 'http://www.cbr.ru/scripts/XML_dynamic.asp?' \
                        f'date_one={date_one}&' \
                        f'date_two={date_two}&' \
                        f'VAL_NM_RQ={currency_id}'

    redis: aioredis.Redis = request.app['redis_pool']
    first, last = None, None

    if exchange_dict := await redis.hgetall(currency_id, encoding='utf-8'):
        first = exchange_dict.get(date_one)
        last = exchange_dict.get(date_two)
    if first is None or last is None:
        async with ClientSession() as session:
            async with session.get(exchange_api_link) as resp:
                # Узнаем курс валют
                result = await resp.text()

        doc = minidom.parseString(result)
        try:
            val_curs = doc.firstChild.firstChild.data
            if val_curs == "Ошибка в параметрах":
                return web.json_response({'Ошибка': 'Ошибка в параметрах'}, status=422)
        except AttributeError:
            pass

        try:
            first, last = currency_processing(doc)
        except AttributeError:
            return web.json_response({'Ошибка': 'Ошибка в параметрах'}, status=422)
        await redis.hset(currency_id, date_one, first)
        await redis.hset(currency_id, date_two, last)
    # переводим значение валют во float с помощью замены символом
    first = float(first.replace(',', '.'))
    last = float(last.replace(',', '.'))

    jsn = {
        'Название': title,
        'Первый обменный курс': first,
        'Второй обменный курс': last,
        'Разница': last - first
    }

    return web.json_response(jsn, dumps=custom_json_dumps, status=200)


async def init():
    app = web.Application()
    app.add_routes(routes)

    cors = cors_setup(
        app,
        defaults={
            "*": ResourceOptions(
                allow_credentials=True, expose_headers="*", allow_headers="*",
            )
        },
    )

    for route in list(app.router.routes()):
        cors.add(route)

    redis_pool = await aioredis.create_redis_pool('redis://localhost')
    app['redis_pool'] = redis_pool

    return app


web.run_app(init())
