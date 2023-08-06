Title: Modernizing the OpenSSL port
Tags: OpenSSL, SSL, FreeBSD, Porting
Modified: 2016-10-02
Author: Bernard Spil
Image: /img/OpenSSLFreeBSD.png
Summary: During the last EuroBSDCon in Belgrade I took maintainership of the OpenSSL port in FreeBSD. At the same time there were OpenSSL releases fixing vulnerabilities and emergency fixes for regressions introduced. The port had not been updated to recent ports framework and I wanted to get it in line with latest porting techniques.

# Introduction

The FreeBSD Ports framework has changed quite a bit over the past couple of years. Most changes make it easier to create ports as well as make them more readable.

All in all reworking the port reduced the number of lines by about a third. I've blogged about this before when creating the [OpenSSL-devel port for 1.1.0](/2016-02-28/porting-openssl-110.html).

# OPTIONS_NG

The `OPTIONS` support in ports is pretty slick. It has been named OPTIONS_NG and is documented well in the [Porter's Handbook](https://www.freebsd.org/doc/en/books/porters-handbook/makefile-options.html).

## Options-helpers

One of the main benefits is that repetitive constructs have been simplified. Where before you'd have

	:::make
	.if ${PORT_OPTIONS:MFOO}
	CONFIGURE_ARGS+=	--enable-foo
	.endif

you can now do that in a single line

	:::make
	FOO_CONFIGURE_ENABLE=	foo

which is a lot simpler. There's a complication in OpenSSL though, it doesn't use autoconf et. al. to configure the build but uses its own Perl Configure script. Autoconf uses `--with-foo`/`--without-foo` and `--enable-bar`/`--no-bar` for feature enabling/disabling but this doesn't always work. Luckily there's also the `FOO_CONFIGURE_ON= foo`/`FOO_CONFIGURE_OFF= no-foo` that we can use to work around the quirkyness of OpenSSL's `Configure`.

Basically OpenSSL comes with a default configuration and you need to only provide an extra option if you want the opposite of the default. Almost of the former `.if ${PORT_OPTIONS:MFOO}` blocks have been reworked into the options helpers. I've made some explicit (i.e. even add default options) to not get hit by changing options in coming releases.

	:::make
	ASM_CONFIGURE_OFF=	no-asm
	EC_CONFIGURE_ON=	enable-ec_nistp_64_gcc_128
	EC_CONFIGURE_OFF=	no-ec_nistp_64_gcc_128
	I386_CONFIGURE_ON=	386
	MD2_CONFIGURE_ON=	enable-md2
	MD2_CONFIGURE_OFF=	no-md2
	PADLOCK_PATCH_SITES=	http://git.alpinelinux.org/cgit/aports/plain/main/openssl/:padlock
	PADLOCK_PATCHFILES=	1001-crypto-hmac-support-EVP_MD_CTX_FLAG_ONESHOT-and-set-.patch:padlock \
				1002-backport-changes-from-upstream-padlock-module.patch:padlock \
				1003-engines-e_padlock-implement-sha1-sha224-sha256-accel.patch:padlock \
				1004-crypto-engine-autoload-padlock-dynamic-engine.patch:padlock
	PADLOCK_VARS=		PATCH_DIST_STRIP=-p1
	RC5_CONFIGURE_ON=	enable-rc5
	RC5_CONFIGURE_OFF=	no-rc5
	RFC3779_CONFIGURE_ON=	enable-rfc3779
	RFC3779_CONFIGURE_OFF=	no-rfc3779
	SCTP_CONFIGURE_ON=	sctp
	SCTP_CONFIGURE_OFF=	no-sctp
	SHARED_CONFIGURE_ON=	shared
	SHARED_MAKE_ENV=	SHLIBVER=${OPENSSL_SHLIBVER}
	SHARED_PLIST_SUB=	SHLIBVER=${OPENSSL_SHLIBVER}
	SHARED_USE=		ldconfig
	SSE2_CONFIGURE_OFF=	no-sse2
	SSL2_CONFIGURE_ON=	enable-ssl2
	SSL2_CONFIGURE_OFF=	no-ssl2
	SSL3_CONFIGURE_ON=	enable-ssl3
	SSL3_CONFIGURE_OFF=	no-ssl3 no-ssl3-method
	THREADS_CONFIGURE_ON=	threads
	THREADS_CONFIGURE_OFF=	no-threads
	ZLIB_CONFIGURE_ON=	zlib zlib-dynamic
	ZLIB_CONFIGURE_OFF=	no-zlib no-zlib-dynamic

## Order, standards

Most descriptions were defined using	
`<OPT>_DESC?= some description`	
which is not standard. Replace `?=` with a `=`

All OPTIONS should be kept together in a block as much as possible.	
Rearrange the descriptions to directly follow the other OPTIONS_* definitions

OPTIONS should be sorted alphabetically.

## Grouping options

I see 4 groups in the options; ciphers, hashes, optimizations and protocols so add these as groups.

	:::make
	OPTIONS_GROUP=	CIPHERS HASHES OPTIMIZE PROTOCOLS
	OPTIONS_GROUP_CIPHERS=	JPAKE RC2 RC4 RC5 DES
	OPTIONS_GROUP_HASHES=	MD2 MD4
	OPTIONS_GROUP_OPTIMS=	ASM I386 SSE2 SSL3
	OPTIONS_GROUP_PROTOS=	SCTP SSL3
	CIPHERS_DESC=	Cipher suites
	HASHES_DESC=	Cryptographic Hash Functions
	OPTIMIZE_DESC=	Optimizations
	PROTOCOLS_DESC=	Cryptographic protocols

This makes for a more structured and appealing `make config` dialog

# Other changes

There were some more things in the port's Makefile that I wanted check. A short description follows.

## MAKE_JOBS_UNSAFE

Back in 2009 the knob `MAKE_JOBS_UNSAFE` was defined for the OpenSSL port. I've not experienced issues in any of the builds I've done so it is removed now.

## Shared libs conflicting with base

In 2006 a check was added to see if the base system had a higher SHLIBVER than the port which then resulted in a message and stopped building. This was at a time when there were still knobs for the port like `WITH_OPENSSL_BETA`, `WITH_OPENSSL_097` and `WITH_OPENSSL_SNAPSHOT` that would result in different versions to be built and installed.

I currently can see no scenario in which this check would be valid. If at any point base (-CURRENT) has a newer version of OpenSSL than ports we can still add this check back in.

## PORTVERSION

Last week I modified the PORTVERSION to no longer use the PORTREVISION suffix but to use the uptream version character(s). This also removes the need to set the CPE_VERSION as the default is OK.

## MAN3 option

When you disabled MAN3 you'd still be generating all the section 3 manpages but they would be deleted shortly after. That was a waste of time and resources so this has now been changed to delete the .pod files after patching so we save ca. 3000 perl invocations.
