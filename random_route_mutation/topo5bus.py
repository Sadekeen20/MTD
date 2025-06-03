from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.log import setLogLevel, info


class FiveBusTopo(Topo):
    def build(self):
        # Add switches s1 to s5
        s = {}
        for i in range(1, 6):
            s[i] = self.addSwitch('s{}'.format(i))

        # Add two hosts with /24 subnet masks
        # h1 = self.addHost('h1', ip='10.0.0.1/24')
        # h2 = self.addHost('h2', ip='10.0.0.2/24')

        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')

        # Host-to-switch connections
        self.addLink(h1, s[1])  # h1 to s1
        self.addLink(h2, s[5])  # h2 to s5

        # IEEE 5-Bus Mesh Topology
        self.addLink(s[1], s[2])
        self.addLink(s[1], s[3])
        self.addLink(s[2], s[3])
        self.addLink(s[2], s[5])
        self.addLink(s[2], s[4])
        self.addLink(s[4], s[5])
        self.addLink(s[3], s[4])


def run():
    topo = FiveBusTopo()
    net = Mininet(topo=topo, link=TCLink, controller=None)

    # Connect to external controller (Ryu or ONOS)
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    net.start()
    info("*** Network is up. Use CLI to test connectivity.\n")

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()
