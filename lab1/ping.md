# How ping works across subnets

Based on this helpful guide of ARP: https://learningnetwork.cisco.com/s/article/fundamentals-of-arp-address-resolution-protocol Starting from Situation 4

Example: `h1 ping ser`

s1, s2 = switch

s3 = router

Assumption: Host knows its GW (gateway) so that router knows it is being addressed

Errors in the current implementation will be marked later in _italic_.

## Step 1 (ARP h1 -> s3)
h1 sends ARP request to the port towards s1 with ETH dst "FF" (broadcast) as it needs to know destination mac of GW. IP dst is the GW 

## Step 2
controller receives packet at s1, stores mac to port mapping, forwards it to port at s3

## Step 3
controller receives packet at s3, detects it's ARP and that the IP dst matches the GW, so it needs to respond with ARP reply (opcode 2):
1. set ETH src as own MAC, and ETH dst as the h1 MAC (gotten from the incoming header)
2. set ARP IP/MAC dst to the incoming packet's data (h1), and ARP IP/MAC to own MAC/IP
3. Send back to port it came from (to s1)

## Step 4
controller receives packet at s1, stores mac to port mapping, detects it already has the mac from h1 (the ETH dst MAC) from Step 2, and creates a flow rule telling it to output to the port towards h1 if matching that MAC, forwards it to port at h1

Now h1 knows the MAC of the router, and it can send the ICMP echo

## Step 5 (Create Echo)
h1 sends ICMP echo to the port towards s1 with ETH dst of the s3 and IP dst of ser

## Step 6
controller receives packet at s1, detects it already has the mac from s3 (the ETH dst MAC) from Step 4, and creates a flow rule telling it to output to the port towards h1 if matching that MAC, forwards it to port at h1.

## Step 7
controller receives packet at s3, as ETH dst MAC matches router's port MAC, it should process it. router sees the IP dst matches a gateway on one of its ports, meaning the target is reachable in that subnet: Need to create a new packet with the IP src of h1 and IP dst of ser, ETC src of outgoing port, but the ETH dst is unknown.

**Issue**: _In this step it also needs to store the incoming ip + mac combo and add it to the router's flow rule, otherwise it will do an ARP again when the echo reply travels back to h1_. It does so in Step 11 for the other side but not here

So for that, it postpones the packet creation and first does an ARP:

## Step 8 (ARP s3 -> ser)
s3 sends ARP request to the port towards ser with ETH dst FF (broadcast) as it needs to know destination mac of ser. IP dst is ser

## Step 9
controller receives packet at s2, stores mac to port mapping, forwards it to port at ser. ser sends an ARP reply.

## Step 10
controller receives packet at s2, stores mac to port mapping, detects it already has the mac from ser (the ETH dst MAC) from Step 9, and creates a flow rule telling it to output to the port towards s3 if matching that MAC, forwards it to port at s3

## Step 11 (Forward Echo)
controller receives packet at s3, sees it is an ARP reply that matches the same IP it used the intended echo packet for in Step 7, and then takes that postponed packet and adds the ETH dst MAC to it, and the controller forwards it to port towards ser.

In addition, as it forwards it creates a flow rule telling it to output on that port if the same IP dst is used.

## Step 12
controller receives packet at s2, stores mac to port mapping, detects it already has the mac from s3 (the ETH dst MAC) from Step 9, and creates a flow rule telling it to output to the port towards ser if matching that MAC, forwards it to port at ser

ser now received the ICMP echo from h1

## Similar steps now in the other direction, except no ARPing, so not listed here

That the route was already traversed once in both directions during ARP, so most packets will not enter the controller anymore. If they do, it's an issue that needs to be looked at.

**Issue:** _when the ser -> h1 echo reaches s3, it still does another ARP which it shouldn't, see Step 7_