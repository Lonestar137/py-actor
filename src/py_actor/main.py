from thespian.actors import ActorSystem, Actor, ActorAddress


class HelloActor(Actor):

    def receiveMessage(self, message, sender):
        self.send(sender, f"Hello, {message}")


class PingActor(Actor):

    def receiveMessage(self, message, sender):
        if message == 'ping':
            self.send(sender, 'pong')
        else:
            self.send(sender, 'unintelligible')


def main():
    actor_system = ActorSystem('multiprocTCPBase')
    actor_ref = actor_system.createActor(HelloActor)
    response = actor_system.ask(actor_ref, 'World', timeout=5)
    print(response)
    actor_system.shutdown()


def server():
    system = ActorSystem('multiprocTCPBase')
    actor = system.createActor(PingActor)
    print("PingActor created with address:", actor)
    system.listen()


def send_ping():
    remote_actor_address = "10.0.0.74:37867"

    system = ActorSystem('multiprocTCPBase')
    local_actor = system.createActor(PingActor)
    print("PingActor created with address:", local_actor)

    remote_actor = ActorAddress(remote_actor_address)
    response = system.ask(remote_actor, 'ping', timeout=5)
    print("Response from remote actor:", response)


if __name__ == '__main__':
    # main()
    # server()
    send_ping()
