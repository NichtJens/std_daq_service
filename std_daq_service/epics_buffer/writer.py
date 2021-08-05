import logging
import os
import struct

_logger = logging.getLogger("EpicsBufferWriter")

BUFFER_FILENAME_FORMAT = "%d.epics_buffer.bin"
BUFFER_FILE_MODULO = 100000


class EpicsBufferWriter(object):
    def __init__(self, buffer_folder):
        _logger.info(f"Starting epics buffer writer in folder {buffer_folder}.")

        self.buffer_folder = buffer_folder
        os.makedirs(self.buffer_folder, exist_ok=True)

        self.current_file = None
        self.current_file_end = None
        # Each file is a bucket in which we place BUFFER_FILE_MODULO pulses.
        self.current_bucket = None

    def _prepare_file(self, pulse_id):
        # Bucket (file) index.
        bucket_id = pulse_id // BUFFER_FILE_MODULO

        if bucket_id == self.current_bucket:
            return

        self.close()

        filename = os.path.join(self.buffer_folder, BUFFER_FILENAME_FORMAT % bucket_id)

        # Equivalent of 'touch'.
        if not os.path.exists(filename):
            _logger.debug(f"Creating buffer file {filename}.")
            open(filename, 'a').close()

        self.current_file = open(filename, mode="r+b", buffering=0)
        self.current_bucket = bucket_id
        # seek(0, 2) puts you to the end of the file.
        self.current_file_end = self.current_file.seek(0, 2)

    def write(self, pulse_id, data):
        self._prepare_file(pulse_id)

        # Slot index for pulse inside the bucket (file).
        slot_id = pulse_id % BUFFER_FILE_MODULO

        # Each slot index has 2 uint64_t (8 bytes) values
        index_offset = slot_id * 2 * 8
        data_n_bytes = len(data)

        # Write index: offset in bytes where the data starts, and the number of bytes of data.
        self.current_file.seek(index_offset)
        self.current_file.write(struct.pack("<QQ", self.current_file_end, data_n_bytes))

        # Dump the buffer to the end of the file.
        self.current_file.seek(self.current_file_end)
        self.current_file.write(data)

        self.current_file_end = self.current_file.tell()

    def close(self):
        if not self.current_file:
            return

        self.current_file.close()

        self.current_file = None
        self.current_bucket = None
        self.current_file_end = None
