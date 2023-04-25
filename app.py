import secrets
import mysql.connector
import json
from datetime import datetime, timedelta
from flask import Flask, make_response, request, jsonify
import jwt
from flask_cors import CORS
from pythainlp.util import thai_strftime

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'mysecretkey'


def connect_to_database():
    global mydb
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="user1_db"
    )
    global mycursor
    mycursor = mydb.cursor()


def get_daily_usage(table_name, date):
    mycursor.execute("SELECT L_total, kWh_total FROM `{}` WHERE date = %s".format(
        table_name), (date.strftime('%Y-%m-%d'),))
    data = mycursor.fetchall()
    if data:
        L_total, kWh_total = data[0]
    else:
        L_total, kWh_total = 0, 0
    return L_total, kWh_total


def get_all_tables():
    mycursor.execute("SHOW TABLES")
    tables = mycursor.fetchall()
    table_list = []
    for table in tables:
        table_list.append(table[0])
    return table_list


@app.route('/')
def index():
    response = make_response("Hello World!")
    return response


@app.route('/updatetotal', methods=['POST'])
def updatetotal():
    table = request.form['table']
    l_total = request.form.get('L_total', None)
    kWh_total = request.form.get('kWh_total', None)

    if l_total is None and kWh_total is None:
        return jsonify({'error': 'L_total or kWh_total is required'}), 400

    if l_total is not None and kWh_total is not None:
        return jsonify({'error': 'Only L_total or kWh_total is allowed'}), 400

    if l_total is not None:
        mycursor.execute("UPDATE `{}` SET L_total = %s WHERE id = 1".format(
            table), (l_total,))
    else:
        mycursor.execute("UPDATE `{}` SET kWh_total = %s WHERE id = 1".format(
            table), (kWh_total,))
    mydb.commit()

    return jsonify({'message': 'Data updated successfully'}), 200


@app.route('/synctotal', methods=['GET'])
def synctotal():
    table = request.args.get('table', None)
    l_total = request.args.get('L_total', False)
    kWh_total = request.args.get('kWh_total', False)

    if not table:
        return jsonify({'error': 'Table is required'}), 400

    mycursor.execute(
        "SELECT id, L_total, kWh_total, date FROM {} WHERE date = (SELECT MAX(date) FROM {}) ORDER BY id DESC LIMIT 1".format(table, table))
    data = mycursor.fetchone()

    if not data:
        return jsonify({'error': 'Data not found'}), 404

    response = {}
    if l_total and data[1]:
        response['L_total'] = data[1]
    if kWh_total and data[2]:
        response['kWh_total'] = data[2]

    mycursor.nextset()  # reset cursor after fetching results

    return jsonify(response), 200


@app.route('/generatemeter', methods=['POST'])
def generatemeter():
    table_name = request.form.get('table_name', None)

    if not table_name:
        return jsonify({'error': 'Table name is required'}), 400

    try:
        mycursor.execute(
            "CREATE TABLE {} (id INT AUTO_INCREMENT PRIMARY KEY, date DATE DEFAULT CURDATE(), L_total FLOAT, kWh_total FLOAT)".format(table_name))
    except mysql.connector.errors.ProgrammingError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': 'Table created successfully'}), 200


@app.route('/deletemeter', methods=['DELETE'])
def deletemeter():
    table_name = request.form.get('table_name', None)

    if not table_name:
        return jsonify({'error': 'Table name is required'}), 400

    try:
        mycursor.execute("DROP TABLE {}".format(table_name))
    except mysql.connector.errors.ProgrammingError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': 'Table deleted successfully'}), 200


@app.route('/listallmeter', methods=['GET'])
def listallmeter():
    connect_to_database()
    mycursor.execute("SHOW TABLES")
    tables = mycursor.fetchall()
    table_list = []
    for table in tables:
        table_list.append(table[0])
    return jsonify({'tables': table_list}), 200


@app.route('/calculator', methods=['POST'])
def calculator():
    # get the parameters from the request body
    start_date_str = request.form['start_date']
    end_date_str = request.form.get('end_date', None)
    electricity_price = float(request.form['electricity_price'])
    water_price = float(request.form['water_price'])

    # convert the date strings to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(
        end_date_str, '%Y-%m-%d') if end_date_str else None

    # calculate the electricity and water usage and costs for each day
    response = {}
    for table_name in get_all_tables():
        L_total_start, kWh_total_start = get_daily_usage(table_name, start_date)
        L_total_end, kWh_total_end = get_daily_usage(table_name, end_date)

        if L_total_start is not None and kWh_total_start is not None and L_total_end is not None and kWh_total_end is not None:
            electricity_cost = (kWh_total_end - kWh_total_start) * electricity_price
            water_cost = (L_total_end - L_total_start) * water_price
            total_cost = electricity_cost + water_cost

            response[table_name] = {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'L_total': L_total_end - L_total_start,
                'kWh_total': kWh_total_end - kWh_total_start,
                'electricity_cost': electricity_cost,
                'water_cost': water_cost,
                'total_cost': total_cost
            }

    # return the response as JSON
    return jsonify(response)


if __name__ == '__main__':
    connect_to_database()
    app.run(port=5000)