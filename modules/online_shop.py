from modules.base import Module, procedure


class OnlineShopModule(Module):
    name = 'online_shop'

    def __init__(self, *args, **kwargs):
        self.sales_channel_id = kwargs.pop('sales_channel_id')
        super().__init__(*args, **kwargs)

    @procedure
    def describe(self):
        return self.get('sales_channel').get_sales_channel(self.sales_channel_id)

    @procedure
    def describe_customers_cart(self, customer_id):
        cart_items = self.get('cart').get_customers_cart_items(
            sales_channel_id=self.sales_channel_id,
            customer_id=customer_id,
        )
        return {
            'items': cart_items,
            'customer_id': customer_id,
        }
