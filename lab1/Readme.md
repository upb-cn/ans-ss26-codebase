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
