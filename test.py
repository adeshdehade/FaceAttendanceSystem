from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Flask Working"

app.run(debug=True)