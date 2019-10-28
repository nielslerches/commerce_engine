from uuid import uuid4

from modules.base import Module, procedure

import peewee


class Customer(peewee.Model):
    uuid = peewee.CharField(unique=True)

    def to_dict(self):
        return {
            'uuid': self.uuid,
        }


class CustomerModule(Module):
    name = 'customer'

    @procedure
    def create_customer(self):
        customer = Customer(uuid=str(uuid4()))
        customer.save()
        return customer.to_dict()

    @procedure
    def get_customer(self, uuid):
        try:
            customer = Customer.get(Customer.uuid == str(uuid))
        except Customer.DoesNotExist:
            customer = None
        return customer.to_dict() if isinstance(customer, Customer) else None
