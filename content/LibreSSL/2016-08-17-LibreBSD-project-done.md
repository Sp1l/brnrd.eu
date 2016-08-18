Title: LibreBSD project "done"
Tags: LibreSSL, FreeBSD, HardenedBSD, TrueOS
Created: 2016-08-17
Author: Bernard Spil
Image: /img/LibreBSD.png
Summary: Today I realized that I had actually fixed all outstanding tasks I had for "LibreBSD". It is likely be the default SSL library provider for HardenedBSD and TrueOS in the very near future.

Today I fixed the last of the things that needed to be improved to make LibreSSL really a drop-in replacement for FreeBSD's libcrypto and libssl. These were mostly cosmetic but still important enough

  1. Delete Non-LibreSSL libs, headers, man-pages etc with `make delete-old`
  2. Add WITH_LIBRESSL and WITHOUT_LIBRESSL descriptions for `man(8) src.conf`
  3. Install libcrypto in the same location as for OpenSSL.

Even though the solutions were ultimately very simple, they eluded me for a while. I'll explain more towards the bottom of this post. Let's first go into how you can use LibreSSL in your FreeBSD base system and do without OpenSSL altogether.

# Switching to LibreSSL

There are several methods

  1. Build your own
  2. Use HardenedBSD (and the additional security features)
  3. Use TrueOS Desktop (formerly PC-BSD)

Both HardenedBSD and TrueOS supply binary distributions with LibreSSL in base.

## HardenedBSD

The HardenedBSD project allows you to switch to LibreSSL in base and also has a
package repo with packages linked against the libcrypto/libssl libraries in base.

To use, install HardenedBSD as you would normally do and then add the following
to /etc/hbsd-update.conf

   :::

and add to the pkg configuration

   :::

## TrueOS Desktop

The PC-BSD project has been providing packages that use LibreSSL for over a year
now. As of 11.0-RC1 PC-BSD has renamed itself to TrueOS Desktop and uses
LibreSSL in base.

## Build your own

# Last mile

For a short explanation of the remaining problems that were fixed.

## Obsolete files

FreeBSD has a file `ObsoleteFiles.inc` that lists all files that were removed
between your current version and all previous release versions. As LibreSSL
is not a default feature but configurable, it is not proper to use this but
ultimately I've discovered `tools/build/mk/OptionalObsoleteFiles.inc` which
does exactly what I want.

Then all that was lacking was figuring out what needs deletion. As OpenSSL
installs ca. 3000 man-page files (and symlinks). Fortunately, all the man-pages
are listed in the `Makefile.man` and `Makefile.man.libressl` files in the
`secure/lib/libcrypto` directory.

Then all that's required is add the OpenSSL libraries and headers to the
list of obsolete files.

## WITH_/WITHOUT_LIBRESSL in man src.conf

Actually stumbled on this whilst working on the Obsolete Files.

Added 2 files to `tools/build/options`

  * `WITH_LIBRESSL`
  * `WITHOUT_LIBRESSL`

containing a one-liner describing what the feature does

    Set to build LibreSSL as libcrypto/libssl provider as replacement of the OpenSSL equivalents.

## Install location of libcrypto

For reasons unknown to me, `libcrypto.so.38` installed into `/usr/lib` where on
a vanilla system it installs in `/lib`. I had copied the line that would make
it install in `/lib` yet it didn't actually do so!

    :::make
    SHLIBDIR?=	/lib

So **why** would it not be set correctly? Sometimes it just takes a bit of time,
you look at the problem again (after Bryan Drewery points out that it *is* that
that is what sets it. So what was biting me? This is the original

    :::make
    SHLIBDIR?=	/lib
    
    .include <bsd.own.mk>

and this the same for LibreSSL

    :::make
    .include <src.opts.mk>
    
    SHLIBDIR?=	/lib

Suddenly it dawned on me, `src.opts.mk` already defines `SHLIBDIR` so the
subsequent `?=` doesn't stick. So the simple solution is

    :::make
    SHLIBDIR?=   /lib
    
    .include <src.opts.mk>

*First* set the `SHLIBDIR` and then include `src.opts.mk`, problem solved!
