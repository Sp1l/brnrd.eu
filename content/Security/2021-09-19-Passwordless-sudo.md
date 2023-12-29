Title: Secure sudo without password
Tags: Network SSH
Category: Security
Created: 2021-09-19
Modified: 2023-12-29
Author: Bernard Spil
Image: /img/Sudo-ssh-agent.png
Summary: Secure usage of sudo without passwords 

# Passwordless `sudo` configuration

```conf
ALL=(ALL) NOPASSWD:ALL
```

seems to be the Out-of-the-Box configuration on most Linux systems. Whilst
this could be useful when installing, this should be removed shortly after.
Combined with SSH password login (in stead of key-based) this quickly is
a very short path to root: effectively, username + password is root.

Let's **not** go into the password hygiene topic here.

Let's see if we can make this safe _and_ simple.

**NOTE**: If any other user can read other user's files or sockets, they
can also gain access to other user's SSH agent context.

## NOPASSWD

Many systems are configured with `NOPASSWD` in sudo. This is poor security,
all an attacker needs is the context of the user. You'd do well to remove
all `NOPASSWD:` strings from your sudo configuration (use `sudo visudo` and
don't forget `sudoers.d/*`!)

Make sure you set sufficiently random passwords for all users, or use the
ssh-agent method described below.
You're already using keys to authenticate in SSH, right?!?

By default sudo will cache the password for 5 minutes. Any sudo command
resets the timer to 5 minutes. To adjust, configure via `sudo visudo`

```conf
Defaults       timestamp_timeout=5
```

## Get rid of password questions

You can use your ssh-agent / pageant on your client instead of using a
password for using sudo.

### Server config

Ubuntu seems to fail on DSA keys (prefix `ssh-dss` in `authorized_keys`).
Fix this by adding to `/etc/ssh/sshd_config`:

```conf
PubkeyAcceptedKeytypes -ssh-dss,ssh-dss-cert-v01@openssh.com
```

Make sure that permissions on all `~/.ssh` directories and `authorized_keys`
files are appropriate, this setup will fail if the permissions are too wide.

#### Install the PAM ssh agent module

FreeBSD: `pkg install pam_ssh_agent_auth`<BR/>
Ubuntu: `apt-get install libpam-ssh-agent-auth`<BR/>
RedHat: `yum install pam_ssh_agent_auth`

#### Configure PAM for sudo

To enable the module, add the following line to `/usr/local/etc/pam.d/sudo`
(`/etc/pam.d/sudo` on Linux) early in the chain, before the first `auth` line.

```conf
auth sufficient pam_ssh_agent_auth.so file=~/.ssh/authorized_keys
```

You could use keys other than the one used for the connection

#### Configure sudo

**NOTE:** not all systems require this...

Make sure that the `SSH_AUTH_SOCK` is not clobbered when sudo is run, and
disable password caching. Use `sudo visudo` and add after the other
"Defaults" lines at the top of the file

```conf
Defaults       env_keep += SSH_AUTH_SOCK
Defaults       timestamp_timeout=0
```

### Client configuration

#### Enable Agent Forwarding

OpenSSH: set `ForwardAgent yes` in `~/.ssh/config`<BR/>
PuTTY: Configuration in "Connection -> SSH -> Auth" enable "Allow Agent
Forwarding"

#### Use the ssh authentication agent

OpenSSH: run `ssh-agent` and add your key with `ssh-add`<BR/>
PuTTY: Start "Pageant" and load your key

#### Reuse existing ssh-agent session

If you're like me, you'll probably be running multiple/many shells. You
can reuse an already running `ssh-agent` in terminals your start.
Add (something like) this to your `.profile` (or `.zshrc`, `.bashrc` etc.)

```sh
#!sh
# Check for an already running ssh-agent
agent_pid=`pgrep ssh-agent`
[ $? -ne 0 ] && agent_pid=-1
# Check persisted environment vars for ssh-agent
file_pid=`sed -ne 's/.*SSH_AGENT_PID=\([0-9]*\).*/\1/p' ~/.ssh/agent`
if [ ${agent_pid} -ne ${file_pid:=0} ] ; then
    # Start ssh-agent and load keys (you can add additional key-filenames) 
    ssh-agent > ~/.ssh/agent
    ( cd ~/.ssh; ssh-add id_ed25519 id_ecdsa; )
fi
. ~/.ssh/agent
```