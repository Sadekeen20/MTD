# shuffler.py
import random
import time

def shuffle_ips(participating_hosts):
    """Shuffle IP addresses among hosts."""
    print("\n[IP SHUFFLE] Shuffling IPs...")
    ip_pool = ["192.168.0." + str(i) for i in range(2, 100)]
    random.shuffle(ip_pool)

    for host, ip in zip(participating_hosts, ip_pool):
        try:
            host.cmd('ifconfig {} 0.0.0.0'.format(host.defaultIntf()))
            host.cmd('ifconfig {} {}'.format(host.defaultIntf(), ip))
            host.setIP(ip)  #extra--delete if messes up
            print("Assigned IP {} to {}".format(ip, host.name))
        except Exception as e:
            print("Error assigning IP to {}: {}".format(host.name, str(e)))
    print("[IP SHUFFLE] Completed.\n")

def shuffle_ports(net, hosts):
    """Shuffle listening ports and update flows."""
    print("[PORT SHUFFLE] Shuffling ports and updating flows...")

    # Shuffle ports
#    ports = [21, 22, 23, 24]
    ports = [8021, 8022, 8023, 8024]
    random.shuffle(ports)

    s1, s2, s3 = net.get('s1'), net.get('s2'), net.get('s3')
    h1, h2, h3, h4 = hosts

    # Stop previous services
    for h in hosts:
        h.cmd('killall nc 2>/dev/null')
    h4.cmd('killall python3 2>/dev/null')

    # Start new listeners
    #h1.cmd('nc -l {} &'.format(ports[0]))
    h2.cmd('nc -l {} &'.format(ports[1]))
    h3.cmd('nc -l {} &'.format(ports[2]))
    h4.cmd('python3 -m http.server {} &'.format(ports[3]))
    
    h1.cmd("python3 -m http.server 8080 &")  # Static server

    # Deploy resource-limited HTTP server on h1
    h1.cmd("ulimit -n 10; python3 -m http.server {} &".format(ports[0]))
    print("[HTTP SERVER] Deployed limited HTTP server on {}:{}\n".format(h1.IP(), ports[0]))

    # Reset flows
    for sw in [s1, s2, s3]:
        sw.cmd('ovs-ofctl del-flows {}'.format(sw.name))

    # Add flows based on new ports
    sw_rules = [
        (s1, h1, ports[0]), (s1, h2, ports[1]),
        (s2, h3, ports[2]), (s3, h4, ports[3])
    ]

    for sw, host, port in sw_rules:
        mac = host.MAC()
        sw.cmd('ovs-ofctl add-flow {} "priority=100,dl_src={},actions=output:{}"'.format(sw.name, mac, port))
        sw.cmd('ovs-ofctl add-flow {} "priority=100,dl_dst={},actions=output:{}"'.format(sw.name, mac, port))
#        print("Configured {} to use port {} for {}".format(sw.name, port, host.name))


    print("\n[ACTIVE SERVICES]")
    print("h1: {} -> limited HTTP on port {}, static HTTP on 8080".format(h1.IP(), ports[0]))
    print("h2: {} -> nc listening on port {}".format(h2.IP(), ports[1]))
    print("h3: {} -> nc listening on port {}".format(h3.IP(), ports[2]))
    print("h4: {} -> HTTP server on port {}".format(h4.IP(), ports[3]))

    print("[PORT SHUFFLE] Completed.\n")

def run_shuffling_periodically(net, participating_hosts, interval=10):
    """Run both IP and port shuffling periodically."""
    h1, h2, h3, h4 = participating_hosts
    iteration = 0

    while True:
        print("\n==== Shuffling Iteration {} ====".format(iteration + 1))
        #shuffle_ips(participating_hosts)
        shuffle_ports(net, [h1, h2, h3, h4])
        # net.pingAll()
        iteration += 1
        time.sleep(interval)
