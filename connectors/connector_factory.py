import logging
import sys

from connectors.eltex.eltex import Eltex
from connectors.juniper.juniper import Juniper


class ConnectorFactory:
    def create_connector(self, connector, ip, credentials):
        if connector == 'eltex':
            return Eltex(ip, credentials)
        elif connector == 'juniper':
            return Juniper(ip, credentials)
        else:
            logging.error(
                f"Unsupported connector '{connector}' for IP: {ip}. Check inventory file."
            )
            sys.exit()