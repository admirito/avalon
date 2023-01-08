#!/usr/bin/env python3

import multiprocessing
import sys
import threading
import time


class BatchGenerator:
    """
    BatchGenerator is an abstraction for a Model, with a specific
    format and batch size in which calling next() method will return
    the next batch data from the model with the given format and size.

    There is also an attribute `ratio` for the class that is not used
    internally, but it could be used by a processor to keep track of
    the ratio of the generated data by the BatchGenerator.
    """
    def __init__(self, model, format, size, ratio=None):
        self.model = model
        self.format = format
        self.size = size

        self.ratio = ratio

    def next(self):
        batch = self.format.batch(self.model, self.size)

        return batch


class Processor:
    """
    Given a list of BatchGenerator instances and an instance of a
    Media (for transfering output data), an instance of this class can
    fork processes for each BatchGenerator instance and start to
    generate and transfer data.
    """

    # all instances of the class will be stored in _instances
    _instances = []

    def __init__(self, batch_generators, media, max_rate=None, max_number=None,
                 max_duration=None):
        self.batch_generators = batch_generators
        self._total_ratio = sum(bg.ratio for bg in batch_generators
                                if bg.ratio is not None)

        self.media = media
        self.max_rate = max_rate
        self.max_number = max_number
        self.max_duration = max_duration

        self._stop = multiprocessing.Value("i")
        self._count = multiprocessing.Value("l")
        self._start_time = multiprocessing.Value("d")
        self._lock = multiprocessing.Lock()

        self._instances.append(self)
        self._instance_index = len(self._instances) - 1

        # pool must be created after all the initializations, so the
        # forked processes are all initialized the same.
        self.pool = multiprocessing.Pool(len(self.batch_generators))

        # TODO: in the old days, in a project older than Avalon in
        # which model data were completely independent, the pool size
        # was another configurable variable and not related to the
        # number of batch-generators. The current workaround for the
        # issue of model/batch-generator dependency is forking a
        # stand-alone python process for every batch-generator. In
        # other words Avalon is only scalable because you can add
        # multiple batch generators to it. This is obviously not as
        # good as expected but fixing it may require another
        # architecture.

    def process(self):
        """
        Start the actual process by forking new Python processes.
        """
        self._start_time.value = time.time()
        # self.pool.map(self._process, self.batch_generators)
        self.pool.map(self._process_classmethod,
                      [(self._instance_index, i)
                       for i in range(len(self.batch_generators))])

    def stop(self):
        """
        Mark an internal flag to ask the processes to exit.
        """
        self._stop.value = 1

    def count(self):
        """
        Returns the total number of generated items by all the
        batch generators in all the processes.
        """
        return self._count.value

    def duration(self):
        """
        Returns the process duration until now.
        """
        return (time.time() - self._start_time.value
                if self._start_time.value > 0 else 0)

    def average_rate(self):
        """
        Returns the average rate of item generation by all the
        batch generators in all the processes.
        """
        duration = self.duration()
        if duration <= 0:
            return 0

        return self.count() / duration

    def is_stopped(self):
        """
        Returns True if the internal stop flag (by calling the
        stop method) is marked, False otherwise.
        """
        return self._stop.value != 0

    def is_finished(self):
        """
        Returns a boolean that whether the process has finished
        according to the provided max_number/max_duration for the
        instance, or not.
        """
        if self.max_number and self.count() >= self.max_number:
            return True

        if self.max_duration and self.duration() >= self.max_duration:
            return True

        return False

    @classmethod
    def _process_classmethod(cls, args):
        """
        Calling the _process method as the target of
        multiprocessing.Process (e.g. with the map method of a pool of
        processes) is not possible because the Processor class has
        some non-pick-able instance objects that can only be
        accessible in the forked processes by inheritance.

        _process_classmethod is a workaround for this problem. It will
        call _process mehtod for a specific instance object by
        leveraging the _instances attribute of Processor class.
        """
        self_index, batch_generator_index = args
        self = cls._instances[self_index]
        cls._process(self, self.batch_generators[batch_generator_index])

    def _process(self, batch_generator):
        """
        The actual process that will be executed in a dedicated
        python process.
        """
        process_count = 0

        while not self.is_stopped():
            batch = batch_generator.next()
            self._wait_for_ratio(batch_generator, process_count)
            self._wait_for_rate()

            with self._lock:
                if self.is_stopped() or self.is_finished():
                    return

                if self._will_be_finished_after(batch_generator.size):
                    self.stop()

            self.media.write(batch)
            process_count += batch_generator.size
            with self._count.get_lock():
                self._count.value += batch_generator.size

    def _will_be_finished_after(self, size):
        if not self.max_number:
            return False

        return self.count() + size >= self.max_number

    def _wait_for_ratio(self, batch_generator, batch_generator_count):
        if batch_generator.ratio is None:
            return

        while not (self.is_stopped() or self.is_finished()):
            expected_ratio = batch_generator.ratio / self._total_ratio
            current_ratio = (batch_generator_count / self.count()
                             if self.count() > 0 else -1)

            if current_ratio > expected_ratio:
                # TODO: adjust wait time dynamically according to the
                # difference between expected/current ratio and the
                # average rate
                time.sleep(0.05)
            else:
                break

    def _wait_for_rate(self):
        if not self.max_rate:
            return

        while not (self.is_stopped() or self.is_finished()):
            min_duration = self.count() / self.max_rate
            wait = min_duration - self.duration()
            if wait > 0:
                time.sleep(min(0.1, wait))
            else:
                break


class ProgressReport(threading.Thread):
    """
    A threading.Thread derivative that can print progress reports
    for a Processor instance in a separate thread.
    """
    def __init__(self, processor, interval, stream=sys.stderr, **kwargs):
        self.__processor = processor
        self.__interval = interval
        self.__stream = stream

        self.__stop = False

        super().__init__(**kwargs)
        self.daemon = kwargs.get("daemon", True)

    def run(self):
        while True:
            time.sleep(self.__interval)

            if self.__stop:
                break

            self.print_progress()

    def print_progress(self):
        self.__stream.write(
            f"{self.__processor.count()} items sent in "
            f"{self.__processor.duration():.1f} seconds. Average Rate = "
            f"{self.__processor.average_rate():.1f} / seconds\n")

    def stop(self):
        self.__stop = True
