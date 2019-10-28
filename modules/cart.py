from modules.base import Module, procedure

import peewee


class CartItem(peewee.Model):
    sales_channel_id = peewee.CharField()
    customer_id = peewee.CharField()
    article_id = peewee.CharField()
    quantity = peewee.SmallIntegerField()

    class Meta:
        indexes = (
            (('sales_channel_id', 'customer_id', 'article_id'), True),
        )

    def to_dict(self):
        return {
            'sales_channel_id': self.sales_channel_id,
            'customer_id': self.customer_id,
            'article_id': self.article_id,
            'quantity': self.quantity,
        }


class CartModule(Module):
    name = 'cart'

    @procedure
    def add_item_to_cart(self, sales_channel_id, customer_id, article_id, quantity=1):
        cart_item, created = CartItem.get_or_create(
            sales_channel_id=sales_channel_id,
            customer_id=customer_id,
            article_id=article_id,
            defaults={'quantity': quantity},
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save(only=cart_item.dirty_fields)

        return cart_item.quantity

    @procedure
    def remove_item_from_cart(self, sales_channel_id, customer_id, article_id, quantity=1):
        cart_item, created = CartItem.get_or_create(
            sales_channel_id=sales_channel_id,
            customer_id=customer_id,
            article_id=article_id,
            defaults={'quantity': quantity},
        )

        if not created:
            cart_item.quantity = max(cart_item.quantity - quantity, 0)
            cart_item.save(only=cart_item.dirty_fields)

        return cart_item.quantity

    @procedure
    def set_cart_item_quantity(self, sales_channel_id, customer_id, article_id, quantity):
        cart_item, created = CartItem.get_or_create(
            sales_channel_id=sales_channel_id,
            customer_id=customer_id,
            article_id=article_id,
            defaults={'quantity': quantity},
        )

        if not created:
            cart_item.quantity = max(quantity, 0)
            cart_item.save(only=cart_item.dirty_fields)

        return cart_item.quantity

    @procedure
    def get_customers_cart_items(self, sales_channel_id, customer_id):
        customers_cart_items = []

        for cart_item in CartItem.select().where(
            sales_channel_id=sales_channel_id,
            customer_id=customer_id,
        ):
            customers_cart_items.append(cart_item.to_dict())
