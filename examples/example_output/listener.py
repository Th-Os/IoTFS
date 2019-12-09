from corefs.listener.listener import Listener


class CustomListener(Listener):

    def __init__(self):
        super().__init__()

    def process(self, item):
        with open("./log", "a+") as f:
            f.write(item.event.name + "_" + item.operation.name + "\n")
