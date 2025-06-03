from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
import threading
from shuffler import run_shuffling_periodically

class SimplifiedTopo(Topo):
    def build(self):
        s1, s2, s3 = self.addSwitch('s1'), self.addSwitch('s2'), self.addSwitch('s3')
        h1 = self.addHost('h1', ip='192.168.0.27/23')
        h2 = self.addHost('h2', ip='192.168.0.28/23')
        h3 = self.addHost('h3', ip='192.168.0.29/23')
        h4 = self.addHost('h4', ip='192.168.0.30/23')

        h5 = self.addHost('h5', ip='192.168.0.111/23')#added for attacker

        self.addLink(h1, s1, port1=21)
        self.addLink(h2, s1, port1=22)
        self.addLink(h3, s2, port1=23)
        self.addLink(h4, s3, port1=24)

        self.addLink(h5, s1, port1=111)#attacker

        self.addLink(s1, s2)
        self.addLink(s2, s3)

def launch_topology():
    topo = SimplifiedTopo()
    net = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip='172.17.0.5', port=6653))
    net.start()
    print("\n[*] Network started. Unified IP+Port shuffling running in background.")
    return net

if __name__ == '__main__':
    setLogLevel('info')
    net = launch_topology()
    participating_hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
#    participating_hosts = [net.get('h2'), net.get('h3'), net.get('h4')]
    shuffle_thread = threading.Thread(target=run_shuffling_periodically, args=(net, participating_hosts))
    shuffle_thread.daemon = True
    shuffle_thread.start()
    CLI(net)
    net.stop()
