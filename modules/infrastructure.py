from modules.base import Module, procedure

import docker


class InfrastructureModule(Module):
    name = 'infrastructure'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.from_env()

    def __post_init__(self, module_name):
        if module_name == self.name:
            for container in self.client.containers.list(
                filters=dict(
                    label='sales_channel_id',
                ),
            ):
                container.stop()
                container.remove()

    @procedure
    def spin_up_online_shop(self, sales_channel_id):
        images = self.client.images.list(
            filters=dict(label='name=commerce_engine_online_shop'),
        )

        if images:
            image = images[0]
        else:
            image, _ = self.client.images.build(
                path='/mnt',
                dockerfile='Dockerfile',
                labels=dict(name='commerce_engine_online_shop'),
            )

        containers = self.client.containers.list(
            filters=dict(
                label='sales_channel_id=' + str(sales_channel_id),
            )
        )

        if containers:
            for container in containers:
                container.stop()
                container.remove()

        infrastructure_host, infrastructure_port = self.address.split(':')
        infrastructure_port = int(infrastructure_port)

        port = 1 + infrastructure_port + len(self.client.containers.list())

        self.client.containers.run(
            image=image.attrs['Id'],
            command=['python3', 'online_shop.py'],
            environment={
                'DEBUG': 'true' if self.debug else 'false',
                'MASTER_MODULE_NAME': 'commerce_engine',
                'MODULE_NAME': 'online_shop',
                'COMMERCE_ENGINE_MODULE_ADDRESS': 'commerce_engine:5000',
                'WAREHOUSE_MODULE_ADDRESS': 'warehouse:5000',
                'FULFILLMENT_CENTER_MODULE_ADDRESS': 'fulfillment_center:5000',
                'SUPPLIER_MODULE_ADDRESS': 'supplier:5000',
                'SALES_CHANNEL_MODULE_ADDRESS': 'sales_channel:5000',
                'CART_MODULE_ADDRESS': 'cart:5000',
                'CUSTOMER_MODULE_ADDRESS': 'customer:5000',
                'PRODUCT_MODULE_ADDRESS': 'product:5000',
                'MANAGEMENT_MODULE_ADDRESS': 'management:5000',
                'INFRASTRUCTURE_MODULE_ADDRESS': 'infrastructure:' + str(infrastructure_port),
                'ONLINE_SHOP_MODULE_ADDRESS': '0.0.0.0:' + str(port),
                'SALES_CHANNEL_ID': str(sales_channel_id),
            },
            ports={
                str(port) + '/tcp': port,
            },
            network='commerce_engine_default',
            working_dir='/mnt',
            detach=True,
            labels=dict(
                sales_channel_id=str(sales_channel_id),
            ),
        )
