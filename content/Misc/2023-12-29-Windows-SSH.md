Title: Using SSH on Windows
Tags: Windows, SSH, Security
Modified: 2023-12-29
Author: Bernard Spil
Image: /img/OpenSSH-Windows.png
Summary: Everything you need to connect to an SSH server is available in Windows!

# Using SSH on Windows

Any currently supported version of Windows has SSH support as an option. Out-of-the-Box it allows for secure authentication without passwords.

This guide helps you set up your Windows installation with Microsoft's own tools for using SSH connections securely.

## Installation

Adapted from [Microsoft's documentation](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse?tabs=gui).

1. Open Settings, select Apps, then select Optional Features.
1. Scan the list to see if the OpenSSH Client is already installed.
    1. If not, at the top of the page, select Add a feature, then:
    1. Find OpenSSH Client, then select Install (you'll need administrative privileges).
1. Once setup completes, return to Apps and Optional Features and confirm OpenSSH Client is listed.

### Terminal

SSH works fine in a "Command Prompt" or "cmd.exe", but you'll have a better time using SSH in a full-featured shell. Microsoft has created "Windows Terminal" which works fine and is customizable. With minor modifications it behaves very much like PuTTY.

1. Check if Windows Terminal is already installed, search for “Terminal” in the installed Apps.
2. Install via the Microsoft Store [direct link](https://aka.ms/terminal)

To mimic PuTTY behavior, enable "Automatically copy selection to clipboard" in Windows Terminal.

## Initialize ssh credentials

Open Terminal (it opens cmd.exe or PowerShell, both work) to create an identity with empty passphrase (password).

**NOTE**: This creates an unprotected private key that **must** be deleted once imported in Windows’ secure storage!

```powershell
PS C:\Users\%USERNAME%> ssh-keygen -t ed25519
Generating public/private ed25519 key pair.
Enter file in which to save the key (C:\Users\%USERNAME%/.ssh/id_ed25519): C:\Users\%USERNAME%/.ssh/id_ed25519
Enter passphrase (empty for no passphrase):
Enter same passphrase again:
Your identification has been saved in C:\Users\%USERNAME%/.ssh/id_ed25519
Your public key has been saved in C:\Users\%USERNAME%/.ssh/id_ed25519.pub
The key fingerprint is:
SHA256:Hetn1tlfd4of4J+tngul+XRA2VLleSpFSbtzFV1WLq8 WORKGROUP\%USERNAME%@Desktop-ABCDEF

The key's randomart image is:

+--[ED25519 256]--+
|             .oo@|
|             ..O+|
|          .   B.*|
|         . o o *o|
|        S o o * o|
|         . . B B |
|          . O E *|
|           + * B=|
|            .o@oo|
+----[SHA256]-----+
```

Now we load our identity persistently in Windows' secure storage and remove the private key (**do not** remove the .pub file)

```powershell
PS C:\Users\%username%> ssh-add %userprofile%\.ssh\id_ed25519
Identity added: .ssh\id_ed25519 (WORKGROUP\%username%@Desktop-ABCDEF)
PS C:\Users\%username%> del %userprofile%\.ssh\id_ed25519
```

The public key you need to have on the system you’re accessing is found in the .pub file

```powershell
PS C:\Users\%username%> type %homepath%\.ssh\id_ed25519.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAII/j+VC4UdM2S/l0RF4VGaherVQi3jH3oPuQPgXTwhiD WORKGROUP\%username%@Desktop-ABCDEF
```

We’ve chosen the ed25519 format as it is secure and most concise. Add the whole string on the remote server in the `~/.ssh/authorized_keys` file, or provide it to the admin of the server for inclusion.

Accessing a server via SSH
You can now use Windows Terminal to access servers that have your ssh key:

```powershell
ssh server.company.local
```

this will try to use key authentication by default and fall back to password-based authentication if that fails. Additional options to pass can be found in the OpenSSH documentation, as an example, you can use a different username in at least 2 ways:

```sh
ssh myuser@server.company.local
```

```sh
ssh -l myuser server.company.local
```

## Saving options

OpenSSH uses a text-file based format in `%userprofile%\.ssh\config`. As an example, you could use a different username by default, or for specific servers, or a shortcut with a config like

```conf
User myuser

Host server
        HostName %h.subdomain.example.org

Host *.subdomain.example.org
        User flastname
```

this will cause a command like `ssh server.example.org` to use username `myuser`, but a connection to `server.subdomain.example.org` to use username `flastname`. As a shortcut, you can use `ssh server` to connect to `server.subdomain.example.org` with username `flastname`.

The possibilities are endless, and there's even variable substitution (`%h`). Note that the "first `Match` wins", order is important.

See the documentation for more information about [ssh configuration](https://man.openbsd.org/ssh_config)

## Using Stepping Stones / Jump Servers

Accessing a server via another server can be achieved ad-hoc

```powershell
ssh -J jumpserver.example.org server.company.local
```

or using a config snippet

```conf
Host *.company.local
        ProxyJump jumpserver.example.org
```

`ssh server.company.local` will now "jump" via `jumpserver.example.org`.
