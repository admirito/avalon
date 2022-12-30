import html

from . import BaseMedia
from ..registry import RequiredValue


def _import_third_party_libs():
    global requests, suds

    import requests
    import suds.client


class SOAPMedia(BaseMedia):
    """
    SOAP (Simple Object Access Protocol) Media (RFC 4227) based on
    suds library.

    The SOAP method should accept a string for each batch.

    Initialize keyword options:
     - `wsdl_url`: (required) the URL for WSDL
     - `method_name`: (required) the name of the method
     - `location`: (required) the SOAP endpoint URL
     - `timeout`: connection timeout
     - `enable_cache`: if True (the default), the SOAP envelope will
       be generated once and consecutive calls will reuse it.
    """

    __title__ = "soap"

    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        _import_third_party_libs()

        self._suds_client = suds.client.Client(
            url=self.wsdl_url,
            location=self.location)

        self._suds_method = getattr(self._suds_client.service,
                                    self.method_name)

        # Create a SOAP envelope template so we can call requests.post
        # instead of calling suds directory when cahce is enabled for
        # better performance.
        clientclass = self._suds_method.clientclass({})
        client = clientclass(self._suds_method.client,
                             self._suds_method.method)
        binding = client.method.binding.input
        template = "AVALON-SOAP-CACHE-TEMPLATE"
        soapenv = binding.get_message(client.method,
                                      (template,), {})
        soapenv = soapenv.str().replace("{", "{{").replace("}", "}}")
        soapenv = soapenv.replace(template, "{}")
        self._soapenv_template = soapenv

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        group.add_argument(
            "--soap-wsdl-url", metavar="<url>",
            default=RequiredValue("--soap-wsdl-url"),
            help="Use WSDL at <url>.")
        group.add_argument(
            "--soap-location", metavar="<url>",
            default=RequiredValue("--soap-location"),
            help="Send SOAP requests to <url>.")
        group.add_argument(
            "--soap-method-name", metavar="<name>",
            default=RequiredValue("--soap-method-name"),
            help="Use <name> as the name of the SOAP method to call.")
        group.add_argument(
            "--soap-timeout", metavar="<n>", default=10, type=int,
            help="For soap media, use <n> as the timeout value.")
        group.add_argument(
            "--soap-disable-cache", action="store_false",
            dest="soap_enable_cache",
            help="Disable envelope caching.")

    def _write(self, batch: str):
        soapenv = self._soapenv_template.format(html.escape(batch))

        if self.enable_cache:
            resp = requests.post(
                self.location, timeout=self.timeout,
                data=soapenv.encode("utf8"),
                headers={"Content-Type": "text/xml; charset=utf-8",
                         "Soapaction": f"urn:{self.method_name}"})
            resp.raise_for_status()
        else:
            self._suds_method(soapenv)
