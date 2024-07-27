from flask import Flask, jsonify
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient("mongodb+srv://regaarzula:YlDDs2OYHYOuuLPc@cluster0.nslprzn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['hydroponic_system']
inputSuhu = db['temperature_settings']
inputJam = db['clock_settings']

@app.route('/get_latest_temp_settings', methods=['GET'])
def get_temp_settings():
    # Mendapatkan pengaturan suhu terbaru dari MongoDB
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
        settings['alarm_time'] = setting.get('alarm_time')
        print(f"alarm_time: {settings['alarm_time']}")  # Debug print
    
    return jsonify(settings)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
