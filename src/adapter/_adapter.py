class Adapter():

    def __init__(self):
        self.client = None

    def start(self):
        self.client.run()

    def create(self):
        raise NotImplementedError("Didn't implement create behavior.")

    def read(self):
        raise NotImplementedError("Didn't implement read behavior.")

    def update(self):
        raise NotImplementedError("Didn't implement update behavior.")

    def delete(self):
        raise NotImplementedError("Didn't implement delete behavior.")
