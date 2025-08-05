### Описание проекта:
Проект реализует в себе веб-приложение для публикации рецептов и взаимодействия с другими пользователями. API бекенда взаимодействует с рецептами, подписками пользователей, корзиной покупок, избранными рецептами. К проекту подключена авторизация по токену. Для сборки проекта испольуется docker, для публикации проекта на удаленнный сервер настроен CI/CD с помощью github actions.

Проект размещен на сервере по адреcу https://foodgram771.ddns.net

### Используемые технологии:

- **Язык программирования**: Python
- **Фреймворк**: Django
- **База данных**: PostgreSQL
- **Инструмент сборки**: Docker
- **CI/CD**: GitHub Actions

### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/Vl0202/foodgram
cd foodgram
```

В корневой директории проекта создать файл с переменными окружения .env и перейти в директорию infra:

```
cd infra
```

Запустить docker-compose

```
docker-compose up -d
```

По адресу http://localhost/api/docs/ можно изучить спецификацию API.

### Как запустить проект (локально):

```
git clone https://github.com/Vl0202/foodgram
cd backend
```
Создание и активациия виртуального окружения
```
python -m venv venv
source venv/bin/activate  # для Linux/Mac
```
Установка зависимостей
```
pip install -r requirements.txt
```

Создание базы данных
```
python manage.py migrate
```
```
python manage.py loaddata ingredients.json
python manage.py loaddata tags.json
python manage.py createsuperuser
python manage.py runserver
```

### Доступы:

Документация API: http://localhost/api/docs/
Админка: http://localhost/admin/
Основной сайт: http://localhost/
Производственный сервер: https://foodgram771.ddns.net/

### Авторы
GitHub: @Vl0202
Ли Владимир

