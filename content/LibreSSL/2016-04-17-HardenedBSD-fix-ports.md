Title: Fixing failing ports for Hardened/LibreBSD
Tags: SSL, LibreSSL, OpenSSL, FreeBSD, HardenedBSD
Created: 2016-04-17
Updated: 2016-08-16
Author: Bernard Spil
Image: /img/HardenedBSDLibreSSL.png
Summary: HardenedBSD ran an `exp-run` with LibreSSL in base. This was expected to uncover a lot of issues where ports check the `OPENSSL_VERSION_NUMBER` to determine if a feature is available. To my surprise, it only uncovered 12 ports that failed due to these version checks.

## Prelude

The [LibreSSL](http://libressl.org) ports (up to 2.4) on FreeBSD include a patch that modifies the OpenSSL version in the header files

	:::patch
	--- include/openssl/opensslv.h.orig     2015-09-11 22:35:14 UTC
	+++ include/openssl/opensslv.h
	@@ -7,7 +7,7 @@
	 #define LIBRESSL_VERSION_TEXT  "LibreSSL 2.3.0"
	
	 /* These will never change */
	-#define OPENSSL_VERSION_NUMBER 0x20000000L
	+#define OPENSSL_VERSION_NUMBER 0x1000107fL
	 #define OPENSSL_VERSION_TEXT   LIBRESSL_VERSION_TEXT
	 #define OPENSSL_VERSION_PTEXT  " part of " OPENSSL_VERSION_TEXT
 
This patch locks the OpenSSL version that is exposed to software to 1.0.1g in line with the forking of LibreSSL from OpenSSL.

This version modification was added to LibreSSL by the original maintainer to circumvent the issues that would arise if ports check OPENSSL_VERSION_NUMBER as a surrogate to detect features. This is a problematic way of checking for features, how will we **ever** be able to remove features this way!

## Result of exp-run

When replacing OpenSSL with LibreSSL for HardenedBSD, I decided to do away with this change and see where I'd end up. Interestingly only 12 ports were failing due to these checks. As more and more software starts using features from 1.0.2 and 1.1.0 this may increase but at least the rate of these issues arising will be lower.

| Port |
|:-----|
| dns/bind910 |
| ftp/curl |
| mail/postfix |
| mail/postfix-current |
| net/haproxy-devel |
| net-mgmt/send |
| security/openvpn |
| security/stunnel |
| security/wpa_supplicant |
| security/xca |

A side-effect of this exp-run is that we are detecting ports that do not set or honor `USES= ssl` (which replaces `USE_OPENSSL= yes` since June) in the port's Makefile. This means that they weren't failing when `DEFAULT_VERSIONS+= ssl=libressl-devel` (which replaces `WITH_OPENSSL_PORT= yes` and `OPENSSL_PORT= security/libressl-devel` since June) is set during build of ports but they are failing now because there's no OpenSSL libcrypto/libssl available on the system.

| Port | Problem |
|:-----|:-------:|
| benchmarks/postal         | SSLv3 |
| databases/mongodb32-tools | SSLv3 |
| databases/mongodb32       | SSLv3 |
| devel/tcl-trf             | SHA-0 |
| finance/openhbci          | DES_ |
| mail/emailrelay           | SSLv3 |
| mail/mixmaster            | EGD  |
| mail/libesmtp             | DES  |
| mail/prayer               | SSLv3 EGD |
| misc/smssend              | SSLv3 |
| multimedia/oscam          | SSLv3 |
| net/Sockets               | SSLv3 |
| net/l4ip                  | EGD  |
| net/netatalk              | DES_ |
| net/netatalk3             | DES_ |
| net/ssltunnel-client      | DES_ |
| net-mgmt/snmp++           | DES_ |
| net-p2p/shx               | EGD  |
| security/certificate-transparency | CMS |
| security/distcache        | SSLv3 |
| security/dsniff           | DES_ |
| security/rcracki_mt       | DES_ |
| www/tomcat-native         | SSLv3 |

All in all I created patches for all of these issues. You can find them in [LibreSSL Ports](https://wiki.freebsd.org/LibreSSL/Ports) and [No-SSLv3](https://wiki.freebsd.org/OpenSSL/No-SSLv3).

## Statistics

All in all there are 204 ports with issues most have patches as well. Not sure if I'll ever get around to updating the number of fixes and the number of ports fixed as well, this is becoming increasingly complex to track using a wiki page!

| Problem | Description | Number of ports |
|:--------|:------------|----------------:|
| [SSLv3](https://wiki.freebsd.org/LibreSSL/PatchingPorts#SSLv2.2FSSLv3_method_failures) | SSLv3 methods removed from LibreSSL 2.3 | 85 |
| [EGD](https://wiki.freebsd.org/LibreSSL/PatchingPorts#EGD) | RAND_egd methods removed from LibreSSL | 38 |
| [DES](https://wiki.freebsd.org/LibreSSL/PatchingPorts#Deprecated_des__methods) | deprecated des_ methods (replaced by DES_ methods) | 29 |
| [COMP](https://wiki.freebsd.org/LibreSSL/PatchingPorts#Uses_removed_Compression) | SSL compression removed from LibreSSL| 10 |
| [SHA-0](https://wiki.freebsd.org/LibreSSL/PatchingPorts#SHA-0) | SHA-0 methods removed from LibreSSL 2.3 | 8 |
| [SSLv2](https://wiki.freebsd.org/LibreSSL/PatchingPorts#SSLv2.2FSSLv3_method_failures) | SSLv2 methods removed from LibreSSL | 7 |
| arc4rand | Conflict with FreeBSD/LibreSSL libs | 4 |
| PSK | Pre-Shared Key removed from LibreSSL  | 4 |
| CMS | Deprecated S/MIME methods | 3 |
| [GOST](https://wiki.freebsd.org/LibreSSL/PatchingPorts#GOST_engine) | GOST methods removed | 2 |
| Other | Non categorized | 25 |

The majority of issues is with the removal of SSLv3. This should improve quickly over the coming months as OpenSSL 1.1 gets released which removes SSLv3 in the default build configuration as well.

### Updates

2016-08-16:

 * [LibreSSL as of 2.4 in ports](https://svnweb.freebsd.org/ports?view=revision&revision=420102) no longer has the `OPENSSL_VERSION_NUMBER` patch
 * [ssl in ports' framework was refactored](https://svnweb.freebsd.org/ports?view=revision&revision=416965)
   - `USE_OPENSSL= yes` is replaced with `USES= ssl`
   - `WITH_OPENSSL_PORT must no longer be used`
   - `OPENSSL_PORT= security/libressl-devel` is replaced with `DEFAULT_VERSIONS+= ssl=libressl-devel`

