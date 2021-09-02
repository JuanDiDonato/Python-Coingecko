#Python3 Module
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
import bcrypt
from pycoingecko import CoinGeckoAPI
import operator


app = Flask(__name__)
cg = CoinGeckoAPI()

#JWT config
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_SECRET_KEY"] = "m1ch0"
#MySQL config
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'API-Coin'

mysql = MySQL(app)
jwt = JWTManager(app)

#Funciones
def llave(obj): 
    return obj['user_price']

#Routes

#New Users
@app.route('/register', methods=['POST'])
def register():
    name = request.json['name']
    surname = request.json['surname']
    username = request.json['username']
    password = request.json['password']
    coin = request.json['coin']
    if username == '' or password == '' or name == '' or surname == '' or coin == '':
        return jsonify({'ERROR' : 'Por favor complete todos los campos.'})
    else:
        cur = mysql.connection.cursor()
        user = cur.execute('SELECT * FROM Usuarios WHERE username = %s',(username,))
        if user:
            return jsonify({'ERROR': 'Este nombre de usuario ya esta registrado.'})
        else: 
            password = password.encode() 
            sal = bcrypt.gensalt()  # cantidad de encriptaciones (12)
                # encripta la contraseña a encriptar las 12 veces
            password_s = bcrypt.hashpw(password, sal)
            cur.execute('INSERT INTO Usuarios (name, surname, username, password, coin) VALUES (%s, %s, %s, %s, %s)', (name, surname, username, password_s, coin))
            mysql.connection.commit()
            return jsonify({'EXITO':'Se registro correctamente.'})
                
#Login
@app.route('/login', methods=['POST'])
def login():
    status = cg.ping()
    if status:
        username = request.json['username']
        password = request.json['password']
        password = password.encode()
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM Usuarios WHERE username = %s',(username,))
        data = cur.fetchall()
        if data:
            datas = data[0]
            coin = datas[5]
            password_f = datas[4]
            id = datas[0]
            user = datas[3]
            password_f = password_f.encode()
            if bcrypt.checkpw(password, password_f):
                access_token = create_access_token(identity=[user,id,coin])
                return jsonify({'token': access_token})
            else:
                return jsonify({'ERROR':'Contraseña incorrecta.'})
        else:
            return jsonify({'ERROR':'Usuario no encontrado.'})
    else:
        return jsonify({'Error': 'Server Coingecko not found :('})

#All coins
@app.route('/coins', methods=['GET'])
@jwt_required()
def get_coins():
    info = get_jwt_identity()
    coin = str(info[2])
    #Get all data coin
    coin_prices = cg.get_coins_markets(vs_currency = coin)

    #Creo un diccionario vacio, donde pondre los datos que necesito de cada moneda. 
    lista = {}

    #Se crea un diccionario para los datos de cada moneda.
    for i in coin_prices:
        lista[i['name']] = {'name' : i['id'],
                            'image': i['image'], 
                            'symbol': i['symbol'], 
                            'current_price': i['current_price'], 
                            'last_updated': i['last_updated']}
    return jsonify(lista)
        
#Add coin
@app.route('/add_coin', methods=['POST'])
@jwt_required()
def add_coins():
    info = get_jwt_identity()
    id_user = info[1]
    cripto_fav = request.json['cripto_fav']
    cur = mysql.connection.cursor()

    fav_coin = cur.execute('SELECT * FROM Criptos WHERE cripto = %s' ,(cripto_fav,))
    if not fav_coin:
        cur.execute('INSERT INTO Criptos (cripto) VALUES (%s)', (cripto_fav,))  

    cur.execute('SELECT id_cripto FROM Criptos WHERE cripto = %s' ,(cripto_fav,))
    id_cripto_tuple = cur.fetchall()
    id_cripto_value = id_cripto_tuple[0][0]
    print(id_cripto_value)
    cripto_user = cur.execute('SELECT * FROM Crip_Fav WHERE id_cripto = %s and Id_user = %s' ,(id_cripto_value,id_user)) 
    if cripto_user:
        mysql.connection.commit()
        return jsonify({'ERROR' : 'Esta criptomoneda ya se encuentra agregada.'})
    else:
        cur.execute('INSERT INTO Crip_Fav (Id_user, id_cripto) VALUES (%s, %s)', (id_user, id_cripto_value))
        mysql.connection.commit()
        return jsonify({"EXITO" : "Cripto agregada a favoritos!" })

#Delete cripto
@app.route('/add_coin/<cripto>', methods=['DELETE'])
@jwt_required()
def delete_id_coin(cripto):
    info = get_jwt_identity()
    id_user = str(info[1])
    cur = mysql.connection.cursor()
    if_cripto = cur.execute('SELECT * FROM Criptos WHERE cripto = %s ', (cripto,))
    id_cripto_tuple = cur.fetchall()
    id_cripto_value = id_cripto_tuple[0][0]
    if if_cripto:
        cur.execute('DELETE FROM Crip_Fav WHERE Crip_Fav.id_cripto = %s and Id_user = %s', (id_cripto_value, id_user))
        mysql.connection.commit()
        return jsonify({'EXITO':'Criptomoneda removida correctamente'})
    else:
        mysql.connection.commit()
        return jsonify({"ERR0R":"Esta criptomoneda no se encuantra agregada!"})

#Get top 10
@app.route('/top', methods=['GET'])
@jwt_required()
def get_top():
    rev = request.json['rev']
    info = get_jwt_identity()
    id_user = str(info[1])
    coin_type = str(info[2])
    cur = mysql.connection.cursor()
    if_fav = cur.execute('SELECT id_cripto FROM Crip_Fav WHERE  Id_user = %s  AND id_cripto IS NOT NULL', (id_user))
    user_coins_tuple = cur.fetchall()
    if not if_fav:
        return jsonify({'ERROR' : 'No tiene criptomonedas en favoritos!'})
    else:
        id_list = []
        for id in user_coins_tuple:
            cur.execute('SELECT cripto FROM Criptos WHERE id_cripto = %s ', (str(id[0]),))
            name_coins_tuple = cur.fetchall()
            name_coins_value = name_coins_tuple[0][0]
            id_list.append(name_coins_value)

        list_coin = []    
        dic_coin = {}
        for i in id_list:
            coin_prices = cg.get_coin_by_id(id = i, localization= False, tickers= False, community_data=False, developer_data=False, sparkline=False)
            dic_coin = {
                'name': coin_prices['id'],
                'symbol': coin_prices['symbol'],
                'usd_price': coin_prices['market_data']['current_price']['usd'],
                'eur_price': coin_prices['market_data']['current_price']['eur'],
                'user_price': coin_prices['market_data']['current_price'][coin_type],
                'last_update': coin_prices['market_data']['last_updated']
            }
            list_coin.append(dic_coin)
        if rev == False:
            list_coin.sort(key=llave)
        else:
            list_coin.sort(key=llave, reverse=True)
    return jsonify(list_coin)
        



if __name__ == '__main__':
    app.run(debug=True)