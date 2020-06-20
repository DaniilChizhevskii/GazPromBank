from flask import render_template
from app.settings import *
from datetime import datetime
import sqlite3
import json
import time
import random
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

database = sqlite3.connect("app.db")

def screen(argument):
	return argument.replace('"', '""')

def isNull(argument):
	return argument in ['', None]

def isAutorized(email, password):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT id, blocked FROM users where email="%s" AND password="%s"' % (screen(email), screen(password)))
	return cursor.fetchone()

def sendReset(email):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT id, name FROM users WHERE email="%s"' % email)
	user = cursor.fetchone()
	if user:
		link = ''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(128))
		cursor.execute('INSERT INTO reset VALUES ("%s", %s)' % (link, user['id']))
		conn.commit()
		sendEmail(email, 'Сброс пароля', render_template('email.html', domain=domain, name=user['name'], link=link))
		return True
	return False

def forgotRestore(link):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT id FROM reset WHERE link="%s"' % screen(link))
	result = cursor.fetchone()
	if result:
		cursor.execute('DELETE FROM reset WHERE link="%s"' % screen(link))
		conn.commit()
		return result['id']
	return False

def getInvites():
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM invites')
	codes = cursor.fetchall()
	codes.reverse()
	return codes

def generateInvite(user_id):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('INSERT INTO invites VALUES("%s", %s, 1)' % (''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(16)), user_id))
	conn.commit()

def validateInvite(code):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT valid FROM invites WHERE code="%s"' % screen(code))
	result = cursor.fetchone()
	if result and result['valid']:
		cursor.execute('UPDATE invites SET valid=0 WHERE code="%s"' % screen(code))
		conn.commit()
		return True
	return False

def registerUser(name, email, password):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT COUNT(*)+1 FROM users')
	identifier = cursor.fetchone()[0]
	cursor.execute('INSERT INTO users VALUES(%s, "%s", "%s", "%s", %s, %s, %s, "%s", "%s", %s, "%s", "Не указан")' % (identifier, screen(password), screen(email), 'Ура! Встречайте новичка!', 0, 0, 0, 'Пока этот пользователь ничего о себе не рассказал.', screen(name), 1, '[]'))
	conn.commit()
	giveBadge(identifier, 'registered')
	sendNotification(identifier, 'Поздравляем с регистрацией!', 'Теперь ты - полноценный пользователь нашего сервиса.', 'warning', 'sunrise', '/threads')

def getUser(identifier):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM users where id="%s"' % identifier)
	user = cursor.fetchone()
	if user:
		user = dict(user)
		user['badges'] = json.loads(user['badges'])
		user['notifications'] = getNotifications(identifier)
	return user

def createThread(owner, title, content, department, theme):
	if isNull(content):
		content = 'Автор обсуждения решил не раскрывать подробностей...'
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT COUNT(*)+1 FROM threads')
	identifier = cursor.fetchone()[0]
	cursor.execute('INSERT INTO threads VALUES(%s, %s, "%s", "%s", %s, 0, 0, 0, "open", "%s", "%s")' % (identifier, owner, screen(title), screen(content), int(time.time()), screen(department), screen(theme)))
	conn.commit()
	giveBadge(owner, 'first_thread')
	cursor.execute('SELECT id FROM users WHERE department="%s"' % department)
	for user in cursor.fetchall():
		if user[0] != owner:
			sendNotification(user[0], 'Новое обсуждение', 'В твоём департаменте опубликовано новое обсуждение', 'success', 'message-square', '/thread/%s' % identifier)
	return identifier

def statusToText(status):
	return statuses[status]

def fromTimestamp(timestamp):
	return datetime.utcfromtimestamp(timestamp + 3600 * 3).strftime('%d.%m.%Y %H:%M')

def getThreads(offset=0, count=10):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT id, title, date, up, down, status, views FROM threads ORDER BY date DESC')
	threads = cursor.fetchall()
	length = len(threads)
	if offset > 0:
		offset -= 1
	threads = threads[offset * 10:][:count]
	for x in range(len(threads)):
		threads[x] = dict(threads[x])
		threads[x]['status'] = statusToText(threads[x]['status'])
		threads[x]['date'] = fromTimestamp(threads[x]['date'])
	return (threads, length)

def getThreadsByDepartment(department):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT id, title, date, up, down, status, views FROM threads WHERE department="%s" ORDER BY date DESC' % screen(department))
	threads = cursor.fetchall()
	threads = threads[:25]
	for x in range(len(threads)):
		threads[x] = dict(threads[x])
		threads[x]['status'] = statusToText(threads[x]['status'])
		threads[x]['date'] = fromTimestamp(threads[x]['date'])
	return threads

def getThreadsByTheme(theme):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT id, title, date, up, down, status, views FROM threads WHERE theme="%s" ORDER BY date DESC' % screen(theme))
	threads = cursor.fetchall()
	threads = threads[:25]
	for x in range(len(threads)):
		threads[x] = dict(threads[x])
		threads[x]['status'] = statusToText(threads[x]['status'])
		threads[x]['date'] = fromTimestamp(threads[x]['date'])
	return threads

def getThreadsByUser(identifier):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT id, title, date, up, down, status, views FROM threads WHERE owner=%s ORDER BY date DESC' % identifier)
	threads = cursor.fetchall()
	for x in range(len(threads)):
		threads[x] = dict(threads[x])
		threads[x]['status'] = statusToText(threads[x]['status'])
		threads[x]['date'] = fromTimestamp(threads[x]['date'])
	return threads

def getThread(identifier):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('UPDATE threads SET views=views+1 WHERE id="%s"' % identifier)
	conn.commit()
	cursor.execute('SELECT * FROM threads WHERE id="%s"' % identifier)
	thread = cursor.fetchone()
	if thread:
		thread = dict(thread)
		thread['viewed_status'] = statusToText(thread['status'])
		thread['date'] = fromTimestamp(thread['date'])
	return thread

def getComments(thread_id):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM comments WHERE thread_id=%s' % thread_id)
	comments = cursor.fetchall()
	for x in range(len(comments)):
		comments[x] = dict(comments[x])
		comments[x]['date'] = fromTimestamp(comments[x]['date'])
		author = getUser(comments[x]['owner'])
		comments[x]['author_name'] = author['name']
		comments[x]['author_avatar'] = author['avatar']
	return comments

def postComment(user, thread_id, content):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT COUNT(*)+1 FROM comments')
	identifier = cursor.fetchone()[0]
	cursor.execute('INSERT INTO comments VALUES(%s, %s, %s, "%s", %s, 0, 0, 0)' % (identifier, thread_id, user['id'], screen(content), int(time.time())))
	conn.commit()
	cursor.execute('SELECT owner FROM threads WHERE id=%s' % thread_id)
	author = cursor.fetchone()[0]
	if author != user['id']:
		sendNotification(author, 'Новый комментарий в обсуждении', 'В твоём обсуждении опубликован новый комментарий', 'success', 'message-circle', '/thread/%s' % thread_id)
	giveBadge(user['id'], 'first_comment')

def isVoiced(target, identifier, owner):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM voices WHERE target="%s" AND id=%s AND owner=%s' % (target, identifier, owner))
	if cursor.fetchone() == None:
		return False
	return True

def changeReputation(user_id, reputation):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	if reputation >= 0:
		reputation = '+%s' % reputation
	else:
		reputation = str(reputation)
	cursor.execute('UPDATE users SET rating=rating%s WHERE id=%s' % (reputation, user_id))
	conn.commit()

def voiceFor(owner, number, target, identifier):
	if isVoiced(target, identifier, owner):
		return 'voice'
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT owner FROM %ss WHERE id=%s' % (target, identifier))
	user_id = cursor.fetchone()[0]
	if user_id == owner:
		return 'self'
	cursor.execute('UPDATE %ss SET %s=%s+1 WHERE id=%s' % (target, number, number, identifier))
	conn.commit()
	changeReputation(user_id, reputationRates[target][number])
	cursor.execute('INSERT INTO voices VALUES ("%s", %s, %s)' % (target, identifier, owner))
	conn.commit()
	if number == 'up':
		giveBadge(owner, 'first_up')
	else:
		giveBadge(owner, 'first_down')
	if target == 'thread':
		return identifier
	else:
		cursor.execute('SELECT thread_id FROM comments WHERE id=%s' % identifier)
		return cursor.fetchone()[0]

def saveSettings(user_id, name, email, password, status, about, department):
	if isNull(about):
		about = 'Этот пользователь пока ничего о себе не написал...'
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('UPDATE users SET name="%s", email="%s", status="%s", description="%s", department="%s" WHERE id=%s' % (screen(name), screen(email), screen(status), screen(about), screen(department), user_id))
	conn.commit()
	if len(password) >= 8:
		cursor.execute('UPDATE users SET password="%s" WHERE id=%s' % (screen(password), user_id))
		conn.commit()

def setAvatar(user_id, number):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('UPDATE users SET avatar="%s" WHERE id=%s' % (number, user_id))
	conn.commit()

def sendNotification(owner, title, content, type, icon, href):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('INSERT INTO notifications VALUES (%s, %s, "%s", "%s", "%s", "%s", "%s")' % (owner, int(time.time()), screen(title), screen(content), screen(type), screen(icon), screen(href)))
	conn.commit()

def getNotifications(user_id):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM notifications WHERE owner=%s' % user_id)
	notifications = cursor.fetchall()
	for x in range(len(notifications)):
		notifications[x] = dict(notifications[x])
		notifications[x]['date'] = fromTimestamp(notifications[x]['date'])
	notifications.reverse()
	return notifications

def readNotifications(user_id):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('DELETE FROM notifications WHERE owner=%s' % user_id)
	conn.commit()

def giveBadge(user_id, badgeName):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT badges FROM users WHERE id=%s' % user_id)
	badges = json.loads(cursor.fetchone()[0])
	if badgeName not in badges:
		badges.append(badgeName)
		cursor.execute('UPDATE users SET badges=\'%s\' WHERE id=%s' % (json.dumps(badges), user_id))
		conn.commit()
		changeReputation(user_id, badgeTypes[badgeName][1])
		sendNotification(user_id, 'Новый значок!', 'Ты получил новый значок: %s.' % badgeTypes[badgeName][0], 'success', 'award', '/profile')
	if len(badges) == 3:
		giveBadge(user_id, 'badges_lover')

def getStats(user_id):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT COUNT(*) FROM threads WHERE owner=%s' % user_id)
	threads = cursor.fetchone()[0]
	cursor.execute('SELECT COUNT(*) FROM comments WHERE owner=%s' % user_id)
	comments = cursor.fetchone()[0]
	return (threads, comments)

def deleteContent(user, target, identifier):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT owner FROM %ss WHERE id=%s' % (screen(target), identifier))
	content = cursor.fetchone()
	if content['owner'] != user['id'] and not user['moderator']:
		return '/threads?from=no_access'
	if target == 'thread':
		cursor.execute('UPDATE threads SET status="deleted" WHERE id=%s' % identifier)
		conn.commit()
		return '/thread/%s' % identifier
	else:
		cursor.execute('UPDATE comments SET deleted=1 WHERE id=%s' % identifier)
		conn.commit()
		cursor.execute('SELECT thread_id FROM comments WHERE id=%s' % identifier)
		return '/thread/%s' % cursor.fetchone()['thread_id']

def block(user, identifier):
	if identifier != user['id'] and user['moderator']:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()
		cursor.execute('UPDATE users SET blocked=1 WHERE id=%s' % identifier)
		conn.commit()

def unblock(user, identifier):
	if identifier != user['id'] and user['moderator']:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()
		cursor.execute('UPDATE users SET blocked=0 WHERE id=%s' % identifier)
		conn.commit()

def sendEmail(toaddr, subject, html):
    fromaddr = "iproud@topstack.dev"
    mypass = "ProudAnyWhere"
    msg = MIMEMultipart()
    msg['From'] = "iProud Support <iproud@topstack.dev>"
    msg['To'] = toaddr
    msg['Subject'] = subject
    msg.attach(MIMEText(html, 'html'))
    server = smtplib.SMTP_SSL('smtp.mail.ru', 465)
    server.login(fromaddr, mypass)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

def addSurvey(thread_id, survey):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('INSERT INTO polls VALUES (%s, \'%s\')' % (thread_id, json.dumps(survey)))
	conn.commit()

def getSurvey(thread_id):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT variants FROM polls WHERE thread_id=%s' % thread_id)
	survey = cursor.fetchone()
	if survey:
		survey = json.loads(survey[0])
	return survey

def saveSurvey(thread_id, survey):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('UPDATE polls SET variants=\'%s\' WHERE thread_id=%s' % (json.dumps(survey), thread_id))
	conn.commit()

def pollFor(user_id, thread_id, variant):
	if isVoiced('poll', thread_id, user_id):
		return '/threads?from=poll'
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('INSERT INTO voices VALUES ("poll", %s, %s)' % (thread_id, user_id))
	conn.commit()
	giveBadge(user_id, 'first_poll')
	survey = getSurvey(thread_id)
	if variant in survey.keys():
		survey[variant] += 1
		saveSurvey(thread_id, survey)
	return '/thread/%s' % thread_id

def getGoods():
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM goods')
	return cursor.fetchall()

def getGood(identifier):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM goods WHERE id="%s"' % identifier)
	return cursor.fetchone()

def buyGood(user, identifier):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM goods WHERE id="%s"' % screen(identifier))
	good = cursor.fetchone()
	if good:
		if good['cost'] > user['rating']:
			return False
		else:
			cursor.execute('SELECT COUNT(*)+1 FROM orders')
			count = cursor.fetchone()
			count = count[count.keys()[0]]
			cursor.execute('INSERT INTO orders VALUES (%s, %s, %s)' % (count, user['id'], identifier))
			conn.commit()
			sendNotification(user['id'], 'Твой заказ успешно создан', 'Мы приняли твой заказ на покупку товара в магазине.', 'primary', 'shopping-cart', '/shop')
			changeReputation(user['id'], -1 * good['cost'])
			return True

def getOrders():
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM orders WHERE id > 0')
	orders = cursor.fetchall()
	for x in range(len(orders)):
		orders[x] = dict(orders[x])
		cursor.execute('SELECT name FROM users WHERE id=%s' % orders[x]['owner'])
		orders[x]['name'] = cursor.fetchone()['name']
		cursor.execute('SELECT name FROM goods WHERE id=%s' % orders[x]['good_id'])
		orders[x]['title'] = cursor.fetchone()['name']
	return orders

def acceptOrder(identifier):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM orders WHERE id="%s"' % screen(identifier))
	order = cursor.fetchone()
	cursor.execute('UPDATE orders SET id=-id WHERE id="%s"' % screen(identifier))
	conn.commit()
	sendNotification(order['owner'], 'Твой заказ успешно осуществлён', 'Спасибо за покупку!', 'success', 'shopping-cart', '/shop')

def rejectOrder(identifier):
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM orders WHERE id="%s"' % screen(identifier))
	order = cursor.fetchone()
	cursor.execute('UPDATE orders SET id=-id WHERE id="%s"' % screen(identifier))
	conn.commit()
	sendNotification(order['owner'], 'Твой заказ отклонён', 'Списанный баллы возвращены на твой баланс.', 'danger', 'shopping-cart', '/shop')
	changeReputation(order['owner'], getGood(order['good_id'])['cost'])

def getRating():
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()
	cursor.execute('SELECT name, rating, id, badges FROM users ORDER BY rating DESC LIMIT 10')
	top = cursor.fetchall()
	for x in range(len(top)):
		top[x] = dict(top[x])
		top[x]['badges_length'] = len(json.loads(top[x]['badges']))
	return top

def getThanks(identifier):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT COUNT(*) FROM voices WHERE target="thanks" AND id=%s' % identifier)
	return cursor.fetchone()[0]

def isThanked(user_id, identifier):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('SELECT * FROM voices WHERE target="thanks" AND id=%s AND owner=%s' % (identifier, user_id))
	return not (cursor.fetchone() == None)

def sayThanks(user_id, identifier):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()
	cursor.execute('INSERT INTO voices VALUES ("thanks", %s, %s)' % (identifier, user_id))
	conn.commit()
	changeReputation(identifier, 10)