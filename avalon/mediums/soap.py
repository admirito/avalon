from . import BaseMedia


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

    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        _import_third_party_libs()

        self.method_name = options["method_name"]
        self.location = options["location"]
        self.timeout = options.get("timeout", 10)
        self.enable_cache = options.get("enable_cache", True)

        self._suds_client = suds.client.Client(
            url=options["wsdl_url"],
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
