from uuid import uuid4

from modules.base import Module, procedure

import peewee


class FulfillmentCenter(peewee.Model):
    uuid = peewee.CharField(unique=True)
    name = peewee.CharField()
    warehouse_id = peewee.CharField(unique=True)

    def to_dict(self):
        return dict(
            uuid=self.uuid,
            name=self.name,
            warehouse_id=self.warehouse_id,
        )


class FulfillmentCenterModule(Module):
    name = 'fulfillment_center'

    @procedure
    def create_fulfillment_center(self, name, warehouse):
        fulfillment_center = FulfillmentCenter.create(
            uuid=str(uuid4()),
            name=name,
            warehouse_id=warehouse['uuid'] if isinstance(warehouse, dict) else warehouse
        )

        return fulfillment_center.to_dict()

    @procedure
    def get_fulfillment_center(self, uuid):
        try:
            fulfillment_center = FulfillmentCenter.get(uuid=uuid).to_dict()
        except FulfillmentCenter.DoesNotExist:
            fulfillment_center = None
        return fulfillment_center

    @procedure
    def get_fulfillment_centers(self, **kwargs):
        fulfillment_centers = []

        _fulfillment_centers = FulfillmentCenter.select()
        if kwargs:
            _fulfillment_centers = _fulfillment_centers.where(*(
                getattr(FulfillmentCenter, keyword) == argument
                for keyword, argument
                in kwargs.items()
            ))

        for fulfillment_center in _fulfillment_centers:
            fulfillment_centers.append(fulfillment_center.to_dict())

        return fulfillment_centers
