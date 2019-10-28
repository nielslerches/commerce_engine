import os

from distutils.util import strtobool

# Database

from peewee import PostgresqlDatabase, Model

# Modules

from modules.commerce_engine import CommerceEngine
from modules.warehouse import WarehouseModule
from modules.fulfillment_center import FulfillmentCenterModule
from modules.supplier import SupplierModule
from modules.sales_channel import SalesChannelModule
from modules.customer import CustomerModule
from modules.cart import CartModule
from modules.product import ProductModule

from modules.management import ManagementModule
from modules.infrastructure import InfrastructureModule

from modules.online_shop import OnlineShopModule

db = PostgresqlDatabase(
    'postgres',
    user='postgres',
    password='postgres',
    host='postgres',
    port=5432,
)

debug = bool(strtobool(os.getenv('DEBUG', 'false')))
master_module_name = os.getenv('MASTER_MODULE_NAME')
module_name = os.getenv('MODULE_NAME')
is_current_module = lambda module_cls: module_cls.name == module_name  # noqa: #E731

modules = {}
module_classes = [
    CommerceEngine,
    WarehouseModule,
    FulfillmentCenterModule,
    SupplierModule,
    SalesChannelModule,
    CustomerModule,
    CartModule,
    ProductModule,
]

if module_name in ('infrastructure', 'management'):
    module_classes.append(InfrastructureModule)
    if module_name == 'management':
        module_classes.append(ManagementModule)
elif module_name == 'online_shop':
    module_classes.append(OnlineShopModule)

for module_cls in module_classes:
    address = os.getenv(module_cls.name.upper() + '_MODULE_ADDRESS', '')
    if module_cls.name in (module_name, master_module_name):
        module = module_cls(
            debug=debug,
            remote=module_cls.name != module_name,
            is_master_module=module_cls.name == master_module_name,
            address=address,
            **{
                'parent_module': modules[master_module_name] if module_cls.name != master_module_name else None,
                'sales_channel_id': os.getenv('SALES_CHANNEL_ID') if module_cls.name == 'online_shop' else None,
            }
        )
        modules[module.name] = module
    else:
        module = modules[master_module_name].install(
            module_cls,
            remote=bool(address),
            address=address,
            debug=debug,
        )
        modules[module.name] = module
    if hasattr(module, '__post_init__'):
        module.__post_init__(module_name)

module = modules[module_name]

if __name__ == '__main__':
    db.connect()
    for cls in Model.__subclasses__():
        cls.bind(db)
    db.create_tables(Model.__subclasses__())
    module.start()
