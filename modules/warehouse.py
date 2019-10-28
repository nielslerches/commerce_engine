from uuid import uuid4

from modules.base import Module, procedure

import peewee


class Warehouse(peewee.Model):
    uuid = peewee.CharField(unique=True)
    name = peewee.CharField()

    def to_dict(self):
        return dict(
            uuid=self.uuid,
            name=self.name,
        )


class WarehouseStockLine(peewee.Model):
    warehouse = peewee.ForeignKeyField(Warehouse, backref='stock_lines')
    location = peewee.CharField()
    sku = peewee.CharField()
    quantity = peewee.IntegerField()

    class Meta:
        indexes = (
            (('warehouse', 'location', 'sku'), True),
        )


class WarehouseModule(Module):
    name = 'warehouse'

    @procedure
    def create_warehouse(self, name):
        warehouse = Warehouse.create(
            uuid=str(uuid4()),
            name=name,
        )

        return warehouse.to_dict()

    @procedure
    def get_warehouse(self, uuid):
        try:
            warehouse = Warehouse.get(uuid=uuid).to_dict()
        except Warehouse.DoesNotExist:
            warehouse = None
        return warehouse

    @procedure
    def get_warehouses(self, **kwargs):
        warehouses = []

        _warehouses = Warehouse.select()
        if kwargs:
            _warehouses = _warehouses.where(*(
                getattr(Warehouse, keyword) == argument
                for keyword, argument
                in kwargs.items()
            ))

        for warehouse in _warehouses:
            warehouses.append(warehouse.to_dict())

        return warehouses

    @procedure
    def count_stock(self, warehouse_id, sku):
        count = 0

        for stock_line in Warehouse.get(uuid=warehouse_id).stock_lines.where(sku=sku):
            count += stock_line.quantity

        return count

    @procedure
    def add_stock(self, warehouse, sku, location, quantity):
        warehouse_id = warehouse['uuid'] if isinstance(warehouse, dict) else warehouse
        warehouse = Warehouse.get(uuid=warehouse_id)
        stock_lines = warehouse.stock_lines.where(sku=sku, location=location)
        if not stock_lines.exists():
            stock_line = WarehouseStockLine.create(
                warehouse=warehouse,
                location=location,
                sku=sku,
                quantity=0,
            )
        stock_line.quantity += quantity
        stock_line.save()
        return stock_line.quantity

    @procedure
    def remove_stock(self, warehouse, sku, location, quantity):
        warehouse_id = warehouse['uuid'] if isinstance(warehouse, dict) else warehouse
        warehouse = Warehouse.get(uuid=warehouse_id)
        stock_lines = warehouse.stock_lines.where(sku=sku, location=location)
        if not stock_lines.exists():
            stock_line = WarehouseStockLine.create(
                warehouse=warehouse,
                location=location,
                sku=sku,
                quantity=0,
            )
        stock_line.quantity -= quantity
        stock_line.save()
        return stock_line.quantity

    @procedure
    def set_stock(self, warehouse, sku, location, quantity):
        warehouse_id = warehouse['uuid'] if isinstance(warehouse, dict) else warehouse
        warehouse = Warehouse.get(uuid=warehouse_id)
        stock_lines = warehouse.stock_lines.where(sku=sku, location=location)
        if not stock_lines.exists():
            stock_line = WarehouseStockLine.create(
                warehouse=warehouse,
                location=location,
                sku=sku,
                quantity=0,
            )
        stock_line.quantity = quantity
        stock_line.save()
        return stock_line.quantity
