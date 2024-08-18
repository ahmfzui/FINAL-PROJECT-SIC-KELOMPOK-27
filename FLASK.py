from flask import Flask, jsonify, request
from pymongo import MongoClient
from ubidots import ApiClient

app = Flask(__name__)

# Konfigurasi Ubidots
API_TOKEN = "BBFF-thUhhRPJojoHiUB78bozuZuPy2dKTv"
LABEL_LAMPU = "66a99dbade9a2d0ca44681c9"
LABEL_MOTOR = "66a21a1de770251891fa8abc"

api = ApiClient(token=API_TOKEN)
variable_lampu = api.get_variable(LABEL_LAMPU)
variable_motor = api.get_variable(LABEL_MOTOR)

# Konfigurasi MongoDB
client = MongoClient("mongodb+srv://regaarzula:YlDDs2OYHYOuuLPc@cluster0.nslprzn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['hydroponic_system']
inputSuhu = db['temperature_settings']
inputJam = db['clock_settings']

@app.route('/get_latest_temp_settings', methods=['GET'])
def get_temp_settings():
    latest_setting = inputSuhu.find().sort([('_id', -1)]).limit(1)
    settings = {}
    for setting in latest_setting:
        settings['min_temp'] = setting['min_temp']
        settings['max_temp'] = setting['max_temp']
    
    return jsonify(settings)

@app.route('/get_latest_clock_settings', methods=['GET'])
def get_clock_settings():
    latest_setting = inputJam.find().sort([('_id', -1)]).limit(1)
    settings = {}
    for setting in latest_setting:
        settings['alarm_time_1'] = setting.get('alarm_time_1')
        settings['alarm_time_2'] = setting.get('alarm_time_2')
        settings['alarm_time_3'] = setting.get('alarm_time_3')
        print(f"alarm_time_1: {settings['alarm_time_1']}")
        print(f"alarm_time_2: {settings['alarm_time_2']}") 
        print(f"alarm_time_3: {settings['alarm_time_3']}")   # Debug print
    
    return jsonify(settings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
