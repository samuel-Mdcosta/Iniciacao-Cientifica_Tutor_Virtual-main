from flask import Flask, request
from flask_cors import CORS
from menu import Menu

chat = Menu()
app = Flask(__name__)
CORS(app)

@app.route('/input', methods=['POST'])
def add_message():
    new_message = request.get_json()
    output = chat.post_message_norag(new_message)

    return output

app.run(port=3000, host='localhost', debug=True)
    