import atexit
import os
import json
import requests
import geocoder
from config import API
from passlib.hash import pbkdf2_sha256
from flask import (
	Flask, render_template, request, session, flash, url_for, redirect, make_response
	)
# twilio for sending msg alert
from twilio.rest import Client
# ibm cloudant
from cloudant import Cloudant
from cloudant.adapters import Replay429Adapter

# algolia search api
from algoliasearch import algoliasearch



# algolia app connection
client = algoliasearch.Client(API().app_id, API().admin_api_key)
index = client.init_index('ema')


# Flask app connection
app = Flask(__name__)
app.secret_key = 'ResQU'
app.config['SESSION_TYPE'] = 'filesystem'


# cloudant Connection 
client = None
db_name = 'resqu'
db = None


if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    if 'cloudantNoSQLDB' in vcap:
        creds = vcap['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True,adapter=Replay429Adapter(retries=10, initialBackoff=0.01))
        db = client.create_database(db_name, throw_on_exists=False)
elif "CLOUDANT_URL" in os.environ:
    client = Cloudant(os.environ['CLOUDANT_USERNAME'], os.environ['CLOUDANT_PASSWORD'], url=os.environ['CLOUDANT_URL'], connect=True, adapter=Replay429Adapter(retries=10, initialBackoff=0.01))
    db = client.create_database(db_name, throw_on_exists=False)
elif os.path.isfile('vcap-local.json'):
    with open('vcap-local.json') as f:
        vcap = json.load(f)
        creds = vcap['services']['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True, adapter=Replay429Adapter(retries=10, initialBackoff=0.01))
        db = client.create_database(db_name, throw_on_exists=False)

# On IBM Cloud Cloud Foundry, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8000
port = int(os.getenv('PORT', 8000))



@app.route('/')
@app.route('/api/v1/')
def home():
	return render_template('index.html')


@app.route('/api/v1/dashboard', methods=["GET","POST"])
def dashboard(result=None):
	results =[]
	if 'result' in dict(request.args):
		results = dict(request.args)['result']
	precausions = get_precausions()
	return render_template('dashboard.html', precausions = precausions, result=results)


@app.route('/api/v1/login', methods=["GET","POST"])
def login():
	if request.method == 'POST':
		selector = { 'username': { '$exists': True, '$in': [ str(request.form['username']) ]},'type':'Users'}
		unique_user = db.get_query_result(selector)
		go = False
		for check in unique_user:
			if check:
				go = True
			break
		if go:
			for user in unique_user:
				password = user.get('password')
				username = user.get('username')
				break
			if not pbkdf2_sha256.verify(request.form.get('password'), password):
				err = 'Password or Username is incorrect.'
				return render_template('login.html', error=err)
			else:
				session['username'] = username
				session['logged_in'] = True
				return redirect(url_for('dashboard'))
		else:
			err = 'Users not exists try again!'
			return render_template('login.html', error=err)
	return render_template('login.html')


@app.route('/api/v1/signup', methods=["GET","POST"])
def signup():
	err = request.args.get('error',)
	if request.method == 'POST':
		selector = { 'username': { '$exists': True, '$in': [ str(request.form['username']) ]},'type':'Users'}
		unique_user = db.get_query_result(selector)
		go = False
		for check in unique_user:
			if check:
				go = True
			break
		if not go:
			if request.form['password'] == request.form['password2']:
				user = {}
				for key,val in request.form.items():
					if 'password' == key:
						user['password'] = pbkdf2_sha256.hash(val)
					elif 'password2'== key:
						pass
					else:
						user[key] = val

				session['username'] = str(request.form['username'])
				session['logged_in'] = False
				try:
					user['type'] = 'Users'
					doc_id = db.create_document(user)
				except Exception as e:
					err = 'IBM Cloudant DB issue.'
					return render_template('signup.html', error=err)    

				return redirect(url_for('home'))
			else:
				err = 'Passwords do not match.'
				return render_template('signup.html', error=err)
		else:
			err = 'Users not exists try again!'
			return render_template('signup.html', error=err)
	return render_template('signup.html')


@app.route('/api/v1/search', methods=['GET','POST'])
def algolia_search():
	result =[]
	sol ={}
	phrase = str(request.form.get('search'))
	try:
		res = index.search(phrase)
		for hits in res.get('hits'):
			for k,v in hits.items():
				if k not in sol:
					sol[k]=v

		for k,v in sol.items():
			if 'doc_' in k:
				result.append(v)
	except:
		pass
	return redirect(url_for('dashboard', result=result))


@app.route('/api/v1/logout')
def logout():
    session.pop('username', None)
    session.pop('logged_in', None)
    return render_template('index.html', msg='Succesfully logout!')

@app.route('/api/v1/sos', methods=['GET','POST'])
def sos():
	if request.method == 'POST':
		disaster = request.form.get('disaster','Disaster')
		msg = ''
		selector = { 'username': { '$exists': True, '$in': [ str(session['username']) ]},'type':'Users'}
		unique_user = db.get_query_result(selector)
		full_name, contact = '', ''
		for user in unique_user:
			full_name = user.get('last_name') + ', '+ user.get('first_name')
			username = user.get('username')
			contact = user.get('contact')
			break
		msg += 'Disaster SOS Alerts\n {} has been stuck in {}.\n Help Urgently Needed!!\n Contact Info: {}\n '.format(full_name, disaster, contact)
		latlng = get_latlng()
		if latlng:
			address = get_location(latlng)
			if address:
				for k,v in address.items():
					msg += '{}: {}\n '.format(k,v)
		msg += 'Please Send Help Soon!'
		if send_alert(msg):
			return render_template('index.html', msg='Succesfully SOS Help Request Sent!')
	return render_template('index.html', error='SOS Request Unable to Sent!') 

def get_precausions(lang="English"):
	precausions = []
	selector = {'language': lang,'type':'Precausions'}
	results = db.get_query_result(selector)
	for result in results:
		feature = {}
		feature['title'] = result['title']
		feature['body'] = result['body'].replace('\\','')
		feature['label'] = result['title'].split(' ')[0]
		feature['hazard_type'] = result['hazard_type']
		precausions.append(feature)
	return precausions

def get_location(latlng):
	geolocation_api = 'https://maps.googleapis.com/maps/api/geocode/json?latlng={}&key={}'.format(latlng, API().API_KEY)
	response = requests.get(geolocation_api)
	if response.json().get('results'):
		return {
			'Address': response.json().get('results')[0].get('formatted_address'),
			'Location': response.json().get('results')[0]['geometry']['location'],
			'Location_type': response.json().get('results')[0].get('location_type')
			}
	return {}

def get_latlng():
	g = geocoder.ip('me')
	print(g.latlng)
	return ''.join(list(map(str, g.latlng)))

def send_alert(body):
	client = Client(API().account_sid, API().auth_token)
	try:
		message = client.messages.create(
		                              from_= API().from_,
		                              body=body,
		                              to= API().to
		                          )

		return message.sid
	except:
		return False


def update_all_objects():
	ema= []
	selector = {'type':'ema'}
	results = db.get_query_result(selector)
	for result in results:
		ema.append(result)
	res = index.add_objects(ema)
	return True


@atexit.register
def shutdown():
    if client:
        client.disconnect()



if __name__ == '__main__':
	# Make sure to update
	update_all_objects()
	app.run(host='0.0.0.0',port=port,debug=True)