Title: Changing Remote Desktop service certificate
Tags: Network Windows RemoteDesktop RDP Certificate
Category: Security
Created: 2024-01-12
Modified: 2024-04-05
Author: Bernard Spil
Image: /img/RDPCertWarning.png
Summary: By default, Windows Server will generate a self-signed certificate for the Remote Desktop Service. Using a different certificate is not trivial, but is doable as this post shows.

# Changing Remote Desktop service certificate

The out-of-the-box configuration forces users to accept certificate errors,
which is reinforcement learning of bad behavior.

Many companies will have Active Directory Certificate Services deployed,
and configured to provision certificates signed by the internal Certificate
Authority. This internal Certificate Authority tends to be added to all
client machines in the company. Yet the certificate is not used for the
Remote Desktop service.

If you do not have Active Directory Certificate Services deployed, you
can use other certificates, like LetsEncrypt's, as well. See the Win-Acme
paragraph.

## Check currently used RDP certificate

```powershell
try {
    (Get-WmiObject -class "Win32_TSGeneralSetting" -Namespace root\cimv2\terminalservices -Filter "TerminalName='RDP-tcp'").SSLCertificateSHA1Hash
} catch {
    wmic /namespace:\\root\cimv2\TerminalServices PATH Win32_TSGeneralSetting Get SSLCertificateSHA1Hash
}
```

this will return the SHA1 fingerprint of the currently used certificate for RDP. It matches the "Thumbprint" that you can find in a certificate's details in `certlm.msc` or by using the "View certificate..." button in the "Certificate errors" RDP dialog.

## Finding the right certificate

Let's start with the script that gets you the certificate you want to bind.

```ps
$now = (Get-Date)
$hostname = [System.Net.Dns]::GetHostEntry([string]$env:computername).HostName
$cert = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object {
    $_.NotAfter -ge $now -and `
    $_.Issuer -notmatch $hostname -and `
    ($_.Subject -match $hostname -or $_.DnsNameList -match $hostname)
} | Sort-Object -Property NotAfter | Select-Object -Last 1
```

Select a certificate from the computer's Personal certificate store that is:

1. Currently valid;
2. Are not self-signed (i.e. Issuer is Hostname);
3. Are valid for this server, either as Common Name or as Subject Alternative Name.
4. With the longest validity (if more than one is found).

Tip: If you use Active Directory Certificate Services, you could select
certificates from your Enterprise CA by replacing the `$_.Issuer` line to
select all certificates issued by your domain:

```
    $_.Issuer -match "DC=<domain>" -and `
```

## Binding the certificate

```powershell
try {
    # This works on modern Windows Server versions, fails on Windows Server 2012
    $path = (Get-WmiObject -class "Win32_TSGeneralSetting" -Namespace root\cimv2\terminalservices -Filter "TerminalName='RDP-tcp'").__path
    Set-WmiInstance -Path $path -argument @{SSLCertificateSHA1Hash=$cert.Thumbprint}
} catch {
    # Fallback for older Windows Server versions like 2012
    wmic /namespace:\\root\cimv2\TerminalServices PATH Win32_TSGeneralSetting Set SSLCertificateSHA1Hash="$($cert.Thumbprint)"
}
```

Things are not the same on all versions of Windows. The method that works
on Windows 2012 is deprecated, the method that works on 2016 does not work
on Windows 2012.

We try the modern method first, and fall back on calling the external `wmic`
command.

# Using LetsEncrypt

On Windows, [Win-Acme](https://www.win-acme.com/) works fine for me. We use
ACME dns-01 validation with a bespoke script and service for our DNS
management tooling.

Win-Acme comes with scripts that will to the binding for you. It will even
do installation of the certificate for all Remote Desktop roles.

```
--installation script --script 'C:\Path\To\Win-Acme\Scripts\ImportRDListener.ps1' --scriptparameters '{CertThumbprint}'
```

This can be accomplished in the "Install" section when you configure Win-Acme.
