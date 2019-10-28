import sys

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash

from modules.base import validate, enhance_schema_with_data
from main import module

host, port = module.address.split(':')
port = int(port)

app = Flask(__name__)
app.secret_key = 'SUPERSECRETKEY'


@app.route('/')
def dashboard():
    metrics = [
        {
            'name': 'Supply Chain',
            'type': 'nested',
            'value': [
                {
                    'name': 'Suppliers',
                    'type': 'statistic',
                    'value': len(module.get('supplier').get_suppliers()),
                },
                {
                    'name': 'Fulfillment Centers',
                    'type': 'statistic',
                    'value': len(module.get('fulfillment_center').get_fulfillment_centers()),
                },
                {
                    'name': 'Warehouses',
                    'type': 'statistic',
                    'value': len(module.get('warehouse').get_warehouses()),
                },
                {
                    'name': 'Sales Channels',
                    'type': 'statistic',
                    'value': len(module.get('sales_channel').get_sales_channels())
                }
            ],
        },
    ]

    return render_template('management/dashboard.html', metrics=metrics)


def merge(a, b):
    a = a.copy()
    a.update(b)
    return a


@app.route('/search')
def search():
    q = str(request.args.get('q', default='', type=str))
    types = {
        'sales channel': lambda q: module.get('sales_channel').search_for_sales_channels(q),
    }

    searches = {}

    if 'type:' in q:
        for key in types.keys():
            if ('type:' + key) in q:
                q = q.replace('type:' + key, '').strip()
                searches[key] = []
    else:
        searches = {key: [] for key in types.keys()}

    result = []
    for key in tuple(searches.keys()):
        result.extend((
            merge(
                object,
                {
                    'doc_type': key,
                    'href': url_for('edit_sales_channel', uuid=object['uuid'])
                },
            )
            for object
            in types[key](q)
        ))

    return render_template('management/search.html', q=q, result=result, title=repr(q))


# Sales Channels

@app.route('/sales-channels')
def sales_channels():
    objects = module.get('sales_channel').get_sales_channels()
    objects = [
        merge(object, {'href': url_for('edit_sales_channel', uuid=object['uuid'])})
        for object
        in objects
    ]
    return render_template('management/sales_channels/index.html', objects=objects)


@app.route('/sales-channels/create', methods=['GET', 'POST'])
def create_sales_channel():
    schema = module.get('sales_channel').get_sales_channel_schema('create')

    if request.method == 'POST':
        errors = validate(request.form, schema)
        if not errors:
            object = module.get('sales_channel').create_sales_channel(
                name=request.form['name'],
                type=request.form['type'],
            )
        else:
            for error in errors:
                flash(error, 'warning')
            return redirect(url_for('create_sales_channel'))
        return redirect(url_for('edit_sales_channel', uuid=object['uuid']))

    return render_template('management/sales_channels/create.html', object={}, schema=schema)


@app.route('/sales-channels/<string:uuid>', methods=['GET', 'POST'])
def edit_sales_channel(uuid):
    schema = module.get('sales_channel').get_sales_channel_schema('update')
    object, messages = module.get('sales_channel').get_sales_channel(uuid)
    schema = enhance_schema_with_data(object, schema)

    flash_many(messages)

    if object is None:
        flash('Sales Channel wasn\'t found.', 'Not Found')
        return redirect((url_for('sales_channels')))

    if request.method == 'POST':
        errors = validate(request.form, schema)
        if not errors:
            module.get('sales_channel').update_sales_channel(
                uuid,
                **{
                    'name': request.form['name'],
                }
            )
        else:
            for error in errors:
                flash(error, 'warning')
        return redirect(url_for('edit_sales_channel', uuid=uuid))

    return render_template('management/sales_channels/edit.html', object=object, title=object['name'], schema=schema)


@app.route('/sales-channels/delete/<string:uuid>', methods=['POST'])
def delete_sales_channel(uuid):
    deleted, messages = module.get('sales_channel').delete_sales_channel(uuid)
    flash_many(messages)
    if not deleted:
        return redirect(url_for('edit_sales_channel', uuid=uuid))
    return redirect(url_for('sales_channels'))


# Products

@app.route('/products')
def products():
    schema = module.get('product').get_product_schema('create')
    objects = module.get('product').get_products()
    objects = [
        merge(object, {'href': url_for('edit_product', uuid=object['uuid'])})
        for object
        in objects
    ]
    return render_template('management/products/index.html', objects=objects, schema=schema)


def flash_many(messages):
    for message in messages:
        if isinstance(message, (tuple, list)):
            flash(message[0], category=message[1])
        else:
            flash(message)


@app.route('/products/create', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        object, errors = module.get('product').create_product(request.form)
        if errors:
            flash_many(errors)
            return redirect(url_for('create_product'))
        return redirect(url_for('edit_product', uuid=object['uuid']))

    return render_template('management/products/create.html', object={}, schema=module.get('product').get_product_schema('create'))


@app.route('/products/<string:uuid>', methods=['GET', 'POST'])
def edit_product(uuid):
    schema = module.get('product').get_product_schema('update')
    object, messages = module.get('product').get_product(uuid)

    flash_many(messages)

    if object is None:
        return redirect(url_for('products'))

    schema = enhance_schema_with_data(object, schema)

    if request.method == 'POST':
        success, messages = module.get('product').update_product(
            uuid,
            {
                'name': request.form.get('name', ''),
                'type': request.form.get('type', ''),
                'brand': request.form.get('brand', ''),
            }
        )

        flash_many(messages)

        return redirect(url_for('edit_product', uuid=uuid))

    return render_template('management/products/edit.html', object=object, title=object['name'], schema=schema)


@app.route('/products/delete/<string:uuid>', methods=['POST'])
def delete_product(uuid):
    response, errors = module.get('product').delete_product(uuid)
    return redirect(url_for('products'))


# Misc.

@app.route('/supply-chain')
def supply_chain():
    return render_template('management/supply_chain/index.html')


@app.route('/_health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(
        host=host,
        port=port,
        debug=module.debug,
    )
