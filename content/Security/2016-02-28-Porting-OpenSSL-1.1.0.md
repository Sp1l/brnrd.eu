Title: Porting OpenSSL 1.1.0
Tags: OpenSSL, SSL, FreeBSD, Porting
Modified: 2016-02-28 14:04:00
Author: Bernard Spil
Image: /img/OpenSSLFreeBSD.png
Summary: Just for fun I decided to port OpenSSL 1.1.0 pre3 (alpha) for FreeBSD. The process starts out with copying the existing OpenSSL port but I found a lot of room for simplification. The picture is just a quip...

**Disclaimer:** This software is in Alpha and should only be used for testing purposes, do *NOT* use it in productive environments.

TL;DR: It works, download from my GitHub [ports repo](https://https://github.com/Sp1l/ports/tree/master/security/openssl-devel)

# And so it begins

First of all, we have to do a 'repo-copy'	

	:::sh
	cd /usr/ports/security
	svn copy ./openssl ./openssl-devel
	cd openssl-devel

First order of business is to fetch the distribution tarball and create the `distinfo` file. This requires editing of the `Makefile`

	:::make
	PORTVERSION=   1.1.0
	PORTREVISION=	0 # Delete this line
	DISTVERSIONSUFFIX=     -pre3
	PKGNAMESUFFIX= -devel

Now we can fetch the tarball and create the distinfo. Additionally we check that the tarball has not been tampered with (you always do that, right?)

	:::sh
	make makesum
	fetch http://openssl.org/source/openssl-1.1.0-pre3.tar.gz.asc
	gpg --verify openssl-1.1.0-pre3.tar.gz.asc \
	   /usr/ports/distfiles/openssl-1.1.0-pre3/openssl-1.1.0-pre3.tar.gz
	gpg: Signature made Mon Feb 15 19:37:23 2016 CET using RSA key ID 7DF9EE8C
	gpg: Good signature from "Richard Levitte <richard@levitte.org>"
	gpg:                 aka "Richard Levitte <levitte@openssl.org>"

_Hint:_ You can find the keys at the OpenSSL Website under [Community / Team](https://www.openssl.org/community/team.html)

# Patching

Now try to apply the patches that are in the files dir. This version changes a lot, many patches no longer apply or the source-file patched simply no longer exists. These we have to `svn rm`.

	:::sh
	make extract
	cd `make -V WRKSRC`
	patch < ../../files/patch-...
	# Figure out what source-files no longer exist, delete these patches
	svn rm files/patch-{RFC-5705,md5.c,openbsd__hw.c,srtp.h,testssl}
	# test all patches one at a time to figure out which ones no longer apply
	# then remove these patches
	svn rm files/patch-{Configure,Makefile}

I'll still have to go through all of the original patches in detail.

Some of the additional commands in the Makefile also failed and have been removed (or the file renamed where applicable).

# Makefile cleanup / options-ify

Looking at the Makefile I had the impression that a lot could be made simpler.

With the change below the Makefile has been reduced from 244 to 171 lines.

## Order, standards

All descriptions were defined using
`<OPT>_DESC?= some description`	
which is not standard. Replace `?=` with a `=`

All OPTIONS should be kept together in a block as much as possible.	
Rearrange the descriptions to directly follow the other OPTIONS_* definitions

OPTIONS should be sorted alphabetically.

## Grouping options

I see 4 groups in the options; ciphers, hashes, optimizations and protocols so add these as groups.

	:::make
	OPTIONS_GROUP=  CIPHERS HASHES OPTIMS PROTOS
	OPTIONS_GROUP_CIPHERS=  JPAKE RC2 RC4 RC5 DES
	OPTIONS_GROUP_HASHES=   MD2 MD4
	OPTIONS_GROUP_OPTIMS=   ASM I386 SSE2 SSL3
	OPTIONS_GROUP_PROTOS=   SCTP SSL3
	CIPHERS_DESC=   Cipher suites
	HASHES_DESC=    Cryptographic Hash Functions
	OPTIMS_DESC=    Optimizations
	PROTOS_DESC=    Cryptographic protocols

This makes for a more structured and appealing `make config` dialog

## Use the new OPTIONS framework fully

There was a lot of repitition in the Makefile in the for of

	:::make
	.if ${PORT_OPTIONS:MSCTP}
	EXTRACONFIGURE+=       sctp
	.else
	EXTRACONFIGURE+=       no-sctp
	.endif

These could mostly be rolled up to a small definitions block

	:::make
	.for _option in asm md2 md4 rc5 rfc3779 sctp sse2 ssl3 threads
	${_option:tu}_CONFIGURE_ON=    enable-${_option}
	${_option:tu}_CONFIGURE_OFF=   no-${_option}
	.endfor
	EC_CONFIGURE_ON+=      enable-ec_nistp_64_gcc_128
	EC_CONFIGURE_OFF+=     no-ec_nistp_64_gcc_128
	SSL3_CONFIGURE_OFF+=           no-ssl3-method

There was a `zlib-dynamic` option as well but the build tools now handle that correctly, i.e. if zlib is disabled, zlib-dynamic is also disabled.	
Not all options could be dealt with using that `for` loop, so these are added afterwards. This creates a problem though, all these configure arguments are now prefixed with `--` so we need to fix that when invoking the (non-standard) configure script. 

	:::make
	do-configure:
		./config --prefix=${PREFIX} --openssldir=${OPENSSLDIR} \
			-L${PREFIX}/lib ${CONFIGURE_ARGS:C/--(no|enable)/\1/g}

## Saner defaults

With OpenSSL 1.1.0 a lot of things are now disabled by default. The ["Perl Entropy Gathering Daemon"](https://github.com/openssl/openssl/issues/296) being one of them.

OpenSSL supports a **lot** of ciphers, hashes and protocols and some are very outdated, I've therefore disabled a number of them by default. In daily use you should not want to use these. There's a nice 

| Feature | Reason |
|:---|:---|
| IDEA cipher | weak |
| MD2 hash   | unsafe |
| MD4 hash   | unsafe |
| MD_GHOST94 | obscure |
| RC2 cipher | unsafe |
| RC4 cipher | unsafe |
| SSLv3 protocol | deprecated |

## Result

![openssl-devel options]({static}/img/OpenSSL-devel-config.png)

# Bugs

There must be more! Do let me know if anything's amiss with the port via mail, GitHub or Twitter.

## Next Protocol Negotiation Protocol

This wasn't fully implemented.	
First and foremost the flag `OPENSSL_NO_NEXTPROTONEG` wasn't generated by the `util/mk1mf.pl` script where all other `OPENSSL_NO_*` flags were defined there.	
Then `ssl/t1_ext.c` and `apps/s_client.c` failed to build due to missing #ifndef OPENSSL_NO_NEXTPROTONEG guards.

Fixed this and upstreamed the patch ["Fix incomplete no-nextprotoneg option"](https://github.com/openssl/openssl/pull/757). This patch is in the port as `files/patch-nextprotoneg`.
