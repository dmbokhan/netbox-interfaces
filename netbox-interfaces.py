import logging
import sys
import argparse
from pathlib import Path
import csv
from ipaddress import ip_address, IPv4Address, IPv6Address
from getpass import getpass

from connectors.connector_factory import ConnectorFactory
from connectors.netbox import NB

import json


def file_type(source):
    """Argparse file type validation"""
    if not Path(source).is_file():
        logging.error("Inventory file doesn't exist")
        sys.exit()
    else:
        return Path(source)

def read_csv(inventory) -> list[dict[IPv4Address | IPv6Address, str]]:
    """ Read CSV file and return list of dicts"""
    result = list()
    with open(inventory) as f:
        reader = csv.DictReader(f)
        for row in reader:
            result.append(
                {
                    'ip': ip_address(row['ip']),
                    'connector': str(row['connector']).lower().strip()
                }
            )
    return result

def main():
    inventory = read_csv(args.inventory)
    credentials = {'username': input('login: '), 'password': getpass('password: ')}
    connector_factory = ConnectorFactory()
    netbox = NB()
    netbox_normalized = list()

    for device in inventory:
        connector = connector_factory.create_connector(
            device['connector'], device['ip'], credentials
        )
        interfaces = connector.get_interfaces()
        interfaces_normalized = connector.get_interfaces_normalize(interfaces)
        interfaces_normalized = netbox.not_update_identic_interface_fields(interfaces_normalized)
        netbox_normalized.append(interfaces_normalized)
    netbox_normalized = netbox.not_update_identic_devices(netbox_normalized)

    print(f"Actions: {json.dumps(netbox.show_diff(netbox_normalized), indent=4)}")
    ask_netbox_add = input('Add interfaces to Netbox? Y/N: ')
    if ask_netbox_add.lower() == 'y':
        netbox.add_interfaces(netbox_normalized)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format="{asctime}.{msecs} {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        prog='Netbox-Interfaces',
        description='''
            Netbox-Interfaces - Connect to devices from inventory-file and push their interfaces into NetBox
        ''',
        epilog='Example: python netbox-interfaces.py'
    )
    parser.add_argument(
        '-i', '--inventory',
        type=file_type, help='Inventory-file path, ex. /path/local/file.csv',
        default=Path(__file__).resolve(strict=True).parent.joinpath('inventory.csv')
    )
    parser.add_argument(
        '-l', '--logging',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='WARNING'
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(args.logging)

    sys.exit(main())