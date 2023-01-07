from . import BaseGenericExtension


class GeneralModelsArgumentsExtension(BaseGenericExtension):
    __title__ = "models"

    def post_add_args(self, parser):
        group = parser.add_argument_group(
            title=self.__title__,
            description="Arguments for all 'log' models")

        group.add_argument(
            "--model-ip-stddev", metavar="<n>", type=int, default=100,
            help="Set default standard deviation for all models when choosing \
            a random IP address from a normal distribution to <n>.")
        group.add_argument(
            "--model-port-stddev", metavar="<n>", type=int, default=2,
            help="Set default standard deviation for all models when choosing \
            a random port number from a normal distribution to <n>.")
        group.add_argument(
            "--model-valid-port-probability", metavar="<n>", type=float,
            default=0.4,
            help="Set default probability of choosing a valid port for all "
            "models when choosing a random port number to <n>.")
        group.add_argument(
            "--model-valid-ports", metavar="<port[=weight][,...]>",
            type=self._port_weight_tuple,
            default="21=5,22=10,23=5,25=5,80=100,110=5,220=5,443=20",
            help="A comma separated list of port_number=weight that will be \
            used when choosing a random valid port number. E.g. 80=10 means \
            port 80 with the probability weight of 10.")

    def _port_weight_tuple(self, key_values):
        """
        Given "a=b,c=d,..." as a string returns the tuple
        ([a, c, ...], [b, d, ...]) which a, b, c, ... are numbers.
        """
        keys = []
        values = []

        for key_value in key_values.split(","):
            key_value = key_value.strip()
            key, value, *_ = key_value.split("=", 1) + [1]
            key, value = int(key), int(value)
            keys.append(key)
            values.append(value)

        return (keys, values)
