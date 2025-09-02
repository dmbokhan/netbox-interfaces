import abc


class BaseConnector:
    """ Base class for other connectors"""
    def __init__(self, ip, credentials):
        self.username = credentials['username']
        self.password = credentials['password']
        self.ip = ip

    @abc.abstractmethod
    def get_interfaces(self) -> dict:
        """ Get interfaces data from device"""
        pass

    @abc.abstractmethod
    def get_interfaces_normalize(self) -> dict:
        """ Get data from 'get_interfaces' and prepare it for Netbox"""
        pass