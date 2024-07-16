Title: Immutable Alpine Linux in bhyve
Tags: bhyve, FreeBSD, linux, Alpine
Date: 2023-02-11
Modified: 2023-02-11 16:18:00
Author: Bernard Spil
Image: /img/bhyve-alpine.png
Summary: Many things don't have proper installation docs any longer and are only provided as Docker (or podman) images. I set out to run Docker on FreeBSD with a minimal Linux using bhyve.

Part 1 of a multip-part series where I hope to end up with some running Docker containers.

## Setting up FreeBSD for bhyve

We'll use the [sysutils/vm-bhyve](https://github.com/churchers/vm-bhyve) port to simplify bhyve invocation.

Enable serial console

    kldload nmdm
    echo 'nmdm_load="YES"' >> /boot/loader.conf

Create storage for bhyve

    zfs create -o mountpoint=/vm zroot/bhyve

Install required packages

    pkg install bhyve-firmware vm-bhyve`

Enable `bhyve-vm`, set storage location an initialize

    sysrc vm_enable YES
    sysrc vm_dir='zfs:zroot/bhyve'

    vm init
    vm switch create public
    vm switch add public em0

    cp /usr/local/share/examples/vm-bhyve/* /vm/.templates

## Create the VM, storage and configuration

Create the VM we'll use

    vm create -t alpine Alpine

This will create `zroot/bhyve/Alpine` dataset

Create the persistent storage for the Alpine overlay.

    cd /vm/Alpine
    truncate -s 33555456 apkovl.img
    mddev=$(mdconfig apkovl.img)
    gpart create -s MBR /dev/${mddev}
    gpart add -t linux-data ${mddev}
    newfs_msdos -L apkovl /dev/${mddev}s1
    mdconfig -d -u ${mddev}

The FAT32 partition will be `/dev/vda1` in Alpine. Using partition type fat32 failed for me.

Modify your `/vm/Alpine/Alpine.conf` to something like

```
loader="grub"
graphics="no"
cpu=4
memory=4096M
network0_type="virtio-net"
network0_switch="public"
disk0_type="ahci-cd"
disk0_name="alpine-virt-latest-x86_64.iso"
disk1_type="virtio-blk"
disk1_name="apkovl.img"
grub_run0="set root=(hd0)
grub_run1="linux /boot/vmlinuz-virt modules=loop,squashfs,sd-mod,usb-storage quiet console=tty0 console=ttyS0,115200"
grub_run2="initrd /boot/initramfs-virt"
uuid="random"
network0_mac="random"
```

Note: The disk0 iso is mapped to the VM as hd0. disk1 will be /dev/vda in Alpine.

**NOTE**: We're not installing, we'll run Alpine from memory with storage on the FreeBSD host.

## Interlude: Grab latest image from Alpine

Python scriptlet to get latest URL from Alpine's download CDN, you'll need to have the `devel/py-yaml` port installed.

```
#!/usr/bin/env python3

import urllib.request
import yaml

BASE_URL = "https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/x86_64"

with urllib.request.urlopen(f"{BASE_URL}/latest-releases.yaml") as response:
    data = yaml.safe_load(response.read().decode())

iso = [flavor["iso"] for flavor in data if flavor["flavor"] == "alpine-virt"][0]

print(f"{BASE_URL}/{iso}")
```

Download and link the latest iso

```
vm iso https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/x86_64/alpine-virt-3.17.2-x86_64.iso
(cd /vm/Alpine
ln -sf ../.iso/alpine-virt-3.17.2-x86_64.iso alpine-virt-latest-x86_64.iso
)
```

## First boot

Start Alpine and enter using serial console

```
vm start Alpine
vm console alpine
```

This will show `Connected`, if you hit Enter you end up at the login prompt. User `root` has no password (yet). Mount the persistent storage and use the `setup-alpine` command to configure the system.

    mkdir -p /media/vda1
    echo "/dev/vda1 /media/vda1 vfat rw 0 0" >> /etc/fstab
    mount -a
    setup-alpine

These are the answers I provided, removed some output for brevity.
We're only creating the root user, no other users.

```
Enter system hostname (fully qualified form, e.g. 'foo.example.org') [localhost] docker
Available interfaces are: eth0.
Enter '?' for help on bridges, bonding and vlans.
Which one do you want to initialize? (or '?' or 'done') [eth0] eth0
Ip address for eth0? (or 'dhcp', 'none', '?') [dhcp] dhcp
Do you want to do any manual network configuration? (y/n) [n] n
udhcpc: lease of 192.2.0.166 obtained from 192.2.0.1, lease time 86400
Changing password for root
New password: <your password>
Retype password: <your password>
passwd: password for root changed by root
Which timezone are you in? ('?' for list) [UTC] UTC
HTTP/FTP proxy URL? (e.g. 'http://proxy:8080', or 'none') [none] none
Which NTP client to run? ('busybox', 'openntpd', 'chrony' or 'none') [chrony] none
Enter mirror number (1-71) or URL to add (or r/f/e/done) [1]
Added mirror dl-cdn.alpinelinux.org
Updating repository indexes... done.
Setup a user? (enter a lower-case loginname, or 'no') [no] no
Which ssh server? ('openssh', 'dropbear' or 'none') [openssh] openssh
Allow root ssh login? ('?' for help) [prohibit-password] prohibit-password
Enter ssh key or URL for root (or 'none') [none] none
No disks available. Try boot media /media/cdrom? (y/n) [n]
Enter where to store configs ('floppy', 'usb', 'vda1' or 'none') [vda1] vda1
Enter apk cache directory (or '?' or 'none') [/media/vda1/cache] /media/vda1/cache
WARNING: Ignoring http://dl-cdn.alpinelinux.org/alpine/v3.17/main: No such file or directory
```
    
The sshd setup didn't do what it advertises it does, we'll get to that later.
Now we persist our changes:

    lbu commit

this generates a file `/media/vda1/docker.apkovl.tar.gz`. If you'd restart the VM now, you get the settings as stored in the apkovl tarball.

Powerdown the VM.

    poweroff

Not sure if this is how it should work, but my SSH session locks up for a couple seconds when I poweroff a VM. Type `~~.` to exit the Serial Console.

## Modify the Alpine overlay

Mount the Alpine overlay in your host

    mkdir /mnt/apkovl
    mddev=$(mdconfig /vm/Alpine/apkovl.img)
    mount_msdosfs /dev/${mddev}s1 /mnt/apkovl

Unpack the transferred `docker.apkovl.tar.gz` in a working dir

    cd ~
    mkdir docker.apkovl
    cd docker.apkovl
    tar xf /mnt/apkovl/docker.apkovl.tar.gz

You end up with the overlay in `docker.apkovl/etc`. Anything you do in that will be in your Alpine host.

We'll be loging in as root with key authentication and fetch the key from the overlay in stead of from the home directory. No need for legacy crypto on FreeBSD.

```
HostKey /etc/ssh/ssh_host_ed25519_key

HostKeyAlgorithms ssh-ed25519-cert-v01@openssh.com,ssh-ed25519
KexAlgorithms     curve25519-sha256,curve25519-sha256@libssh.org
Ciphers           chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
MACs              hmac-sha2-512-etm@openssh.com

PermitRootLogin prohibit-password

AuthorizedKeysFile      /etc/ssh/authorized_keys/%u .ssh/authorized_keys

PasswordAuthentication no

AllowTcpForwarding no
GatewayPorts no
X11Forwarding no

Subsystem       sftp    internal-sftp
```

Put the public key you'll use to access the Docker host in `etc/ssh/authorized_keys/root`

    cp ~/.ssh/id_docker.pub etc/ssh/authorized_keys/root

Package the overlay again

    tar zcf /mnt/apkovl/docker.apkovl.tar.gz --strip-components 1 .

Don't forget to tear down the mount

    umount /mnt/apkovl
    mdconfig -d -u ${mddev}

## Second boot

We can now start the Alpine VM and connect to it with SSH and our key.

    ssh -i ~/.ssh/id_docker docker

    Welcome to Alpine!

    The Alpine Wiki contains a large amount of how-to guides and general
    information about administrating Alpine systems.
    See <https://wiki.alpinelinux.org/>.

    You can setup the system with the command: setup-alpine

    You may change this message by editing /etc/motd.

    docker:~#
