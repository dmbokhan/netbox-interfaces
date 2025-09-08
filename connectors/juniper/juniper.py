import logging
import sys
import re
from pathlib import Path

from jnpr.junos import Device
from jnpr.junos.op.ethport import EthPortTable

from connectors.base_connector import BaseConnector


class Juniper(BaseConnector):
    """
        Juniper device connector
    """
    def get_interfaces(self) -> dict:
        device = {
            'host': str(self.ip),
            'user': self.username,
            'password': self.password,
        }
        logging.info(f"Connect to {self.ip}")
        try:
            with Device(**device) as ssh:
                hostname = ssh.facts['hostname']
                output = EthPortTable(ssh).get('*')
        except Exception as e:
            logging.error(e)
            sys.exit()
        logging.info(f"Connection to {self.ip} successfully closed.")

        result = {
            "hostname": str(hostname),
            "interfaces": output,
        }
        
        return result
    
    def get_interfaces_normalize(self, data) -> dict:
        result = {
            "hostname": data['hostname'],
            "interfaces": list()
        }

        def _define_interface_type(interface_name):
            """ Define interface_type by interface_name"""
            interface_name = interface_name.lower()
            if interface_name.startswith('irb'):
                return 'virtual'
            if interface_name.startswith('lo'):
                return 'virtual'
            if interface_name.startswith('em'):
                return '1000base-t'
            if interface_name.startswith('re'):
                return '1000base-t'
            if interface_name.startswith('ge'):
                return '1000base-t'
            if interface_name.startswith('xe'):
                return '10gbase-x-sfpp'
            if interface_name.startswith('et'):
                return '25gbase-x-sfp28'
            if interface_name.startswith('ae'):
                return 'lag'
            return 'other'

        for interface in data['interfaces']:
            interface_data = dict()
            if not interface.name.startswith(('irb', 'lo', 'em', 're', 'ge', 'xe', 'et', 'ae')):
                continue
            interface_data['name'] = interface.name
            interface_data['type'] = _define_interface_type(interface_data['name'])
            interface_data['enabled'] = True if interface.admin == 'up' else False
            if interface.description is not None:
                interface_data['description'] = interface.description
            if not interface.name.startswith(('lo',)):
                interface_data['mtu'] = interface.mtu
            result['interfaces'].append(interface_data.copy())
            del interface_data

        return result