from . import BaseMedia


def _import_third_party_libs():
    global kafka
    import kafka


class KafkaMedia(BaseMedia):
    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        _import_third_party_libs()

        self._options = options
        self._topic = self._options["topic"]
        self._producer: kafka.KafkaProducer = None
        self.force_flush = self._options["force_flush"]

    def _write(self, batch: str):
        if not isinstance(batch, str):
            raise ValueError("kafka media only accepts string value.")
        # producer have to be created per process
        if not self._producer:
            self._producer = kafka.KafkaProducer(
                bootstrap_servers=
                    self._options["bootstrap_servers"].split(","),
                    batch_size=2**16,
                    linger_ms=1000,
            )
        self._producer.send(topic=self._topic, value=batch.encode("utf-8"))
        if self.force_flush:
            self._producer.flush(3)

    def __del__(self):
        if self._producer:
            self._producer.flush(5)
