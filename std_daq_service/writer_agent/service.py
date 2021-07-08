from logging import getLogger
from threading import Event

import zmq

from std_daq_service.protocol import ImageMetadata

_logger = getLogger("RequestWriterService")


class RequestWriterService(object):
    def __init__(self, input_stream_url, output_stream_url):
        self.input_stream_url = input_stream_url
        self.output_stream_url = output_stream_url

        self.interrupt_request = Event()
        self.current_request_id = None

        ctx = zmq.Context()

        _logger.info(f'Connecting input stream to {self.input_stream_url}.')
        self.input_stream = ctx.socket(zmq.SUB)
        self.input_stream.setsockopt(zmq.RCVTIMEO, 100)
        self.input_stream.connect(self.input_stream_url)

        _logger.info(f'Binding output stream to {self.output_stream_url}.')
        self.output_stream = ctx.socket(zmq.PUB)
        self.output_stream.bind(self.output_stream_url)

    def on_request(self, request_id, request):
        self.interrupt_request.clear()
        self.current_request_id = request_id

        n_images = request['n_images']
        writer_stream_data = {
            'output_file': request['output_file'],
            'run_id': request['run_id'],
            'n_images': n_images,
            'image_metadata': ImageMetadata().as_dict()
        }

        _logger.info(f"Starting write request for n_images {writer_stream_data['n_images']} "
                     f"in {writer_stream_data['output_file']}")

        i_image = 0

        try:
            self.input_stream.setsockopt_string(zmq.SUBSCRIBE, "")

            while i_image < n_images and not self.interrupt_request.is_set():
                try:
                    recv_bytes = self.input_stream.recv()
                except zmq.Again:
                    continue

                writer_stream_data['image_metadata'] = ImageMetadata.from_buffer_copy(recv_bytes).as_dict()
                writer_stream_data['i_image'] = i_image

                self.output_stream.send_json(writer_stream_data)
                i_image += 1

            # Stop message has i_image == n_images.
            writer_stream_data["i_image"] = n_images
            self.output_stream.send_json(writer_stream_data)

        finally:
            self.input_stream.setsockopt_string(zmq.UNSUBSCRIBE, '')

    def on_kill(self, request_id):
        if self.current_request_id == request_id:
            self.interrupt_request.set()
