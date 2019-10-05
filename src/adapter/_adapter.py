class Adapter():

    def __init__(self, client):
        self.client = client

    def start(self):
        self.client.register(Events.CREATE, self.create)
        self.client.register(Events.READ, self.read)
        self.client.register(Events.UPDATE, self.update)
        self.client.register(Events.DELETE, self.delete)
        self.client.run()

    def create(self, *args):
        raise NotImplementedError("Didn't implement create behavior.")

    def read(self, *args):
        raise NotImplementedError("Didn't implement read behavior.")

    def update(self, *args):
        raise NotImplementedError("Didn't implement update behavior.")

    def delete(self, *args):
        raise NotImplementedError("Didn't implement delete behavior.")


class Events():

    CREATE = 0
    READ = 1
    UPDATE = 2
    DELETE = 3
