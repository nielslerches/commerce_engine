import sys

from copy import copy

from uuid import uuid4
from datetime import datetime

from modules.base import Module, procedure, validate, enhance_schema_with_data

import peewee


def make_attribute_value_resolver(
    attribute_name,
    attribute_multiple_default=False,
):
    def resolve(value):
        attribute, _ = Attribute.get_or_create(name=attribute_name, defaults={'multiple': False})
        attribute_value, _ = AttributeValue.get_or_create(name=value, attribute=attribute)
        return attribute_value
    return resolve


NAME = 'Name'
TYPE = 'Type'
BRAND = 'Brand'

RESOLVERS = {
    NAME: lambda value: value,
    TYPE: make_attribute_value_resolver('Type'),
    BRAND: make_attribute_value_resolver('Brand'),
}


class Attribute(peewee.Model):
    name = peewee.CharField(unique=True)
    multiple = peewee.BooleanField(default=False)

    def __str__(self):
        return self.name


class AttributeValue(peewee.Model):
    attribute = peewee.ForeignKeyField(Attribute, backref='values')
    name = peewee.CharField()

    class Meta:
        indexes = (
            (('attribute', 'name'), True),
        )

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<' + repr(self.attribute) + ': ' + str(self) + '>'


class Product(peewee.Model):
    uuid = peewee.CharField(unique=True)
    name = peewee.CharField()
    created_at = peewee.DateTimeField(default=datetime.now)
    deleted_at = peewee.DateTimeField(null=True)
    type = peewee.ForeignKeyField(AttributeValue, backref='as_products_type')
    brand = peewee.ForeignKeyField(AttributeValue, backref='as_products_brand')

    def __str__(self):
        return self.name

    @classmethod
    def get_schema(cls, mode):
        schema = dict(
            mode=mode,
            type='object',
            properties=dict(
                name=dict(
                    key='name',
                    name=NAME,
                    type='string',
                    ordering=0,
                    resolver=NAME,
                ),
                type=dict(
                    key='type',
                    name=TYPE,
                    type='string',
                    choices=[
                        attribute_value.name
                        for attribute_value
                        in AttributeValue
                        .select()
                        .join(Attribute)
                        .where(Attribute.name == 'Type')
                        .order_by(Attribute.name)
                    ],
                    can_create_choices=True,
                    ordering=1,
                    resolver=TYPE,
                ),
                brand=dict(
                    key='brand',
                    name=BRAND,
                    type='string',
                    choices=[
                        attribute_value.name
                        for attribute_value
                        in AttributeValue
                        .select()
                        .join(Attribute)
                        .where(Attribute.name == 'Brand')
                        .order_by(Attribute.name)
                    ],
                    can_create_choices=True,
                    ordering=2,
                    resolver=BRAND,
                ),
            ),
            required=['name', 'type', 'brand'],
        )

        return schema

    @classmethod
    def get_processors(cls, dto, schema):
        processors = []

        if schema['mode'] == 'create':
            processors.append(lambda object: setattr(object, 'uuid', str(uuid4())))

        for required in schema.get('required', []):
            subschema = schema['properties'][required]

            def make_processor(required, subschema):
                resolve = RESOLVERS.get(subschema.get('resolver'), lambda value: value)

                def processor(obj):
                    result = resolve(dto.get(required))
                    setattr(obj, required, result)

                return processor

            processors.append(make_processor(required, subschema))

        return processors

    def to_dict(self):
        return dict(
            uuid=self.uuid,
            name=self.name,
            type=self.type.name,
            brand=self.brand.name,
        )

    def delete(self):
        self.deleted_at = datetime.now()
        self.save(only=self.dirty_fields)


class ProductAttributeValue(peewee.Model):
    product = peewee.ForeignKeyField(Product, backref='attribute_values')
    attribute_value = peewee.ForeignKeyField(AttributeValue, backref='products')

    class Meta:
        indexes = (
            (('product', 'attribute_value'), True),
        )


class Article(peewee.Model):
    uuid = peewee.CharField(unique=True)
    name = peewee.CharField()
    product = peewee.ForeignKeyField(Product, backref='articles')
    recommended_retail_price = peewee.DecimalField(
        max_digits=9,
        decimal_places=2,
    )


class ArticleAttributeValue(peewee.Model):
    article = peewee.ForeignKeyField(Article, backref='attribute_values')
    attribute_value = peewee.ForeignKeyField(AttributeValue, backref='articles')

    class Meta:
        indexes = (
            (('article', 'attribute_value'), True),
        )


class ArticleSupplierSKU(peewee.Model):
    article = peewee.ForeignKeyField(Article, backref='supplier_skus')
    supplier_sku_id = peewee.CharField()

    class Meta:
        indexes = (
            (('article', 'supplier_sku_id'), True),
        )


class ArticleSupplierSKUPricing(peewee.Model):
    article_supplier_sku = peewee.ForeignKeyField(ArticleSupplierSKU, backref='pricings')
    sales_channel_id = peewee.CharField()
    price = peewee.DecimalField(
        max_digits=9,
        decimal_places=2,
    )

    class Meta:
        indexes = (
            (('article_supplier_sku', 'sales_channel_id'), True),
        )


class ProductModule(Module):
    name = 'product'

    @procedure
    def get_products(self, **kwargs):
        products, _products = [], Product.select().where(Product.deleted_at.is_null(True))

        if kwargs:
            _products = _products.where(*(
                getattr(Product, keyword) == argument
                for keyword, argument
                in kwargs.items()
            ))

        for product in _products:
            products.append(product.to_dict())

        return products

    @procedure
    def create_product(self, dto):
        schema = Product.get_schema('create')
        errors = validate(dto, schema)

        if errors:
            return None, errors

        brand_attribute, _ = Attribute.get_or_create(name='Brand', defaults={'multiple': False})
        type_attribute, _ = Attribute.get_or_create(name='Type', defaults={'multiple': False})

        brand_attribute_value, _ = AttributeValue.get_or_create(name=dto['brand'], attribute=brand_attribute)
        type_attribute_value, _ = AttributeValue.get_or_create(name=dto['type'], attribute=type_attribute)

        product = Product.create(
            uuid=str(uuid4()),
            name=dto['name'],
            brand=brand_attribute_value,
            type=type_attribute_value,
        )

        return product.to_dict(), errors

    @procedure
    def get_product(self, uuid):
        try:
            return Product.get(uuid=uuid).to_dict(), []
        except Product.DoesNotExist as e:
            return None, [str(e)]

    @procedure
    def update_product(self, uuid, dto):
        product = Product.get(uuid=uuid)
        schema = Product.get_schema('update')
        schema = enhance_schema_with_data(product.to_dict(), schema)
        errors = validate(dto, schema)

        if errors:
            return False, errors

        processors = Product.get_processors(dto, schema)
        for process in processors:
            process(product)

        product.save()

        return True, []

    @procedure
    def delete_product(self, uuid):
        product = Product.get(uuid=uuid)
        product.delete()

    @procedure
    def get_product_schema(self, mode):
        return Product.get_schema(mode)
