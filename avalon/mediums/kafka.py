from . import BaseMedia


def _import_third_party_libs():
    global kafka
    import kafka


class KafkaMedia(BaseMedia):
    __title__ = "kafka"

    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        _import_third_party_libs()

        self._producer: kafka.KafkaProducer = None

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        group.add_argument(
            "--kafka-bootstrap-servers", metavar="<addr>", type=str,
            help="A comma seperated list determines servers addresses.")
        group.add_argument(
            "--kafka-topic", metavar="<t>", type=str,
            help="Determines the topic.")
        group.add_argument(
            "--kafka-force-flush", action="store_true",
            help="Force to flush kafka producer for each batch, may have \
            bad effect of performance.")

    def _write(self, batch: str):
        if not isinstance(batch, str):
            raise ValueError("kafka media only accepts string value.")

        # producer have to be created per process
        if not self._producer:
            self._producer = kafka.KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(","),
                batch_size=2**16,
                linger_ms=1000,
            )

        self._producer.send(topic=self.topic, value=batch.encode("utf-8"))

        if self.force_flush:
            self._producer.flush(3)

    def __del__(self):
        if self._producer:
            self._producer.flush(5)
