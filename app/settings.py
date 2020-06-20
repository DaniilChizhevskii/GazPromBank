import os

home = '/root/GazProm/app'
static = os.path.join(home, '../static')
templates = os.path.join(home, '../templates')
secret_key = '\xe9\xb9\x95\x83ZZ\x94R7\x923kU\xea\xe4_=.\xe2\xf4\x97\xb6e*'
debug = True
port = int(os.environ.get("PORT", 443))
db_path = os.path.join(home, 'app.db')

reputationRates = {
	'comment': {
		'up': 2,
		'down': -1
	},
	'thread': {
		'up': 5,
		'down': -2
	}
}

badgeTypes = {
	'autobiography': ['Автобиограф', 10],
	'first_thread': ['Первая активность', 10],
	'first_comment': ['Начинающий комментатор', 5],
	'first_up': ['Меценат', 10],
	'first_down': ['Критик', 5],
	'badges_lover': ['Собиратель значков', 30],
	'first_poll': ['Голос народа', 10],
	'registered': ['Новичок', 10]
}

statuses = {
	'open': 'Открыто',
	'closed': 'Закрыто',
	'success': 'Успешно решено',
	'deleted': 'Удалено'
}

domain = 'gazprom.topstack.dev'