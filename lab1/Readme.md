# Readme
First thing in any window: `cd share/ans-ss26-labs/lab1`

In first window: `ryu-manager ans_controller.py` or `ryu-manager ryu.app.ofctl_rest ans_controller.py` to use the `SwitchFlowTester`

In second window: `sudo python3 run_network.py`

From second window once network runs: `xterm h1` (h2, etc) to open host terminals

In second window to restart network: `exit`, then `sudo mn -c`, which also kills the controller

## Common troubleshooting commands
Ping: `h1 ping h2 -c5` , `pingall`

Check TCP/UDP connectivity: `iperf h1 h2 (-u)` , add -u for UDP

See flow tables on node s1: `sudo ovs-ofctl dump-flows s1` (in separate window, not mininet)

# RFC things to look at

[RFC Link](https://datatracker.ietf.org/doc/html/rfc1812)

### Page 39: Packet Drop Action
In the following, the action specified in certain cases is to
silently discard a received datagram.  This means that the datagram
will be discarded without further processing **and that the router will
not send any ICMP error message** (see Section [4.3]) as a result.
However, for diagnosis of problems a router SHOULD provide the
capability of logging the error (see Section [1.3.3]), including the
contents of the silently discarded datagram, and SHOULD count
datagrams discarded.

Das heißt: packet drop action = keine extra ICMP error message action

### Page 46: TTL
Note in particular that a router MUST NOT check the TTL of a packet
except when forwarding it.

A router MUST NOT originate or forward a datagram with a Time-to-Live
(TTL) value of zero.

A router MUST NOT discard a datagram just because it was received
with TTL equal to zero or one; if it is to the router and otherwise
valid, the router MUST attempt to receive it.

Auf Page 65 steht auch für IP Forwarding: The forwarder decrements (by at least one)

Das heißt: Jedes packet was der router (controller in unserem fall) forwarded (d.h. nicht selber schreibt) muss ttl-1 haben, aber neue pakete (z.b. ICMP echo) nicht.
Ich glaube aber dass der router die packets schon selber dropped wenn ttl 0 ist, das müssen wir nicht extra als match action rule machen, aber kann man evtl. testen

### Page 49: Router IP origin + broadcast
When a router originates any datagram, the IP source address MUST be
one of its own IP addresses (but not a broadcast or multicast
address).  The only exception is during initialization.

For most purposes, a datagram addressed to a broadcast or multicast
destination is processed as if it had been addressed to one of the
router's IP addresses;

### Page 58: ICMP Echo
A router MUST implement an ICMP Echo server function that receives
Echo Requests sent to the router, and sends corresponding Echo
Replies.

The IP source address in an ICMP Echo Reply MUST be the same as the
specific-destination address of the corresponding ICMP Echo Request
message.

Data received in an ICMP Echo Request MUST be entirely included in
the resulting Echo Reply.

### Page 71: Router to Router
Das müssen wir NICHT machen, weil nur 1 router:

When a router is going to forward a packet, it must determine whether
it can send it directly to its destination, or whether it needs to
pass it through another router.  If the latter, it needs to determine
which router to use.  This section explains how these determinations
are made.
