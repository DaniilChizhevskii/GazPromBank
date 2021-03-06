from flask import Flask, request, redirect, render_template, session
from validate_email import validate_email
from app.functions import *
from app.settings import *
import sys
import os

app = Flask(__name__)
app.static_folder = static
app.template_folder = templates
app.secret_key = secret_key
app.debug = debug

@app.before_request
def checkAuth():
	if request.path in ['/', '/login', '/register', '/forgot']:
		if 'id' in session.keys():
			if getUser(session['id'])['blocked']:
				del session['id']
				return redirect('/login')
			return redirect('/threads')
	else:
		if 'id' not in session.keys() and not (request.path.startswith('/reset') or request.path.startswith('/static')):
			print(request.path)
			return redirect('/login')

@app.route('/')
def toLogin():
	return redirect('/login')

@app.route('/login', methods=['GET'])
def loginPage():
	return render_template('login.html')

@app.route('/login', methods=['POST'])
def loginProcess():
	user = isAutorized(request.form.get('email'), request.form.get('password'))
	if user:
		if user['blocked']:
			return render_template('login.html', error='blocked')
		session['id'] = user['id']
		return redirect('/threads')
	else:
		return render_template('login.html', error='incorrect')

@app.route('/register', methods=['GET'])
def registerPage():
	return render_template('register.html', closed=closed)

@app.route('/register', methods=['POST'])
def registerProcess():
	invite = request.form.get('invite')
	name = request.form.get('name')
	email = request.form.get('email').lower()
	password = request.form.get('password')
	if isNull(invite) or isNull(name) or isNull(email) or isNull(password):
		return render_template('register.html', error='null', closed=closed)
	if not validate_email(email):
		return render_template('register.html', error='email', closed=closed)
	if len(password) < 8:
		return render_template('register.html', error='password', closed=closed)
	if closed and not validateInvite(invite):
		return render_template('register.html', error='invite', closed=closed)
	registerUser(name, email, password)
	return render_template('login.html', error='correct')

@app.route('/forgot', methods=['GET'])
def forgotPage():
	return render_template('forgot.html')

@app.route('/forgot', methods=['POST'])
def forgotСheck():
	email = request.form.get('email').lower()
	if sendReset(email):
		return render_template('forgot.html', success=True)
	else:
		return render_template('forgot.html', success=False)

@app.route('/reset/<link>', methods=['GET'])
def forgotCheck(link):
	identifier = forgotRestore(link)
	if identifier:
		session['id'] = identifier
		return redirect('/threads')
	else:
		return redirect('/login')

@app.route('/logout', methods=['GET'])
def logout():
	if 'id' in session.keys():
		del session['id']
	return redirect('/login')

@app.route('/threads')
def listOfThreads():
	department = request.args.get('department')
	theme = request.args.get('theme')
	if department not in departments and  theme not in themes:
		return render_template('threads.html', user=getUser(session['id']), threads=getThreads(), message=request.args.get('from'), departments=departments, themes=themes)
	elif department in departments:
		return render_template('threads_by_department.html', user=getUser(session['id']), threads=getThreadsByDepartment(department), departments=departments, themes=themes, selected_department=department)
	else:
		return render_template('threads_by_theme.html', user=getUser(session['id']), threads=getThreadsByTheme(theme), departments=departments, themes=themes, selected_theme=theme)

@app.route('/threads/new', methods=['GET'])
def newThreadPage():
	return render_template('new_thread.html', user=getUser(session['id']), departments=departments, themes=themes)

@app.route('/threads/new', methods=['POST'])
def newThreadProcess():
	user = getUser(session['id'])
	title = request.form.get('title')
	content = request.form.get('content')
	department = request.form.get('department')
	theme = request.form.get('theme')
	if isNull(title):
		return render_template('new_thread.html', user=user, title=title, content=content, error='Поле <b>Название обсуждения</b> является обязательным.')
	identifier = createThread(user['id'], title, content, department, theme)
	if request.form.get('survey') == 'on':
		survey = {}
		for x in range(1, int(request.form.get('quantity')) + 1):
			survey[request.form.get('variant_%s' % x)] = 0
		addSurvey(identifier, survey)
	return redirect('/thread/%s' % identifier)

@app.route('/threads/<page>')
def listOfThreadsByPage(page):
	page = int(page)
	if page <= 1:
		return redirect('/threads')
	return render_template('threads_page.html', user=getUser(session['id']), threads=getThreads(offset=page), message=request.args.get('from'), page=page)

@app.route('/thread/<identifier>')
def showThread(identifier):
	user = getUser(session['id'])
	thread = getThread(identifier)
	if thread:
		author = getUser(thread['owner'])
		survey = getSurvey(identifier)
		voiced = isVoiced('poll', identifier, user['id'])
		if thread['status'] == 'deleted':
			if user['id'] == thread['owner'] or user['moderator']:
				return render_template('thread.html', thread=thread, user=user, author=author, comments=getComments(identifier), message='deleted', survey=survey, voiced=voiced)
			return redirect('/threads?from=no_access')
		return render_template('thread.html', thread=thread, user=user, author=author, comments=getComments(identifier), message=request.args.get('from'), survey=survey, voiced=voiced)
	return redirect('/threads?from=not_found')

@app.route('/comment/<thread_id>', methods=['POST'])
def postCommentProcess(thread_id):
	content = request.form.get('content')
	if isNull(content):
		return redirect('/thread/%s?from=null' % thread_id)
	user = getUser(session['id'])
	postComment(user, thread_id, content)
	return redirect('/thread/%s?from=success' % thread_id)

@app.route('/voice/<number>/<target>/<identifier>', methods=['GET'])
def voiceProcess(number, target, identifier):
	user = getUser(session['id'])
	thread_id = voiceFor(user['id'], number, target, identifier)
	if not isNull(thread_id) and (isinstance(thread_id, int) or thread_id.isdigit()):
		return redirect('/thread/%s' % thread_id)
	else:
		return redirect('/threads?from=%s' % thread_id)

@app.route('/poll/<identifier>', methods=['POST'])
def pollProcess(identifier):
	variant = request.form.get('variant')
	return redirect(pollFor(session['id'], identifier, variant))

@app.route('/profile')
def redirectToProfile():
	return redirect('/profile/%s' % session['id'])

@app.route('/profile/<identifier>')
def showProfile(identifier):
	user = getUser(session['id'])
	profile = getUser(identifier)
	for x in range(len(profile['badges'])):
		profile['badges'][x] = badgeTypes[profile['badges'][x]][0]
	if profile:
		return render_template('profile.html', profile=profile, user=user, threads=getThreadsByUser(identifier), stats=getStats(identifier), thanks=getThanks(identifier), thanked=isThanked(user['id'], identifier), result=request.args.get('thanked'))
	else:
		return redirect('/threads?from=profile')

@app.route('/thanks/<identifier>')
def sayThanksProcess(identifier):
	user = getUser(session['id'])
	if not isThanked(user['id'], identifier):
		sayThanks(user['id'], identifier)
		return redirect('/profile/%s?thanked=true' % identifier)
	return redirect('/profile/%s?thanked=false' % identifier)

@app.route('/settings', methods=['GET'])
def showSettings():
	user = getUser(session['id'])
	return render_template('settings.html', user=user, departments=departments, domain=domain)

@app.route('/settings', methods=['POST'])
def saveSettingsProcess():
	user = getUser(session['id'])
	name = request.form.get('name')
	email = request.form.get('email')
	password = request.form.get('password')
	status = request.form.get('status')
	about = request.form.get('about')
	department = request.form.get('department')
	unit = request.form.get('unit')
	if isNull(name) or isNull(email) or isNull(status):
		return render_template('settings.html', error='null', user=user)
	if not validate_email(email):
		return render_template('settings.html', error='email', user=user)
	if not isNull(password) and len(password) < 8:
		return render_template('settings.html', error='password', user=user)
	saveSettings(user['id'], name, email, password, status, about, department, unit)
	user = getUser(session['id'])
	giveBadge(user['id'], 'autobiography')
	return render_template('settings.html', error='success', user=user, departments=departments, domain=domain)

@app.route('/settings/avatar/<number>')
def setAvatarProcess(number):
	setAvatar(session['id'], int(number))
	return redirect('/profile')

@app.route('/notifications/read', methods=['POST'])
def readNotificationsProcess():
	readNotifications(session['id'])
	return 'ok'

@app.route('/delete/<target>/<identifier>')
def deleteContentProcess(target, identifier):
	user = getUser(session['id'])
	return redirect(deleteContent(user, target, identifier))

@app.route('/block/<identifier>')
def blockProcess(identifier):
	user = getUser(session['id'])
	block(user, identifier)
	return redirect('/profile/%s' % identifier)

@app.route('/unblock/<identifier>')
def unblockProcess(identifier):
	user = getUser(session['id'])
	unblock(user, identifier)
	return redirect('/profile/%s' % identifier)

@app.route('/invite')
def viewInvites():
	user = getUser(session['id'])
	if not user['moderator']:
		redirect('/threads?from=not_found')
	return render_template('invites.html', user=user, invites=getInvites(), success=request.args.get('success'))

@app.route('/invite/new', methods=['POST'])
def generateInvitesProcess():
	user = getUser(session['id'])
	if not user['moderator']:
		redirect('/threads?from=not_found')
	number = int(request.form.get('number'))
	for x in range(number):
		generateInvite(session['id'])
	return redirect('/invite?success=true')

@app.route('/shop')
def showShop():
	if isNull(request.args.get('success')):
		success = None
	elif request.args.get('success') == 'true':
		success = True
	else:
		success = False
	return render_template('shop.html', user=getUser(session['id']), goods=getGoods(), success=success)

@app.route('/shop/<identifier>')
def showGood(identifier):
	good = getGood(identifier)
	if good:
		return render_template('good.html', user=getUser(session['id']), good=good)
	return redirect('/threads?from=not_found')

@app.route('/shop/accept/<identifier>')
def acceptOrderProcess(identifier):
	user = getUser(session['id'])
	if not user['moderator']:
		redirect('/threads?from=not_found')
	acceptOrder(identifier)
	return render_template('orders.html', user=user, orders=getOrders(), success=True)

@app.route('/shop/reject/<identifier>')
def rejectOrderProcess(identifier):
	user = getUser(session['id'])
	if not user['moderator']:
		redirect('/threads?from=not_found')
	rejectOrder(identifier)
	return render_template('orders.html', user=user, orders=getOrders(), success=True)

@app.route('/buy/<identifier>')
def buyGoodProcess(identifier):
	user = getUser(session['id'])
	result = buyGood(user, identifier)
	if result:
		return redirect('/shop?success=true')
	else:
		return redirect('/shop?success=false')

@app.route('/orders')
def viewOrders():
	user = getUser(session['id'])
	if not user['moderator']:
		redirect('/threads?from=not_found')
	return render_template('orders.html', user=user, orders=getOrders(), success=request.args.get('success'))

@app.route('/help')
def showHelp():
	return render_template('help.html', user=getUser(session['id']))

@app.route('/rating')
def showRating():
	return render_template('rating.html', user=getUser(session['id']), top=getRating())

@app.errorhandler(404)
def toThreads(error):
	return redirect('/threads?from=dont_know')