import logging
import sys
import re
from pathlib import Path
from lxml import etree

from jnpr.junos import Device

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
                hostname = ssh.rpc.get_config(
                    filter_xml='<system><host-name></host-name></system>',
                    options={'format':'json'}
                )['configuration']['system']['host-name']
                output = ssh.rpc.get_interface_information({'format':'json'})

                # retrieve logical interfaces
                logical_interfaces = list()
                for interface in output['interface-information'][0]['physical-interface']:
                    if 'logical-interface' in interface:
                        for logical_interface in interface['logical-interface']:
                            logical_interfaces.append(logical_interface.copy())
        except Exception as e:
            logging.error(e)
            sys.exit()
        logging.info(f"Connection to {self.ip} successfully closed.")

        result = {
            "hostname": str(hostname),
            "physical-interfaces": output['interface-information'][0]['physical-interface'],
            "logical-interfaces": logical_interfaces
        }
        
        return result
    
    def get_interfaces_normalize(self, data) -> dict:
        result = {
            "hostname": data['hostname'],
            "interfaces": list()
        }

        def _define_interface_type(interface_name, speed=None):
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
                if speed == '1Gbps':
                    return '1000base-t'
                if speed == '10Gbps':
                    return '10gbase-x-sfpp'
                if speed == '25Gbps':
                    return '25gbase-x-sfp28'
                if speed == '100Gbps':
                    return '100gbase-x-qsfp28'
            if interface_name.startswith('ae'):
                return 'lag'
            return 'other'

        for interface in data['physical-interfaces']:
            interface_data = dict()
            if not interface['name'][0]['data'].startswith(('irb', 'lo', 'em', 're', 'ge', 'xe', 'et', 'ae')):
                continue
            interface_data['name'] = interface['name'][0]['data']
            interface_data['enabled'] = True if interface['admin-status'][0]['data'] == 'up' else False
            if 'speed' in interface:
                interface_data['type'] = _define_interface_type(interface_data['name'], speed=interface['speed'][0]['data'])
            else:
                interface_data['type'] = _define_interface_type(interface_data['name'])  # not all interfaces have speed
            if 'description' in interface:
                interface_data['description'] = interface['description'][0]['data']
            if 'mtu' in interface:
                if interface['mtu'][0]['data'].isdigit():  # mtu must contain only digits
                    interface_data['mtu'] = int(interface['mtu'][0]['data'])
            result['interfaces'].append(interface_data.copy())
            del interface_data

### for logical interfaces
#        for interface in data['logical-interfaces']:
#            interface_data = dict()
#            if not interface['name'][0]['data'].startswith(('irb', 'lo', 'ge', 'xe', 'et', 'ae')):
#                continue
#            interface_data['name'] = interface['name'][0]['data']
#            interface_data['type'] = 'virtual'
#            if 'description' in interface:
#                interface_data['description'] = interface['description'][0]['data']
#            result['interfaces'].append(interface_data.copy())
#            del interface_data

        return result