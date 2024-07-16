Title: The sorry state of IT security and operations
Tags: OpenSSL, SSL, LibreSSL
Modified: 2016-02-28 14:04:00
Author: Bernard Spil
Image: /img/OpenSSL_DROWN.png
Summary: Something good happened for IT security, OpenSSL disabled SSLv2 by default in the latest release 1.0.2g. And then, projects started switching it back on... WHY!?!

With the release of the latest set of vulnerabilities for OpenSSL the project also released new versions 1.0.1s and 1.0.2g. For those of you still running older versions like 1.0.0 or even 0.9.8 (please tell me you're not using 0.9.7!) you can only hope that the vendor of the product you use releases fixes.

Again some of the vulnerabilities relate to old and known to be insecure features are available in the library. These were SSLv2 and export ciphers which date back to the previous crypto-wars.

# What changed

The interesting thing with the releases, apart from the vulnerabilities that were fixed, is that it now builds [without SSLv2](https://github.com/openssl/openssl/commit/9dfd2be8a1761fffd152a92d8f1b356ad667eea7) support. In the past you had to disable SSLv2 in your configuration to not use it, but now you **can't** use it.

The change is in the completely custom Configure script of OpenSSL

	:::perl
	my %disabled = ( # "what"         => "comment" [or special keyword "experimental"]
		 "ec_nistp_64_gcc_128" => "default",
		 "gmp"		  => "default",
		 "jpake"          => "experimental",
		 "md2"            => "default",
		 "rc5"            => "default",
		 "rfc3779"	  => "default",
		 "sctp"           => "default",
		 "shared"         => "default",
		 "ssl2"           => "default",
		 "store"	  => "experimental",
		 "unit-test"	  => "default",
		 "zlib"           => "default",
		 "zlib-dynamic"   => "default"
	       );

The line containing `"ssl2"` was added in this release to the "disabled" array of options. You could say that this is no big deal, everyone already disabled SSLv2 long ago. In addition, EGD (The Perl Entropy Gathering Daemon) support is now disabled by default, which is also a good thing. No system from the past 10 years needs EGD as source of entropy (randomness).

# What happens

So what actually happens if you build your OpenSSL with the default configuration?

What happens is that the flag `OPENSSL_NO_SSL2` is defined

	#define OPENSSL_NO_SSL2

Then in the code you find blocks that start with `#ifndef OPENSSL_NO_SSL2`

	:::c
	# ifndef OPENSSL_NO_SSL2
	const SSL_METHOD *SSLv2_method(void); /* SSLv2 */
	const SSL_METHOD *SSLv2_server_method(void); /* SSLv2 */
	const SSL_METHOD *SSLv2_client_method(void); /* SSLv2 */
	# endif

Which actually hides the code that follows completely. In the blocks of code that are disabled like that are also the method definitions.

# Impact

Before this change the shared libraries (`libssl.so`) still contained the SSLv2 methods mentioned above.	
After this change, these methods are gone and this leads to errors when starting applications as they can't find the methods required in the shared library.

It is good practice to change the shared library version if anything changes. The library mentioned earlier is usually `libssl.so.8` and `libssl.so` just refers to that. With a change like this (removing or adding methods or structures) the major library vesion is increased, with bug fixes a minor version is increased.

So we now have many broken programs on systems simply because they refer to these removed methods even if they're not actually used. The knee-jerk reaction of all projects is to switch SSLv2 on again by adding `enable-ssl2` to their configuration when building the OpenSSL package.

# The sorry state

Effectively we've boxed ourselves in. We can't remove these known-to-be-insecure features because programs that haven't been re-compiled will break. Some software will fail to build altogether because the developers have not implemented `OPENSSL_NO_SSL2` checks so they won't build.

And the sad thing is that OpenSSL 1.1.0 doesn't really help here either. For compatibility's sake it has exactly the same shared library version number `.8` even though it comes with a lot of added methods and structures for newer cryptographic algoritms.

The same basically goes for EGD, noone needs it any longer, but it's still there lurking in the background and who knows Perhaps attackers find a way to abuse it and compromise your systems with it!

There's a lot of other features in OpenSSL as well that should already be long gone but they live on, forever?

# The alternative

I've been working hard and long on making all software packages work on FreeBSD with an alternative OpenSSL library from [OpenBSD](http://openbsd.org) which is called [LibreSSL](http://libressl.org).

LibreSSL removed a lot of these unsafe and questionable features more than 2 years ago, and about a year ago it already removed SSLv3. With every change in the ABI the shared library version is increased (currently at `.38`).

A **lot** of time was spent modifying software code to make it work without all these unsafe and questionable feature whilst maintaining compatibility with the original OpenSSL libraries and features.

# Have your cake and eat it!

**Now** is the time to switch to using LibreSSL. You'd be in good company, [VOID Linux](http://voidlinux.eu), [OpenELEC](http://openelec.tv) and [PC-BSD](http://pcbsd.org) use LibreSSL already, [Alpine Linux](http://alpinelinux.org/) will be joining soon.

![Operating systems using LibreSSL]({static}/img/AlpineVoidPCBSD.png)

The greatest compliment I've received from the projects using the patches I created was when I asked what his experience was with the switch to LibreSSL and the response was "uneventful". There's proof for you that it isn't all that difficult to switch!

All the patches that you need for [removing SSLv3](https://wiki.freebsd.org/OpenSSL/No-SSLv3) and [supporting LibreSSL](https://wiki.freebsd.org/LibreSSL/Ports) are sitting there waiting for you to start using them.



