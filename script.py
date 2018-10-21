import os
import json
import requests
# ibm cloudant
from cloudant import Cloudant
from cloudant.adapters import Replay429Adapter

# cloudant Connection 
client = None
db_name = 'resqu'
db = None


if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    print('Found VCAP_SERVICES')
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
        print('Found local VCAP_SERVICES')
        creds = vcap['services']['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True, adapter=Replay429Adapter(retries=10, initialBackoff=0.01))
        db = client.create_database(db_name, throw_on_exists=False)


def post_precausion_fema():
	fema_precausion_url = 'https://www.ready.gov/feeds/fema-mobile-app-hazard-json-feed'
	response = requests.get(fema_precausion_url)
	for precausion in response.json().get("nodes"):
		precausion.get('node')['type'] = 'Precausions'
		doc_id = db.create_document(precausion.get("node"))

	return doc_id

def get_precausions(lang="English"):
	selector = {'language': lang,'type':'Precausions'}
	results = db.get_query_result(selector)
	for result in results:
		print(result['title'])
		break

def post_disaster_summary():
    count = 1
    with open('ema.txt','r') as f:
        stat=''
        for line in f:
            stat+=line
            if line.isspace():
                doc={'doc_'+str(count):stat}
                stat = ''
                count+=1
                doc['type'] ='ema'
                doc_id = db.create_document(doc)
    print('done')

if __name__ == '__main__':
    post_disaster_summary()
    client.disconnect()

	