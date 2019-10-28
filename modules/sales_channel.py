from datetime import datetime
from uuid import uuid4

from modules.base import Module, procedure

import peewee


class SalesChannel(peewee.Model):
    ONLINE_SHOP = 'online shop'
    PHYSICAL_SHOP = 'physical shop'

    TYPES = (
        ONLINE_SHOP,
        PHYSICAL_SHOP
    )

    uuid = peewee.CharField(unique=True)
    name = peewee.CharField()
    type = peewee.CharField(constraints=[peewee.Check("type in {!r}".format(TYPES))])
    created_at = peewee.DateTimeField(default=datetime.now)
    deleted_at = peewee.DateTimeField(null=True)

    @property
    def supplier_ids(self):
        if 'supplier_ids' not in self.__dict__:
            self.__dict__.update({
                'supplier_ids': [
                    sales_channel_supplier.supplier_id
                    for sales_channel_supplier
                    in (
                        supplier.supplier_id
                        for supplier
                        in self.suppliers
                    )
                ]
            })
        return self.__dict__['supplier_ids']

    def to_dict(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'type': self.type,
            'supplier_ids': self.supplier_ids,
        }

    def delete(self):
        self.deleted_at = datetime.now()
        self.save(only=self.dirty_fields)

    @classmethod
    def get_schema(cls, mode):
        schema = dict(
            type='object',
            properties=dict(
                name=dict(
                    key='name',
                    name='Name',
                    type='string',
                    ordering=0,
                ),
                type=dict(
                    key='type',
                    name='Type',
                    type='string',
                    default=SalesChannel.ONLINE_SHOP,
                    choices=list(SalesChannel.TYPES),
                    ordering=1,
                ),
            ),
        )

        if mode != 'create':
            schema['properties']['type']['immutable'] = True
            schema['properties']['type']['optional'] = True

        return schema


class SalesChannelSupplier(peewee.Model):
    sales_channel = peewee.ForeignKeyField(SalesChannel, backref='suppliers')
    supplier_id = peewee.CharField()
    ordering = peewee.SmallIntegerField()

    class Meta:
        database = db
        indexes = (
            (('sales_channel', 'supplier_id'), True),
        )


class SalesChannelModule(Module):
    name = 'sales_channel'

    @procedure
    def create_sales_channel(self, name, type=SalesChannel.ONLINE_SHOP, suppliers=None):
        uuid = str(uuid4())
        sales_channel = SalesChannel.create(
            uuid=uuid,
            name=name,
            type=type,
        )

        for i, supplier in enumerate(suppliers or []):
            supplier_id = supplier['uuid'] if isinstance(supplier, dict) else supplier
            SalesChannelSupplier.create(
                sales_channel=sales_channel,
                supplier=supplier_id,
                ordering=i,
            )

        return sales_channel.to_dict()

    @procedure
    def get_sales_channel(self, uuid):
        try:
            sales_channel = SalesChannel.get(uuid=str(uuid)).to_dict()
        except SalesChannel.DoesNotExist as e:
            return None, [str(e)]
        return sales_channel, []

    @procedure
    def get_sales_channels(self, **kwargs):
        sales_channels = []

        _sales_channels = SalesChannel.select().where(SalesChannel.deleted_at.is_null(True))
        if kwargs:
            _sales_channels = _sales_channels.where(*(
                getattr(SalesChannel, keyword) == argument
                for keyword, argument
                in kwargs.items()
            ))

        for sales_channel in _sales_channels:
            sales_channels.append(sales_channel.to_dict())

        return sales_channels

    @procedure
    def update_sales_channel(self, uuid, name=None, type=None):
        updates = {}
        if name:
            updates['name'] = str(name).strip()
        if type:
            updates['type'] = str(type).strip()

        sales_channel = SalesChannel.get(uuid=uuid)
        for field, value in updates.items():
            setattr(sales_channel, field, value)
        sales_channel.save(only=sales_channel.dirty_fields)

    @procedure
    def delete_sales_channel(self, uuid):
        try:
            SalesChannel.get(SalesChannel.uuid == uuid).delete()
        except SalesChannel.DoesNotExist as e:
            return False, [str(e)]

        return True, [['Sales Channel was deleted.', 'success']]

    @procedure
    def find_sales_channel_which_uuid_starts_with(self, string):
        try:
            sales_channel = SalesChannel.get(SalesChannel.uuid.startswith(string)).to_dict()
        except SalesChannel.DoesNotExist:
            sales_channel = None
        return sales_channel

    @procedure
    def search_for_sales_channels(self, q):
        sales_channels = []
        if q:
            q = ' & '.join(q.split())
            sql = """
            SELECT
                *
            FROM
                "saleschannel"
            WHERE
                to_tsvector('english', "saleschannel"."name") @@ to_tsquery('english', %s)
            ORDER BY
                ts_rank(
                    to_tsvector('english', "saleschannel"."name"),
                    to_tsquery('english', %s)
                )
            """

            for sales_channel in SalesChannel.raw(sql, *[str(q) for _ in range(2)]):
                sales_channels.append(sales_channel.to_dict())
        else:
            for sales_channel in SalesChannel.select():
                sales_channels.append(sales_channel.to_dict())

        return sales_channels

    @procedure
    def get_sales_channel_schema(self, mode):
        return SalesChannel.get_schema(mode)
