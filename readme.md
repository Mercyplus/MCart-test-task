# mcart test task

### Техническое задание:

Реализовать микросервис, который будет предоставлять http api, для показа разницы курса той или иной валюты относительно рубля за выбранные даты.

### Проделанная работа:

#### Получение данных

Для получения курсов валют использовался [API](http://www.cbr.ru/development/sxml/), который принимал две даты от пользователя и возвращал XML документ, содержащий ежедневные курсы валют в рублях между двумя датами которые.

Список доступных валют был получен [отсюда](http://www.cbr.ru/scripts/XML_valFull.asp).

Для оптимизации количества запросов к API было использовано кэширование. Для кэширования в проекте я применил Redis, как популярное и удобное решение. Для взаимодействия с Redis было использовано асинхронная библиотека `aioredis`. Если данных нет в Redis, то они запрашиваются у API, а потом складываются в Redis.

#### Микросервис

Для написания микросервиса я использовал веб-фреймворк aiohttp, из-за асинхронности и актуальности.

Сервис предоставляет два метода:

Список доступных валют в формате (символьный код (RUR), название). `/api/currency_list`

Получение разницы курса относительно рубля между двумя датами за выбранную дату, метод должен принимать символьный код валюты, и две даты. Метод возвращает курс за первую дату, курс за вторую дату и разницу между ними. `/api/exchange_rate_difference?date_one=date&date_two=date&symb=USD` Если пользователь указывает неверные аргументы или валюта не будет найдена, то пользователь получит соответствующую ошибку.

#### Запуск:

Для установки тестового виртуального окружения выполните следующие команды:
```sh
python3 -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
```

Помимо python приложения необходимо запустить Redis. Redis можно развернуть в Docker контейнере:
```sh
docker run --name redis-container -p 6379:6379 -d redis
```

Для запуска:
```sh
python currency_main.py
```

## Тесткейсы:
Получение списка валют:
```sh
curl http://127.0.0.1:8080/api/list_currency
```

Должен вернуть:
```json
[["AUD", "Австралийский доллар"], ["AZN", "Азербайджанский манат"], ["GBP", "Фунт стерлингов Соединенного королевства"], ["AMD", "Армянский драм"], ["BYN", "Белорусский рубль"], ["BGN", "Болгарский лев"], ["BRL", "Бразильский реал"], ["HUF", "Венгерский форинт"], ["HKD", "Гонконгский доллар"], ["DKK", "Датская крона"], ["USD", "Доллар США"], ["EUR", "Евро"], ["INR", "Индийская рупия"], ["KZT", "Казахстанский тенге"], ["CAD", "Канадский доллар"], ["KGS", "Киргизский сом"], ["CNY", "Китайский юань"], ["MDL", "Молдавский лей"], ["NOK", "Норвежская крона"], ["PLN", "Польский злотый"], ["ROL", "Румынский лей"], ["RON", "Румынский лей"], ["XDR", "СДР (специальные права заимствования)"], ["SGD", "Сингапурский доллар"], ["TJS", "Таджикский сомони"], ["TRY", "Турецкая лира"], ["TMM", "Туркменский манат"], ["TMT", "Новый туркменский манат"], ["UZS", "Узбекский сум"], ["UAH", "Украинская гривна"], ["CZK", "Чешская крона"], ["SEK", "Шведская крона"], ["CHF", "Швейцарский франк"], ["ZAR", "Южноафриканский рэнд"], ["KRW", "Вон Республики Корея"], ["JPY", "Японская иена"]]
```

Получение разницы курсов:
```sh
curl http://127.0.0.1:8080/api/exchange_rate_difference?date_one=2021-01-15&date_two=2021-04-15&symb=USD
```

Должен вернуть:
```json
{"Название": "Доллар США", "Первый обменный курс": 73.7961, "Второй обменный курс": 75.6826, "Разница": 1.886499999999998}
```