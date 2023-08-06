Title: Your private git server in a chroot
Tags: FreeBSD, git
Modified: 2023-08-06
Author: Bernard Spil
Image: /img/git-chroot.jpg
Summary: Wanted to have a personal, self-hosted git service (ssh-only) that I can use without worrying about keys stored in the repo. Add some (not so fancy) separation using chroot so we can determine the repo paths.

# git server in `chroot`

The objective is 

1. to have a personal, self-hosted git service
2. that I can access via ssh
3. and does not expose my whole system

The [official documentation](https://git-scm.com/book/en/v2/Git-on-the-Server-Setting-Up-the-Server) from git was helpful, as is the [sshd_config](https://man.openbsd.org/sshd_config) manual page.

The rest of this guide assumes you work in a single shell and have `GIT_USER` and `GIT_ROOT` variables exported in your shell.

## Create a separate `git` user

You *can* use the regular `git` user, but this makes it more difficult to separate this from attacks in your logs. For simplicity, we'll use `git` as the user here and use `/var/git` as storage location for the repositories.

```sh
export GIT_USER=git
export GIT_ROOT=/var/git
pw user add ${GIT_USER} -c 'git server' -d ${GIT_ROOT} -s /usr/local/bin/git-shell
```

and create the home directory **owned by root, not writable by group/other**

```sh
install -d -o root -m 755 ${GIT_ROOT}
```

## Create the chroot environment

This is somewhat more involved, several steps. There was some bit of trial-and-error getting to a working chroot, bear with me.

### Directory layout

Create the required directories

```sh
mkdir ${GIT_ROOT}/bin
mkdir ${GIT_ROOT}/dev
mkdir ${GIT_ROOT}/lib
mkdir -p ${GIT_ROOT}/var/run
mkdir -p ${GIT_ROOT}/usr/local/bin
mkdir ${GIT_ROOT}/usr/local/lib
```

### Determine required libraries and copy

You will need 2 binaries, and the libraries these depend on, in the chroot

1. `git`
2. `git-shell`

So we copy them to the chroot

```sh
cp -p /usr/local/bin/git /usr/local/bin/git-shell ${GIT_ROOT}/usr/local/bin 
```

On FreeBSD these will live in `/usr/local/bin`. To determine what libraries you need, use `readelf -d` or `ldd` on the binaries.

```sh
$ ldd /usr/local/bin/git
/usr/local/bin/git:
        libpcre2-8.so.0 => /usr/local/lib/libpcre2-8.so.0 (0x2ab8bbbb8000)
        libz.so.6 => /lib/libz.so.6 (0x2ab8bccfe000)
        libthr.so.3 => /lib/libthr.so.3 (0x2ab8bc58d000)
        libc.so.7 => /lib/libc.so.7 (0x2ab8bd69b000)
        [vdso] (0x7fffffffe000)
```

**NOTE**: dependencies for `git-shell` are the same as for `git` on my system...
Copy these over to the respective location in the chroot:

```sh
for file in ldd /usr/local/bin/git | sed -nE 's^.* => ([^ ]+) .*$^\1^p'; do
    cp -pv $file ${GIT_ROOT}${file}
done
```

### Other chroot nits

You'll need the run-time link-editor in the chroot

```sh
cp -p /libexec/ld-elf.so.1 ${GIT_ROOT}/libexec/
```

Got an error on missing `/dev/null`, solved by

```sh
cp -p /dev/null ${GIT_ROOT}/dev/null
```

The runtime linker needs to be able to find all libraries, we can fix this

```sh
ldconfig -f ${GIT_ROOT}/var/run/ld-elf.so.hints /lib /usr/lib /usr/lib/compat /usr/local/lib
```

### Test that the chroot works

Verify that you get the git version returned

```sh
$ chroot -u ${GIT_USER} ${GIT_ROOT} /usr/local/bin/git -v
git version 2.41.0
```

### All together now

In a single script:

```sh
# Set variables
export GIT_USER=git
export GIT_ROOT=/var/git

# Create user and home-dir
pw user add ${GIT_USER} -c 'git server' -d ${GIT_ROOT} -s /usr/local/bin/git-shell
install -d -o root -m 755 ${GIT_ROOT}

# Create directory layout
mkdir ${GIT_ROOT}/bin
mkdir ${GIT_ROOT}/dev
mkdir ${GIT_ROOT}/lib
mkdir ${GIT_ROOT}/libexec
mkdir -p ${GIT_ROOT}/var/run
mkdir -p ${GIT_ROOT}/usr/local/bin
mkdir ${GIT_ROOT}/usr/local/lib

# Copy binaries and required shared libraries to chroot
cp -p /usr/local/bin/git /usr/local/bin/git-shell ${GIT_ROOT}/usr/local/bin 
for file in $(ldd /usr/local/bin/git | sed -nE 's^.* => ([^ ]+) .*$^\1^p'); do
    cp -pv $file ${GIT_ROOT}${file}
done

# Copy and configure the runtime linker
cp -p /libexec/ld-elf.so.1 ${GIT_ROOT}/libexec/
ldconfig -f ${GIT_ROOT}/var/run/ld-elf.so.hints /lib /usr/local/lib

# Make sure we have `null` device
cp -p /dev/null ${GIT_ROOT}/dev/null
```

## Add the configuration to OpenSSH

We'll store the authorized keys in the ssh config dir rather than in the `git` user's home-dir. I'm assuming you don't allow password auth, key only (`PasswordAuthtentication no` and `KbdInteractiveAuthentication no`).

```ssh
Match User git
        ChrootDirectory /var/git
        DisableForwarding yes
        # PasswordAuthentication no # Set global
        AuthorizedKeysFile /etc/ssh/authorized_keys/git
        ForceCommand /usr/local/bin/git-shell
```

Add any ssh keys that require access to the git repositories to the file `/etc/ssh/authorized_keys/git` (can be root-owned, not readable for anything but root). 


Test your config for errors and restart the ssh server after modifying the config.

```sh
sshd -t && service sshd restart
```

Keep your session open, and create a parallel session to make sure ssh still works. Already open sessions are not closed by a restart!

## Create your first repository

Create the "bare" repo on your git server

```sh
install -d -o ${GIT_USER} ${GIT_ROOT}/repo1
chroot -u ${GIT_USER} ${GIT_ROOT} /usr/local/bin/git init --bare /repo1
```

Push content to your personal git server

```sh
cd myproject
git init
git add .
git commit -m 'Initial commit'
git remote add origin git@example.org:/repo1
git push origin master
```