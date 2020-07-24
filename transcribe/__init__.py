__version__ = "0.1.0dev"

from awscrt.io import ClientBootstrap, DefaultHostResolver, EventLoopGroup


class AWSCRTEventLoop:
    def __init__(self):
        self.bootstrap = self._initialize_default_loop()

    def _initialize_default_loop(self):
        event_loop_group = EventLoopGroup(1)
        host_resolver = DefaultHostResolver(event_loop_group)
        return ClientBootstrap(event_loop_group, host_resolver,)
