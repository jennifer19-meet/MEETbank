from flask import Flask, request, render_template, session, url_for, redirect
import random, pyrebase, string, openpyxl, xlsxwriter, os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth as auth2

########################## SETUP ######################

app = Flask(__name__,
	template_folder='templates', 
	static_folder='static'
)
app.config.from_pyfile('config.py')

firebaseConfig = os.getenv('FIREBASE_CONFIG')

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()

cred = credentials.Certificate("certs.json")
firebase_admin.initialize_app(cred)

######################### FUNCTIONS ####################

characters = string.ascii_letters + string.digits
student_groups = ['A', 'B', 'C', 'D', 'E', 'F']
lab_headers = ['Python Review', 'Front-End Review', 'MVC', 'Flask Routing', 'Advanced Flask', 'Flask Forms', 'Login Session', 'Firebase Authentication', 'Firebase Realtime Database']
milestone_headers = ['Wireframe', '3 html', 'CSS', 'JS', '3 Routes', 'Methods', 'auth', 'db', 'Dynamic routes', 'Heroku', 'API']
session_headers = ['Intro to Summer', 'Python Review', 'Front-End Review', 'MVC', 'Flask Routing', 'Advanced Flask', 'Flask Forms', 'Login Session', 'Firebase Authentication', 'Firebase Realtime Database', 'Individual Project Intro']
num_labs = len(lab_headers)
num_sessions = len(session_headers)
num_milestones = len(milestone_headers)

def random_password(length):
	''' Creates a random password of a specified length (int) '''
	return ''.join(random.choice(characters) for i in range(length))

def group_name_and_money(group):
	'''
	Given a valid group (str) (i.e. one of the ones in student_groups), 
	it returns a dict with the keys being the uids of students in that
	group and the value being the name and total money they have.
	'''

	students = {}
	if group in student_groups:
		users = db.child('Users').get().val()
		for uid in users:
			if 'group' in users[uid]:
				if users[uid]['group'] == group:
					students[uid] = {'name' : users[uid]['name'], 'money': calculate_money(uid)}
	return students

def group_info(group):
	'''
	Given a valid group (str) (i.e. one of the ones in student_groups), 
	it returns a dict with the keys being the uids of students in that
	group and the value being a dict with all the information in the
	database for each student.
	'''

	student_info = {}
	if group in student_groups:
		users = db.child('Users').get().val()
		for uid in users:
			if 'group' in users[uid]:
				if users[uid]['group'] == group:
					student_info[uid] = users[uid]
	return student_info

def group_names_uid_extra(group, key):
	'''
	Given a valid group (str) (i.e. one of the ones in student_groups)
	and a key to find the value of (str), it returns a dict with the 
	keys being the uids of students in that group and the value being 
	another dict with the name and the key specified (unless that key 
	is labs in which case it'll add the following keys: bonuses, extras, 
	advanced, help_asked, TA)
	'''

	student_info = {}
	if group in student_groups:
		users = db.child('Users').get().val()
		for uid in users:
			if 'group' in users[uid]:
				if users[uid]['group'] == group:
					if key == 'labs':
						student_info[uid] = {'name':users[uid]['name'], 'bonuses': users[uid]['bonuses'], 'extras': users[uid]['extras'], 'advanced': users[uid]['advanced'], 'help_asked': users[uid]['help_asked'], 'TA': users[uid]['TA']}
					else:
						student_info[uid] = {'name':users[uid]['name'], key: users[uid][key]}
	return student_info

def generate_empty_extra(num):
	''' Generates a list with num (int) False values (used for
	database info re-entering when a form is submitted) '''
	return [False for _ in range(num)]

def all_students_empty(group, num, keys):
	'''
	Returns a dict with the uids of students in a specified group 
	as the keys and adds another dict as a value. The inner dict 
	contains the keys specified (list) with corresponding lists 
	as values. The lists will contain num (int) many False values 
	in them.
	'''

	final = {}
	if group in student_groups:
		users = db.child('Users').get().val()
		for uid in users:
			if 'group'in users[uid]:
				if users[uid]['group'] == group:
					for key in keys:
						final[uid][key] = generate_empty_extra(num)
	return final

def calculate_money(uid):
	'''
	Returns the total amount of money (int) a given student (with 
	the specified uid (str)) has in his bank account
	'''

	total = 0
	user = db.child('Users').child(uid).get().val()
	settings = db.child('Settings').get().val()
	user_vals = [user['TA'], user['daily'], user['help_asked'], user['initial'], user['sessions'].count(True), user['individual_proj'].count(True), user['bonuses'].count(True), user['extras'].count(True), user['advanced'].count(True), user['group_proj'] ]
	settings_amounts = [settings['TA_pay'],settings['daily'], settings['help_cost'], settings['initial'], settings['participation'], settings['milestones'], settings['bonus'], settings['extras'], settings['advanced'], settings['group_winners']]
	for i in range(len(user_vals)):
		total += (user_vals[i] * settings_amounts[i])
	return total

######################### ROUTES #######################

@app.route('/', methods = ["GET", "POST"])
def main():
	'''
	If the user isn't logged in, it will send the person the login page (GET).
	If the method is POST, it'll process the login info. If it doesn't succeed,
	it'll send the user back to the login page and show an error message. Otherwise,
	it'll send the user to the homepage and display the correct information for their
	user_type. If the user goes to this route and they're already logged in, it'll 
	send them to their correct home page.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] in ['TA', 'instructor', 'student', 'admin', 'coordinator']:
			money = 0
			user = {}
			settings = {}
			if session['type'] == 'student':
				money = calculate_money(session['user']['localId'])
				user = db.child('Users').child(session['user']['localId']).get().val()
				settings = db.child('Settings').get().val()
			return render_template('home.html', groups = student_groups, user_type = session['type'], money = money, user = user, settings =settings)
		return render_template('error.html', error = "unknown session type (i.e. not 'TA', 'instructor', 'admin', 'coordinator' or 'student')", user_type = session['type'])
	error = ''
	if request.method == "POST":
		try:
			session['user'] = auth.sign_in_with_email_and_password(request.form['email'], request.form['password'])
			session['type'] = db.child('Users').child(session['user']['localId']).child('type').get().val() 
			return redirect(url_for('main'))
		except:
			error = "login failed"
	return render_template('login.html', error = error)

@app.route('/add_day', methods=['POST'])
def add_day():
	'''
	Allows the admin to add one day to all students' accounts. Accepts only 
	POST for safety issues.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] == 'admin':
			users = db.child('Users').get().val()
			for uid in users:
				if users[uid]['type'] == 'student':
					db.child('Users').child(uid).update({'daily': users[uid]['daily']+1})
			return redirect(url_for('settings'))
		return render_template('error.html', error = 'You don\'t have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))	

@app.route('/remove_day', methods=['POST'])
def remove_day():
	'''
	Allows the admin to remove one day from all students' accounts. Accepts only 
	POST for safety issues.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] == 'admin':
			users = db.child('Users').get().val()
			for uid in users:
				if users[uid]['type'] == 'student':
					db.child('Users').child(uid).update({'daily': users[uid]['daily']-1})
			return redirect(url_for('settings'))
		return render_template('error.html', error = 'You don\'t have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))	

@app.route('/rules')
def rules():
	'''
	* Sends logged in users to the rules page. If a TA, instructor,
	coordinator or admin access this page. They will see more information.
	* Sends other not logged in users to the login page
	'''

	if 'user' in session and 'type' in session:
		settings = db.child('Settings').get().val()
		extra = False
		if session['type'] in ['TA', 'instructor', 'admin', 'coordinator']:
			extra = True
		return render_template('rules.html', extra = extra, settings = settings, user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/settings', methods = ["GET", "POST"])
def settings():
	'''
	Sends you to the settings page if you're an admin and lets you update the settings
	for the prices and rewards. If you don't have admin status, it'll take you to the 
	error page. If you aren't logged in, you'll be redirected to the login page.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] == 'admin':
			if request.method == 'POST':
				settings = {'help_cost': int(request.form['help_cost']),
							'participation': int(request.form['participation']),
							'bonus': int(request.form['bonus']),
							'extras': int(request.form['extras']),
							'advanced': int(request.form['advanced']),
							'daily': int(request.form['daily']),
							'initial': int(request.form['initial']),
							'TA_pay': int(request.form['TA_pay']),
							'milestones': int(request.form['milestones']), 
							'group_winners': int(request.form['group_winners'])
							}
				db.child('Settings').update(settings)
			else:
				settings = db.child('Settings').get().val()
			return render_template('settings.html', settings = settings, user_type = session['type'])
		return render_template('error.html', error = 'You don\'t have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/add', methods = ["GET", "POST"])
def add():
	'''
	If you're an admin, it'll take you to the add page which allows 
	you to add people to the database and authenticate them from the
	info on an excel sheet. If you aren't an admin, it'll take you 
	to the error page. If you aren't logged in, it'll take you to the 
	login page.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] == 'admin':
			if request.method == "POST":
				wb = openpyxl.load_workbook(request.files['excel_sheet'])
				output_wb = xlsxwriter.Workbook('accounts.xlsx')
				output_ws = output_wb.add_worksheet()
				row_num = 0
				sheet = wb['sheet']
				failed = []
				for row in sheet.iter_rows():
					if row[5].value == None:
						break
					email = row[5].value.strip()
					password = random_password(6)
					
					row_num+=1
					if row[4].value in ["student", "admin"]:
						group = row[1].value if row[1].value != "None" else ""
						user_info = {'name': row[0].value,
									'email':email,
									'type': row[4].value, 
									'group':group, 
									'TA':0, 
									'help_asked':0, 
									'individual_proj': generate_empty_extra(num_milestones), 
									'group_proj':False,
									'bonuses': generate_empty_extra(num_labs),
									'extras': generate_empty_extra(num_labs),
									'advanced': generate_empty_extra(num_labs),
									'sessions':generate_empty_extra(num_sessions), 
									'initial':1,
									'daily': 0,
									'password' : password
									}
					elif row[4].value == 'coordinator':
						user_info = {'name': row[0].value,
									'email':email,
									'type': row[4].value, 
									'groups':row[5].value,
									'password' : password
									}
					else:
						user_info = {'name': row[0].value,
									'email':email,
									'type': row[4].value,
									'password' : password
									}
					try:
						user_id = auth.create_user_with_email_and_password(email, password)['localId']
						db.child("Users").child(user_id).set(user_info)
						output_ws.write(row_num, 0, email)
						output_ws.write(row_num, 1, password)
						output_ws.write(row_num, 2, row[0].value)
					except:
						failed.append(email)
					# auth.send_password_reset_email(email)
				output_wb.close()
				if failed:
					return failed.join('\n')
				return redirect(url_for("add"))
			return render_template("add.html", user_type = session['type'])
		return render_template('error.html', error = "You don't have access to this page. If this is a mistake, contact Jennifer", user_type = session['type']) 	
	return redirect(url_for('main'))

@app.route('/make_change')
def make_change():
	'''
	Route dedicated to making changes in the database. Only
	allows GET requests. Only the admin can access it. Change
	the commented out code to make a change.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] == 'admin':
			# users = db.child('Users').get().val()
			# for uid in users:
			# 	if users[uid]['type'] != 'student':	
			# 		db.child('Users').child(uid).child('group_proj').remove()
			# for i in range(len(store_items)):
			# 	item = {'name': store_items_names[i], 'number': store_items_numbers[i], 'pics': store_items[i], 'price': 0, 'claimed_by':[]}
			# 	db.child('Store').push(item)
			return render_template('error.html', error = "Change was completed successfully", user_type = session['type']) 	
		return render_template('error.html', error = "You don't have access to this page. If this is a mistake, contact Jennifer", user_type = session['type']) 	
	return redirect(url_for('main'))

@app.route('/session/<string:group>', methods = ["GET", "POST"])
def session_page(group):
	'''
	Allows instructors and admins to edit and view the participation 
	in all sessions for a specified group. If the user type isn't one 
	the two allowed it'll send the user to the error page. If the user 
	isn't logged in, it'll send them to the login page. It allows GET 
	and POST.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] in ['instructor', 'admin']:
			if group in student_groups:
				if request.method =='POST':
					empty_sessions = all_students_empty(group, num_sessions, ['sessions'])
					for item in request.form.getlist('sessions'):
						empty_sessions[item.split('_')[0]][int(item.split('_')[1])] = True
					for uid in empty_sessions:
						db.child('Users').child(uid).update(empty_sessions[uid])
				students = group_names_uid_extra(group, 'sessions')
				return render_template('sessions.html', students = students, group = group, headers = session_headers, user_type = session['type'])
			return render_template('error.html', error = 'This group doesn\'t exist', user_type = session['type'])
		return render_template('error.html', error = 'Only instructors have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/lab/<string:group>', methods = ["GET", "POST"])
def lab_page(group):
	'''
	Allows instructors, TAs and admins to edit and view the bonuses, extras 
	and advanced labs completed for a specified group. It also allows 
	them to edit and view the number of times the student has asked for 
	help and TAed. If the user type isn't one the two allowed it'll 
	send the user to the error page. If the user isn't logged in, it'll 
	send them to the login page. It allows GET and POST.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] in ['TA', 'instructor', 'admin']:
			if group in student_groups:
				if request.method =='POST':
					uids = [item.split('_')[0] for item in request.form.getlist('labs')]
					lab_indexes = [int(item.split('_')[1]) for item in request.form.getlist('labs')]
					part = [item.split('_')[2] for item in request.form.getlist('labs')]
					empty_sessions = all_students_empty(group, num_labs, ['bonuses', 'extras', 'advanced'])
					for i in range(len(uids)):
							empty_sessions[uids[i]][part[i]][lab_indexes[i]] = True
					for uid in empty_sessions:
						try:
							empty_sessions[uid]['help_asked'] = int(request.form[uid+'_help_asked'])
							empty_sessions[uid]['TA'] = int(request.form[uid+'_TA'])
						except:
							pass
						db.child('Users').child(uid).update(empty_sessions[uid])
				students = group_names_uid_extra(group, 'labs')
				return render_template("labs.html", students = students, group = group, headers = lab_headers, user_type = session['type'])
			return render_template('error.html', error = 'This group doesn\'t exist', user_type = session['type'])
		return render_template('error.html', error = 'Only instructors/TAs have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/individual_proj/<string:group>', methods=['POST', 'GET'])
def individual_proj(group):
	'''
	Allows instructors, TAs and admins to edit and view the individual 
	project milestones completed by the students in a specified group. 
	If the user type isn't one the two allowed it'll send the user to
	the error page. If the user isn't logged in, it'll send them to the 
	login page. It allows GET and POST.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] in ['TA', 'instructor', 'admin']:
			if group in student_groups:
				if request.method =='POST':
					uids = [item.split('_')[0] for item in request.form.getlist('individual_proj')]
					indexes = [int(item.split('_')[1]) for item in request.form.getlist('individual_proj')]
					empty_sessions = all_students_empty(group, num_milestones, ['individual_proj'])
					for i in range(len(uids)):
						empty_sessions[uids[i]][indexes[i]] = True
					for uid in empty_sessions:
						db.child('Users').child(uid).update(empty_sessions[uid])
				students = group_names_uid_extra(group, 'individual_proj')
				return render_template('individual_proj.html', students = students, group = group, headers = milestone_headers, user_type = session['type'])
			return render_template('error.html', error = 'This group doesn\'t exist', user_type = session['type'])
		return render_template('error.html', error = 'Only instructors/TAs have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/group_proj/<string:group>', methods=['POST', 'GET'])
def group_proj(group):
	'''
	Allows instructors, TAs and admins to edit and view the winners of 
	the group project in a specified group. If the user type isn't one 
	the two allowed it'll send the user to the error page. If the user 
	isn't logged in, it'll send them to the login page. It allows GET 
	and POST.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] in ['TA', 'instructor', 'admin']:
			if group in student_groups:
				students = group_names_uid_extra(group, 'group_proj')
				if request.method =='POST':
					uids = request.form.getlist('group_proj')
					for uid in students:
						if uid in uids:
							db.child('Users').child(uid).update({'group_proj':True})
						else:
							db.child('Users').child(uid).update({'group_proj':False})
				return render_template('group_proj.html', students = students, group = group, user_type = session['type'])
			return render_template('error.html', error = 'This group doesn\'t exist!', user_type = session['type'])
		return render_template('error.html', error = 'Only instructors/TAs have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/shop', methods=['GET', 'POST'])
def shop():
	'''
	Allows logged in users to view the store page with all the
	products. If the user isn't logged in, it sends them to the
	login page. Allows both GET and POST.
	'''

	if 'user' in session and 'type' in session:
		stuff = db.child('Store').get().val()
		return render_template('shop.html', stuff = stuff, user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/logout')
def logout():
	'''
	Logs out users. Route only allows GET requests and then sends them 
	to the login page
	'''

	try:
		del session['user']
	except:
		pass
	try:
		del session['type']
	except:
		pass
	auth.current_user = None
	return redirect(url_for("main"))

@app.route('/reset_all_passwords', methods = ['POST'])
def reset_all_passwords():
	'''
	Only admin access; Sends a reset password email to all users in the 'Users'
	database. Only POST is allowed on this route. Can be reached from add.html
	'''

	if 'user' in session and 'type' in session:
		if session['type'] == 'admin':
			users = db.child('Users').get().val()
			for uid in users:
				auth.send_password_reset_email(users[uid]['email'])
			return redirect(url_for('add'))
		return render_template('error.html', error = 'You don\'t have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/delete_all_users', methods = ['POST'])
def delete_all_users():
	'''
	Deletes all users except for the admin. Can only be accessed through POST
	for safety.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] == 'admin':
			for user in auth2.list_users().iterate_all():
				if user.uid != "b43QiQ9Pw9ewAZu1u0MeDKy2vWF3":
					try:
						auth2.delete_user(user.uid)
					except:
						pass
					try:
						db.child('Users').child(str(user.uid)).remove()
					except:
						pass
			return redirect(url_for('add'))
		return render_template('error.html', error = 'You don\'t have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/student_tiers', methods=['POST'])
def tiers():
	'''
	If the admin accesses this page, all the student's total money
	will be calculated and put into an excel sheet saved under the
	name money_collected.xlsx so you can sort it by money column 
	and see how much money everyone has (used to set prices). Can 
	only be accessed through POST.
	'''

	if 'user' in session and 'type' in session:
		if session['type'] == 'admin':
			output_wb = xlsxwriter.Workbook('money_collected.xlsx')
			output_ws = output_wb.add_worksheet()
			users = db.child('Users').get().val()
			row = 0
			for uid in users:
				if users[uid]['type'] == 'student':
					output_ws.write(row, 0, users[uid]['name'])
					output_ws.write(row, 1, calculate_money(uid))
					row += 1
			output_wb.close()
			return redirect(url_for('settings'))
		return render_template('error.html', error = 'You don\'t have access to this page!', user_type = session['type'])
	return redirect(url_for('main'))

@app.route('/<path:other_path>', methods=['GET', 'POST'])
def catch_all(other_path):
	'''
	catches all other routes and sends them to an error page instead of 
	breaking the website
	'''
	
	if 'user' in session and 'type' in session:
		return render_template('error.html', error = "This route doesn't exist", user_type = session['type'])
	return redirect(url_for('main'))

if __name__ == "__main__":
	app.run(debug=True)