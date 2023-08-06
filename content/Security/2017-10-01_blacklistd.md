Title: Blacklist them skiddies with blacklistd
Tags: Network SSH FreeBSD
Category: Security
Author: Bernard Spil
Image: /img/blacklistd.png
Status: draft
Summary: Your OpenSSH setup is safe, but why suffer with all the spam in the logs from skiddies trying to brute-force your server? blacklistd to the rescue!

My OpenSSH configuration does not allow password login (or root login for that matter). Attackers on the internet will just keep on trying to login with a password generating many log-entries that end up in my `daily` output.

In the olden days I just had OpenSSH running on port 22 and built my own blackhole solution with shell scripting. Nowadays I run OpenSSH externally on 2022 and it seems the skiddies have found out. Luckily FreeBSD added `blacklistd` in 11.0 and it's about time I find out how I can use that to reduce log-spam. Blacklistd "supports" ipfw as well as the other available firewalls on FreeBSD.

= What is `blacklistd` =

`blacklistd` runs as a daemon and other daemons can send it messages about security events. It is a bit like syslog as it reads its messages from a socket. The man-page of blacklistd describes quite well how that all works, I encourage you to read the [man-page](https://www.freebsd.org/cgi/man.cgi?query=blacklistd) to see how it all fits together.

= Configuration =

As always, I like my own way of doing things


    blacklistd_enable="YES"

