import logging
from threading import Thread
import zmq

_logger = logging.getLogger('Transceiver')


class Transceiver(object):
    def __init__(self, input_stream_url, output_stream_url, processing_func):
        self.input_stream_url = input_stream_url
        self.output_stream_url = output_stream_url
        self.processing_func = processing_func

        self.last_run_id = None

        self.run_thread = True
        self.transceiver_thread = Thread(target=self.run_transceiver)
        self.transceiver_thread.start()

    def run_transceiver(self):
        try:
            ctx = zmq.Context()

            _logger.info(f'Connecting input stream to {self.input_stream_url}.')
            input_stream = ctx.socket(zmq.SUB)
            input_stream.setsockopt(zmq.RCVTIMEO, 500)
            input_stream.connect(self.input_stream_url)
            input_stream.setsockopt_string(zmq.SUBSCRIBE, "")

            _logger.info(f'Binding output stream to {self.output_stream_url}.')
            output_stream = ctx.socket(zmq.PUB)
            output_stream.bind(self.output_stream_url)

            while self.run_thread:
                try:
                    recv_bytes = input_stream.recv()
                except zmq.Again:
                    continue

                message = self.processing_func(recv_bytes)

                if message:
                    output_stream.send(message)

            _logger.info('Transceiver stopping on request.')

        except Exception as e:
            _logger.exception("Transceiver error", e)
            raise KeyboardInterrupt

    def stop(self):
        self.run_thread = False
        self.transceiver_thread.join()
