import re
import sys

from functools import wraps
from importlib import import_module
from urllib.parse import parse_qsl

import requests
from flask import Flask, request, jsonify


def validate(data, schema, name=''):
    if not name:
        name = 'data'

    errors, type = [], schema['type']
    choices = schema.get('choices', [])

    if schema.get('optional', False) and not data:
        return errors

    if choices and not schema.get('can_create_choices', True) and data not in choices:
        errors.append('{!r} must be one of the following: {!r}'.format(name, choices))

    if type == 'object':
        for key, subschema in schema.get('properties', {}).items():
            errors.extend(validate(data.get(key), subschema, subschema.get('name', key)))
    elif type == 'string':
        sys.stdout.flush()
        if not schema.get('optional', False) and not data:
            errors.append('{!r} must be something'.format(name))

    return errors


def enhance_schema_with_data(data, schema):
    schema = schema.copy()
    type = schema['type']

    if type == 'object':
        schema['properties'] = schema.get('properties', {}).copy()
        for key, subschema in list(schema['properties'].items()):
            if data and key in data:
                schema['properties'][key] = enhance_schema_with_data(data[key], subschema)
    elif type == 'string':
        if data:
            schema['default'] = data

    return schema


def parse_dicts_as_lists(obj):
    if isinstance(obj, dict):
        if obj and all(key.isdigit() for key in obj.keys()) and min(obj.keys()) == '0' and max(obj.keys()) == str(len(obj) - 1):
            obj = [
                parse_dicts_as_lists(value)
                for key, value
                in sorted(obj.items())
            ]
        else:
            obj = {
                key: parse_dicts_as_lists(value)
                for key, value
                in obj.items()
            }
    elif isinstance(obj, list):
        obj = [
            parse_dicts_as_lists(value)
            for value
            in obj
        ]
    return obj


def parse_advanced_qs(qs):
    root = dict(parse_qsl(qs))
    for key in list(root.keys()):
        value = root.pop(key)
        path = list(token for token in re.split(r'\[|\]\[|\]', key) if token)
        current = root
        for token in path[:-1]:
            if token not in current:
                current[token] = {}
            current = current[token]
        current[path[-1]] = value
    return parse_dicts_as_lists(root)


def procedure(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if self.remote:
            response = requests.post(
                'http://' + self.address,
                json={
                    'method_name': method.__name__,
                    'args': list(args),
                    'kwargs': dict(kwargs),
                },
            )
            response = response.json()
            if 'raise' in response:
                raised = response['raise']
                exception_module = import_module(raised['module'])
                exception_class = getattr(exception_module, raised['name'])
                exception = exception_class(*raised['args'])
                raise exception
            return response['return']
        return method(self, *args, **kwargs)
    return wrapper


class Module:
    parent_module = None
    name = ''
    remote = False
    address = '127.0.0.1:5000'
    modules = {}
    is_master_module = False
    debug = False

    def __init__(self, **kwargs):
        self.parent_module = kwargs.get('parent_module', self.parent_module)
        self.name = kwargs.get('name', self.name)
        self.remote = kwargs.get('remote', self.remote)
        self.address = kwargs.get('address', self.address)
        self.modules = kwargs.get('modules', self.modules.copy())
        self.is_master_module = kwargs.get('is_master_module', self.is_master_module)
        self.debug = kwargs.get('debug', self.debug)

    def install(self, module, **kwargs):
        if isinstance(module, type):
            module = module(parent_module=self, **kwargs)
        self.modules[module.name] = module
        return module

    def get(self, module_name):
        module = self.modules.get(module_name, self.parent_module.get(module_name) if self.parent_module is not None else None)
        if module is None:
            raise NotImplementedError('module {!r} not found. Did you remember to install it?'.format(module_name))
        return module

    def get_description(self):
        description = {
            'name': self.name,
            'remote': self.remote,
            'address': self.address,
            'modules': {
                name: module.get_description()
                for name, module
                in self.modules.items()
            },
        }

        return description

    def get_nested_module(self, path):
        path = path.strip('/')
        path = path.split('/')
        path = [token for token in path if token]
        module = self
        for token in path:
            module = module.get(token)
        return module

    def route(self, path='/'):
        try:
            module = self.get_nested_module(path)
            if request.method == 'GET':
                return jsonify(module.get_description())
            body = request.json
            return jsonify({'return': getattr(self, body['method_name'])(*body['args'], **body['kwargs'])})
        except Exception as exception:
            return jsonify({
                'raise': {
                    'module': type(exception).__module__,
                    'name': type(exception).__name__,
                    'args': list(exception.args),
                },
            }), 500

    def start(self):
        host, port = self.address.split(':')
        flask = Flask(__name__)
        flask.route('/', methods=['GET', 'POST'])(self.route)
        flask.route(
            '/<path:path>',
            methods=['GET', 'POST']
        )(self.route)
        flask.run(host=host, port=int(port), debug=self.debug)

    def __repr__(self):
        return '<' + self.__class__.__name__ + ' ' + repr(self.name) + '>'
