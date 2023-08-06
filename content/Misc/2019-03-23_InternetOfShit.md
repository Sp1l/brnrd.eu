Title: Killing the "Internet of shiT"
Date: 2019-03-23
Tags: Weekend, Solar, PV, IoT
Image: /img/PVOutput-Goodwe.png
Summary: The only IoT device in my LAN is the inverter (ca. 400V DC to 230V@50Hz AC) for my solar panels. I don't like devices that do not/can not update in my network. Now that the website I used to pull the measurement data from is changed (and thus broken) I decided to reverse what the device does and build my own service.

# Security?

First order of business is to find out what the inverter actually does and to see if it is in any way secure.

Summary:

 * admin:admin as credentials
 * Plain-text web-services
 * Likely no protection against spoofing measurements

# Where are you?

The inverter is connected to my wireless LAN and uses DHCP to get an IP-address. Thus it gets the DNS configuration I push from my FreeBSD home-server.
There's an unknown device in my network with a MAC OUI AC:CF:23 which apparently is registered by [Hi-Flyin](http://www.hi-flying.com/).
The IP-address has port 80 open (no other ports) and runs a webserver. It even has a login (realm A11)! So how do I get in?!?
Let's just try Username admin and Password admin... Lo' and behold!

![Goodwe WebUI]({static}/img/GoodweUI.png)

From the WebUI we can see that this *is* the Goodwe Inverter, so let's move on!

# What are you doing?

Now that we know the IP-address of the inverter, it's time to find out what the thing is actually doing on the network. My home-server is not acting as the gateway, but it is hosting DNS. Time to fire up pcap to see where it connects to.

    :::shell
    tcpdump -i em0 -p host ....2.107

This quickly results in some DNS requests

    :::shell
    14:22:51.819712 IP HF-A11.20306 > brnrd.eu.domain: 454+ A? www.goodwe-power.com. (38)
    14:22:51.819814 IP brnrd.eu.domain > HF-A11.20306: 454* 1/0/0 A 172.17.2.8 (54)

This tells us they're simply connecting to www.goodwe-power.com. Waiting a bit longer doesn't result in any other addresses it resolves using DNS.

## DNS: Unbound

Now it's time to convince the inverter to connect to some other host where I can capture the data. To do this I just add a simple line to my unbound configuration in `/var/unbound/conf.d/spoof.conf`

    :::
    local-data: "www.goodwe-power.com. IN A ....2.8"

and reload the configuration, test if this does what it says on the tin.

    :::shell
    service unbound reload
    host www.goodwe-power.com
    www.goodwe-power.com has address ....2.8

Any traffic from the inverter should now go to my web-server.

## Again, what are you doing?

Again, we fire up tcpdump to check what the inverter tries to do. This time we can see more traffic

    :::shell
    14:30:52.612884 IP HF-A11.1620 > gw.http: Flags [S], seq 1910663072, win 16384, options [mss 1460,nop,wscale 0,nop,nop,TS val 55601 ecr 0], length 0
    14:30:52.612933 IP gw.http > HF-A11.1620: Flags [S.], seq 1593908410, ack 1910663073, win 65535, options [mss 1460,nop,wscale 6,nop,nop,TS val 594925872 ecr 55601], length 0
    14:30:52.614563 IP HF-A11.1620 > gw.http: Flags [.], ack 1, win 18824, options [nop,nop,TS val 55601 ecr 594925872], length 0

BINGO! The inverter simply connects to the HTTP port. No security here!

## Re-routing the traffic via my web-server

I tear down the DNS spoofing temporarily to prepare my web-server for interception. I don't want to loose measurements!

Now we go over to the web-server and add a virtual host that simply relays the requests to the Goodwe server.

    :::apache
    <VirtualHost *:80>
       ServerName www.goodwe-power.com
    
       ProxyPreserveHost On
       ProxyPass /        http://47.254.132.36/
       ProxyPassReverse / http://47.254.132.36/
    </VirtualHost>

After reloading the apache configuration, I run a quick test to see if this all works as expected (relevant output only):

    :::shell
    service apache24 reload
    curl -vI http://    
    ...
    * Connected to www.goodwe-power.com (172.17.2.8) port 80 (#0)
    > HEAD / HTTP/1.1
    ...
    < Server: nginx

That's the Goodwe server's response, not Apache's, on the correct IP-address and port.

## Again again, what are you doing?

Enabled the DNS spoofing again, and fired up tcpdump. This time I log all output to a file.

    :::shell
    tcpdump -i em0 -p -s0 -w./goodwe.pcap host ....2.107 and port 80

The output file is then inspected in [WireShark](https://wireshark.org). The only thing the inverter is doing is posting content.

    :::
    0000   b4 99 ba eb fe af ac cf 23 aa bb cc 08 00 45 00   ........#.S)..E.
    0010   00 da 12 f0 00 00 40 06 0a 99 01 01 02 6b 01 01   ......@......k..
    0020   02 08 42 65 00 50 38 4b 52 94 49 a3 8b ad 80 18   ..Be.P8KR.I.....
    0030   49 88 b9 14 00 00 01 01 08 0a 00 00 9e 56 14 33   I............V.3
    0040   49 90 50 4f 53 54 20 2f 41 63 63 65 70 74 6f 72   I.POST /Acceptor
    0050   2f 44 61 74 61 6c 6f 67 20 48 54 54 50 2f 31 2e   /Datalog HTTP/1.
    0060   31 0d 0a 43 6f 6e 6e 65 63 74 69 6f 6e 3a 43 6c   1..Connection:Cl
    0070   6f 73 65 0d 0a 43 6f 6e 74 65 6e 74 2d 4c 65 6e   ose..Content-Len
    0080   67 74 68 3a 30 36 36 0d 0a 48 6f 73 74 3a 77 77   gth:066..Host:ww
    0090   77 2e 67 6f 6f 64 77 65 2d 70 6f 77 65 72 2e 63   w.goodwe-power.c
    00a0   6f 6d 0d 0a 0d 0a 00 31 33 36 30 30 44 53 55 31   om.....13600DSU1
    00b0   31 30 30 30 30 34 31 01 00 2e 0a 5d 08 06 00 10   1000041....]....
    00c0   00 0e 09 05 00 1e 13 85 02 9a 00 01 00 f2 00 00   ................
    00d0   00 00 00 02 16 30 00 00 40 4e 00 14 00 00 00 00   .....0..@N......
    00e0   00 00 0e 1d 00 00 00 0f                           ........

In the output, I recognize my inverter's ID as I also see it on the Goodwe website "13600DSU11100041".

**NOTE**: The device ID has been modified, I don't want anyone to pollute my data!

The POST body contains binary data, what does it mean!? I decided to collect some more samples to see if I can find out what's what in this binary data.

# Reverse-engineering the payload

Here are 3 of the POST bodies, without the device ID for brevity

    :::
    12:25:18 01 00 2e 0a 5d 08 06 00 10 00 0e 09 05 00 1e 13 85 02 9a 00 01 00 f2 00 00 00 00 00 02 16 30 00 00 40 4e 00 14 00 00 00 00 00 00 0e 1d 00 00 00 0f
    12:33:19 01 00 2e 0a 47 08 04 00 0e 00 0b 08 f2 00 1b 13 85 02 46 00 01 00 f3 00 00 00 00 00 02 16 31 00 00 40 4e 13 1d 00 00 00 00 00 00 0e 06 00 00 00 10
    12:41:20 01 00 2e 0a 2c 08 05 00 0e 00 0a 08 fa 00 19 13 88 02 18 00 01 00 f4 00 00 00 00 00 02 16 32 00 00 40 4e 00 14 00 00 00 00 00 00 0e 11 00 00 00 11
    12:49:21 01 00 2e 0a 49 08 31 00 0e 00 0b 09 05 00 1a 13 87 02 3f 00 01 00 f4 00 00 00 00 00 02 16 33 00 00 40 4f 13 1d 00 00 00 00 00 00 0e 20 00 00 00 12

On the new Goodwe portal, I can download measurements using the "Reports" section. I selected all available measurements for my inverter, and downloaded the excel sheet.

| Time | Mode | Vpv1(V) | Vpv2(V) | Ipv1(A) | Ipv2(A) | Vac1(V) | Iac1(A) | Fac1(Hz) | Pac(W) | Temp(℃) | Daily(kWh) | Total(kWh) | HTotal(Hrs) | RSSI(%) |
| -------- | ------ | ----- | ----- | --- | --- | ----- | - | ----- | ----- | ---- | --- | ------- | ----- | ----- |
| 12:25:18 | Normal | 265.3 | 205.4 | 1.6 | 1.4 | 230.9 | 3.0 | 49.97 | 666 | 24.2 | 1.5 | 13675.2 | 16462 | 0 |
| 12:33:19 | Normal | 263.1 | 205.2 | 1.4 | 1.1 | 229.0 | 2.7 | 49.97 | 582 | 24.3 | 1.6 | 13675.3 | 16462 | 0 |
| 12:41:20 | Normal | 260.4 | 205.3 | 1.4 | 1.0 | 229.8 | 2.5 | 50.00 | 536 | 24.4 | 1.7 | 13675.4 | 16462 | 0 |
| 12:49:21 | Normal | 263.3 | 209.7 | 1.4 | 1.1 | 230.9 | 2.6 | 49.99 | 575 | 24.4 | 1.8 | 13675.5 | 16463 | 0 |

There's no directly visible relation between these 2 sets of data. From the tcpdump output we see that there are hardly any plain ASCII characters in here either. Let's try to convert some of the values to hex and see where that leads. The simple targets are the ones without decimals, so Pac(W) it must be! Using the dec2hex() function of LibreOffice or Excel makes this an easy task.

| Pac | Hex(Pac) |
| --- | -------- |
| 666 | 02 9a |
| 582 | 02 46 |
| 536 | 02 18 |
| 575 | 02 3f |

These are all present in the table above! (somewhere halfway the binary output). The values with decimals, I multiplied by 10 (100 for the frequency) and converted to hex:

| Time     | Vpv1  | Vpv2  | Ipv1  | Ipv2  | Vac1  | Iac1  | Fac1  | Pac   | Temp  | Daily | Total       | HTotal |
| -------- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----------- | ----- |
| 12:25:18 | 0A 5D | 08 06 | 00 10 | 00 0E | 09 05 | 00 1E | 13 85 | 02 9A | 00 F2 | 00 0F | 00 02 16 30 | 40 4E |
| 12:33:19 | 0A 47 | 08 04 | 00 0E | 00 0B | 08 F2 | 00 1B | 13 85 | 02 46 | 00 F3 | 00 10 | 00 02 16 31 | 40 4E |
| 12:41:20 | 0A 2C | 08 05 | 00 0E | 00 0A | 08 FA | 00 19 | 13 88 | 02 18 | 00 F4 | 00 11 | 00 02 16 32 | 40 4E |
| 12:49:21 | 0A 49 | 08 31 | 00 0E | 00 0B | 09 05 | 00 1A | 13 87 | 02 3F | 00 F4 | 00 12 | 00 02 16 33 | 40 4F |

As you can see, all these values can be found in the binary POST body. They're even in the right order, apart from the Daily kWh which is the last column. That leaves us with the remaining data (hex, then decimal where not "00 00"):

| Mode?    | 2nd   | 3rd   | 4th   | 5th   | 6th   | 7th   | Dec(2nd) | Dec(6th) |
| -------- | ----- | ----- | ----- | ----- | ----- | ----- | -----:| -----:|
| 01 00 2e | 00 14 | 00 00 | 00 00 | 00 00 | 0e 1d | 00 00 | 20    | 3613 |
| 01 00 2e | 13 1d | 00 00 | 00 00 | 00 00 | 0e 06 | 00 00 | 4893  | 3590 |
| 01 00 2e | 00 14 | 00 00 | 00 00 | 00 00 | 0e 11 | 00 00 | 20    | 3601 |
| 01 00 2e | 13 1d | 00 00 | 00 00 | 00 00 | 0e 20 | 00 00 | 4893  | 3616 |

There doesn't seem to be any relevant data in here, perhaps some checksum?

What I've ended up with:

| Bytes | Field | Value | Hex |
| ----:| ---- |:---- |:---- | 
| 1 - 17 | Device ID | .13600DSU11000041 | 00 31 33 36 30 30 44 53 55 31 35 33 30 30 30 34 37 |
| 18 - 20 | Mode? | | 01 00 2e |
| 21 - 22 | Vpv1 (V) | 265.3 | 0a 5d |
| 23 - 24 | Vpv2 (V) | 205.4 | 08 06 |
| 25 - 26 | Ipv1 (A) | 1.6 | 00 10 |
| 27 - 28 | Ipv2 (A) | 1.4 | 00 0e |
| 29 - 30 | Vac1 (V) | 230.9 | 09 05 |
| 31 - 32 | Iac1 (A) | 3.0 | 00 1e |
| 33 - 34 | Fac1 (Hz) | 49.97 | 13 85 |
| 35 - 36 | Pac (W) | 666 | 02 9a |
| 37 - 38 | unknown | .. | 00 01 |
| 39 - 40 | Temp (&deg;C) | 24.2 | 00 f2 |
| 41 - 44 | unknown | .... | 00 00 00 00 |
| 45 - 48 | Total (kWh) | 13675.2 | 00 02 16 30 |
| 49 - 52 | HTotal (Hrs) | 16462 | 00 00 40 4e |
| 53 - 64 | unknown | ...... | 00 14 00 00 00 00 00 00 0e 1d 00 00 
| 65 - 66 | Daily (kWh) | 1.5 | 00 0f |

# Writing a parser

Now that I know what the structure of the data is, I can start writing a parser. This will allow me to push the data straight into [PVoutput.org](https://pvoutput.org/) without having to scrape it from the Goodwe website first.

To be continued!