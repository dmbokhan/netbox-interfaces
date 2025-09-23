import logging
import sys
import re
from pathlib import Path

import netmiko

from connectors.base_connector import BaseConnector


class Eltex(BaseConnector):
    """
        Eltex device connector
    """
    def get_interfaces(self) -> dict:
        template_file = Path(__file__).resolve(strict=True).parent.joinpath('eltex_show_interfaces_description_template.textfsm')
        device = {
            'device_type': 'generic',
            'host': str(self.ip),
            'username': self.username,
            'password': self.password,
            'port': 22,
        }

        def _ansi_escape(s):
            """Remove the ANSI escape sequences from a string"""
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', s)

        logging.info(f"Connect to {self.ip}")
        try:
            with netmiko.ConnectHandler(**device) as ssh:
                hostname = _ansi_escape(ssh.find_prompt().strip()[0:-1])  # get hostname from prompt and clear unprintable characters
                ssh.send_command('terminal width 0', expect_string=r".+#$")
                ssh.send_command('terminal datadump', expect_string=r".+#$")
                ssh.send_command('set cli pagination off', expect_string=r".+#$")
                output = ssh.send_command(
                    'show interfaces description',
                    expect_string=r".+#$",
                    use_textfsm=True,
                    textfsm_template=template_file,
                )
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

        def _convert_vlan_interface_name(original_interface_name):
            """ Convert original interface vlan name, ex. '1' to 'vlan1' """
            if original_interface_name[0].isdigit():
                return f"vlan{original_interface_name}"
            return original_interface_name
            
        def _convert_interface_mode(original_port_mode):
            """ Convert original port mode, ex. 'Access (1)' to 'access' """
            if original_port_mode.startswith('Access'):
                return interface['port_mode'].split(" ")[0].lower()  # remove vlan id for access port
            if original_port_mode.startswith('Trunk'):
                return "tagged"
            return None
            
        def _define_interface_type(interface_name):
            """ Define interface_type by interface_name"""
            interface_name = interface_name.lower()
            if interface_name.startswith('vlan'):
                return 'virtual'
            if interface_name.startswith('l'):  # Loopback
                return 'virtual'
            if interface_name.startswith('g'):  # Gi
                return '1000base-t'
            if interface_name.startswith('t'):  # Te
                return '10gbase-x-sfpp'
            if interface_name.startswith('p'):  # Po
                return 'lag'
            return 'other'
        
        for interface in data['interfaces']:
            interface_data = dict()
            interface_data['name'] = _convert_vlan_interface_name(interface['interface'])
            interface_data['mode'] = _convert_interface_mode(interface['port_mode'])
            interface_data['type'] = _define_interface_type(interface_data['name'])
            interface_data['enabled'] = True if interface['protocol'].lower() == 'up' else False
            interface_data['description'] = interface['description'].strip()
            if interface_data['enabled'] == False and interface_data['description'] == '':
                ### ignore empty interfaces
                del interface_data
                continue
            result['interfaces'].append(interface_data.copy())
            del interface_data

        return result