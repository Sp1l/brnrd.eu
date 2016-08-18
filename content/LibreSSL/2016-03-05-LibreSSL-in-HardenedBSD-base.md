Title: LibreSSL in HardenedBSD base Part I
Tags: SSL, LibreSSL, OpenSSL, HardenedBSD
Created: 2016-03-05
Modified: 2016-03-05 19:51:00
Author: Bernard Spil
Image: /img/HardenedBSDLibreSSL.png
Summary: With last week's OpenSSL vulnerabilities questions came up when LibreSSL would replace OpenSSL in FreeBSD base. This was picked up by the HardenedBSD developers and they asked me if I'd be interested in adding LibreSSL as alternative libcrypto/ssl in HardenedBSD. Well SURE I do! This post describes the early stages of this project.

It seemed to be a way bigger thing than I thought, after the [HardenedBSD announcement](https://hardenedbsd.org/article/op/2016-02-28/new-project-member-bernard-spil-sp1l) I got congratulations from many places. I can only see that as endorsement to make it happen!

**The challenge**

 1. Add [LibreSSL](http://libressl.org) as alternative provider of libcrypto and libssl in [HardenedBSD](http://hardenedbsd.org)
 2. Allow selecting LibreSSL _or_ OpenSSL using `/etc/src.conf`

# And so it begins

After setting up a VM with HardenedBSD 42 (based on FreeBSD 11) I branched the HardenedBSD playground source repository into `hardened/current/libressl`.

This branch I cloned to my HardenedBSD VM in `/usr/src` and is the starting point for the changes. I ran a full `make buildworld` to have a populated `/usr/obj` tree that I can hack on.

Then I added LibreSSL 2.3.2 (latest snapshot release for the upcoming OpenBSD 5.9) to the mix by extracting it into `/usr/src/crypto/libressl` (notice the nice relic from the previous [Crypto Wars](https://en.wikipedia.org/wiki/Crypto_Wars) here, putting all crypto sources in a separate path makes it easier to distribute without the strong crypto).

By default LibreSSL portable builds with Cmake but that's not an option for the base system, so I added the latest `Makefile` from OpenBSD to the repository in `/usr/src/secure/lib/libcrypto` and `/usr/src/secure/lib/libcrypto`.

# Beginner mistakes

I dove straight into `/usr/src/share/Mk` to edit files that were relevant to OpenSSL building. I started adding WITH_LIBRESSL and adding conditionals to disable OpenSSL when LibreSSL is selected. There's a big mistake in that aproach! The base system's Makefile's are littered with

	:::make
	.if ${MK_OPENSSL} == "no"
	disabled code
	.endif

My approach would set `WITHOUT_OPENSSL` and additionally set `MK_OPENSSL=no` effectively disabling OpenSSL, and that's **NOT** what we want!

The behaviour that is requested to leave the MK_OPENSSL knob function as is, and only alter the libraries that are used. To do so we should only want *one* knob to drive the behaviour of base. This is the magic knob in `/etc/src.conf`

	:::make
	WITH_LIBRESSL=	yes

That is all it should take to build with LibreSSL and without OpenSSL. Going forward, some more bits will have to be added.

 1. setting `WITHOUT_OPENSSL= yes` should still work as it does currently (although it [is broken](http://bsdxbsdx.blogspot.nl/2015/04/build-packages-in-poudriere-without.html))
 2. setting `WITH_LIBRESSL= yes` and `WITHOUT_OPENSSL= yes` should build LibreSSL and not OpenSSL but NOT set `MK_OPENSSL= no`
 3. setting `WITH_LIBRESSL= yes` should behave as option 2.

Don't try the modified `WITHOUT_OPENSSL` behaviour just yet, it's not implemented!

# Pick and choose

The LibreSSL tarball includes additional code that is in OpenBSD base but not found on other operating systems. We will need to add some of these to the build. This is where the port helps out, it uses Cmake to detect what needs to be added. Using `cmake -LAH` to generate `CMakeCache.txt` I get the following missing features

	:::sh
	$ grep '^HAVE.*=$' CMakeCache.txt
	HAVE_EXPLICIT_BZERO:INTERNAL=
	HAVE_GETAUXVAL:INTERNAL=
	HAVE_GETENTROPY:INTERNAL=
	HAVE_REALLOCARRAY:INTERNAL=
	HAVE_TIMINGSAFE_BCMP:INTERNAL=
	HAVE_TIMINGSAFE_MEMCMP:INTERNAL=

We will have to add these to the makefile to allow LibreSSL to build.

# libcrypto

When building LibreSSL (and OpenSSL as well), it will first build `libcrypto` and then `libssl` as the latter requires the former to build. So we start hacking in `/usr/src/secure/lib/libcrypto`

	:::make
	# $FreeBSD$
	
	.if !"${WITH_LIBRESSL}" == "yes"
	
	# content of the original Makefile

	.else
	.include "Makefile.libressl"
	.endif # ${MK_OPENSSL} != "no"

This isn't the cleanest way to do it, but makes merging changes from FreeBSD later on a lot easier. If `WITH_LIBRESSL` is defined, we simply jump to the modified copy of OpenBSD's Makefile which I named `Makefile.libressl`

The Makefile is largely OK but we need to add the compatibilty code from OpenBSD and set the paths correctly for `make` to find the source files. The file `crypto/CMakeLists.txt` is very helpful here.

The relevant changes from `Makefile.libressl`

	:::make
	SHLIB_MAJOR=    38
	OPENSSL_VER=    2.3.2
	OPENSSL_DATE=   2016-01-28

	LIBRESSL_SRC=   ${.CURDIR}/../../../crypto/libressl
	SSL_SRC=        ${LIBRESSL_SRC}/ssl
	LCRYPTO_SRC=    ${LIBRESSL_SRC}/crypto

	CFLAGS+= -I${LIBRESSL_SRC}/include -I${LIBRESSL_SRC}/include/compat
	CFLAGS+= -I${SSL_SRC}
	CFLAGS+= -I${LCRYPTO_SRC}
	CFLAGS+= -I${LCRYPTO_SRC}/modes -I${LCRYPTO_SRC}/asn1 -I${LCRYPTO_SRC}/evp

	# compat/
	SRCS+=  explicit_bzero.c getentropy_freebsd.c reallocarray.c \
	        timingsafe_bcmp.c timingsafe_memcmp.c

	explicit_bzero.c:
	        CFLAGS+= -O0

And see there! It builds!

# libssl

The modification to the default `secure/lib/libssl/Makefile` is done exactly like the `libcrypto` modification.

Again, very little change was required to make this work. Basically modifying the paths is all that was required to build libssl.

The relevant changes in `Makefile.libressl`

	:::make
	SHLIB_MAJOR=    38

	LIBRESSL_SRC=   ${.CURDIR}/../../../crypto/libressl
	LSSL_SRC=        ${LIBRESSL_SRC}/ssl

	.include <bsd.own.mk>
	CFLAGS+= -Wall -Wundef
	CFLAGS+= -DLIBRESSL_INTERNAL
	CFLAGS+= -I${LIBRESSL_SRC}/include -I${LIBRESSL_SRC}/include/compat
	CFLAGS+= -I${SSL_SRC}
	CFLAGS+= -I${LIBRESSL_SRC}/crypto -I${LIBRESSL_SRC}/crypto/evp

	LIBADD= crypto

	.PATH:  ${LSSL_SRC}

With these changes, libssl builds without problem.

# OpenSSL (the executable)

Again, the modification to the default `secure/usr.bin/openssl/Makefile` is done exactly like the `libcrypto` modification.

The `Makefile` as imported from OpenBSD required very little modification to work.

## One more thing...

This build was just a bit of hacking. Linking `openssl` failed, and a bit of digging showed that libssl was incorrectly linked as well, it linked `libssl.so.8`. This is due to the way I was building and linking. To solve I dropped into the /usr/obj tree and linked libssl and openssl separately using the commmands from the build logs of libssl and openssl.

	:::sh
	cd /usr/obj/usr/src/secure/lib/libssl
	cc  ... bs_cbs.So | tsort -q` -lcrypto -L../libcrypto
	cd /usr/src/secure/lib/libssl
	make

	cd /usr/obj/usr/src/secure/usr.bin/openssl
	cc ... x509.o   -lssl  -lcrypto -L../../lib/libcrypto -L../../lib/libssl
	cd /usr/src/secure/usr.bin/openssl
	make
	
Checks with `readelf -d` show that libssl and openssl now link correctly!

# Install & verify

Now we can install libcrypto, libssl and openssl

	:::sh
	cd /usr/src/secure/lib/libcrypto
	make install
	cd /usr/src/secure/lib/libssl
	make install
	cd /usr/src/secure/usr.bin/openssl
	make install
	
And voilá we have a working LibreSSL in base!

	:::sh
	which openssl
	/usr/bin/openssl

	openssl version
	LibreSSL 2.3.2

	readelf -d /usr/bin/openssl
	Dynamic section at offset 0x67028 contains 23 entries:
	  Tag                Type    Name/Value
	 0x0000000000000001 NEEDED Shared library: [libssl.so.38]
	 0x0000000000000001 NEEDED Shared library: [libcrypto.so.38]
	 0x0000000000000001 NEEDED Shared library: [libc.so.7]
		
# Conluding

So far so good! Building is only half of the work, the proof of the pudding is in the eating.

Next up: 

 1. Building world with LibreSSL
 2. Add assembly optimizations
 3. Polish code
 4. Add `libtls` and LibreSSL's TLS-capable `nc`

