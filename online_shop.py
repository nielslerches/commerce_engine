import os
from distutils.util import strtobool

from flask import Flask, jsonify, session

from main import module

host, port = module.address.split(':')
port = int(port)
app = Flask(__name__)
app.secret_key = 'SUPERSECRETKEY'


@app.before_request
def get_or_create_customer():
    customer = module.get('customer').get_customer(session.get('customer_id'))
    if customer is None:
        customer = module.get('customer').create_customer()
    if session.get('customer_id') != customer['uuid']:
        session['customer_id'] = customer['uuid']


@app.route('/')
def index():
    return jsonify(module.describe())


@app.route('/api/cart')
def api_cart():
    return jsonify(module.describe_customers_cart(session['customer_id']))


@app.route('/_health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(
        host=host,
        port=port,
        debug=module.debug,
    )
