import time
class StopWatch:
    def __enter__(self, *args):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()

    @property
    def time(self):
        return self.end-self.start

