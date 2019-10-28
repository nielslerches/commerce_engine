from uuid import uuid4

from modules.base import Module, procedure

import peewee


class Supplier(peewee.Model):
    uuid = peewee.CharField(unique=True)
    name = peewee.CharField()

    @property
    def fulfillment_center_ids(self):
        if 'fulfillment_center_ids' not in self.__dict__:
            self.__dict__.update({
                'fulfillment_center_ids': [
                    fulfillment_center.fulfillment_center_id
                    for fulfillment_center
                    in self.fulfillment_centers
                ]
            })
        return self.__dict__['fulfillment_center_ids']

    def to_dict(self):
        return dict(
            uuid=self.uuid,
            name=self.name,
            fulfillment_center_ids=self.fulfillment_center_ids,
        )


class SupplierFulfillmentCenter(peewee.Model):
    supplier = peewee.ForeignKeyField(Supplier, backref='fulfillment_centers')
    fulfillment_center_id = peewee.CharField()
    ordering = peewee.SmallIntegerField()

    class Meta:
        indexes = (
            (('supplier', 'fulfillment_center_id'), True),
        )


class SupplierSKU(peewee.Model):
    uuid = peewee.CharField(unique=True)
    supplier = peewee.ForeignKeyField(Supplier, backref='skus')
    sku = peewee.CharField()

    class Meta:
        indexes = (
            (('supplier', 'sku'), True),
        )


class SupplierFulfillmentCenterSKU(peewee.Model):
    supplier_sku = peewee.ForeignKeyField(SupplierSKU, backref='fulfillment_center_skus')
    fulfillment_center_id = peewee.CharField()
    sku = peewee.CharField()

    class Meta:
        indexes = (
            (('supplier_sku', 'fulfillment_center_id'), True),
        )


class SupplierModule(Module):
    name = 'supplier'

    @procedure
    def create_supplier(self, name, fulfillment_center_ids=None):
        supplier = Supplier.create(
            uuid=str(uuid4()),
            name=name,
        )

        for i, fulfillment_center in enumerate(fulfillment_center_ids or []):
            fulfillment_center_id = fulfillment_center['uuid'] if isinstance(fulfillment_center, dict) else fulfillment_center
            SupplierFulfillmentCenter.create(
                supplier=supplier,
                fulfillment_center_id=fulfillment_center_id,
                ordering=i,
            )

        return supplier.to_dict()

    @procedure
    def get_supplier(self, uuid):
        try:
            supplier = Supplier.get(uuid=uuid).to_dict()
        except Supplier.DoesNotExist:
            supplier = None
        return supplier

    @procedure
    def get_suppliers(self, **kwargs):
        suppliers = []

        _suppliers = Supplier.select()
        if kwargs:
            _suppliers = _suppliers.where(*(
                getattr(Supplier, keyword) == argument
                for keyword, argument
                in kwargs.items()
            ))

        for supplier in _suppliers:
            suppliers.append(supplier.to_dict())

        return suppliers
