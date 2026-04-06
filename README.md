# MFASweep
MFASweep is a PowerShell script that attempts to log in to various Microsoft services using a provided set of credentials and will attempt to identify if MFA is enabled. Depending on how conditional access policies and other multi-factor authentication settings are configured some protocols may end up being left single factor.  It also has an additional check for ADFS configurations and can attempt to log in to the on-prem ADFS server if detected. 

Currently MFASweep has the ability to log in to the following services:

* Microsoft Graph API
* Azure Resource Manager API
* Microsoft 365 Exchange Web Services
* Microsoft 365 Web Portal w/ 7 user-agent / device types (Windows, Linux, MacOS, Android, iPhone, Windows Phone, Unknown Platform via Nintendo Switch)
* Microsoft 365 Active Sync
* ADFS

**WARNING: This script attempts to login to the provided account ELEVEN (11) different times (12 if you include ADFS). If you entered an incorrect password this may lock the account out.**

For more information check out the blog post here: [Exploiting MFA Inconsistencies on Microsoft Services](https://www.blackhillsinfosec.com/exploiting-mfa-inconsistencies-on-microsoft-services/) 

![MFASweep Example](/example.jpg?raw=true)

![Single Factor Access Results Example](/example2.jpg?raw=true)

## Usage

This command will use the provided credentials and attempt to authenticate to the Microsoft Graph API, Azure Resource Manager API, Microsoft 365 Exchange Web Services, Microsoft 365 Web Portal with 7 different user agents, and Microsoft 365 Active Sync. If any authentication methods result in success, tokens and/or cookies will be written to `AccessTokens.json`. (Currently does not log cookies or tokens for EWS, ActiveSync, and ADFS.)

```PowerShell
Invoke-MFASweep -Username targetuser@targetdomain.com -Password Winter2026 -WriteTokens 
```

This command runs with the default auth methods and checks for ADFS as well.

```PowerShell
Invoke-MFASweep -Username targetuser@targetdomain.com -Password Winter2026 -Recon -IncludeADFS
```

### Notes

* The script now uses an `Invoke-MFASweepWebRequest` wrapper so it can run cleanly on both Windows PowerShell 5.1 and PowerShell 7+.
* Microsoft Graph API and Azure Resource Manager API checks explicitly detect `AADSTS53003` responses and report Conditional Access blocks separately from generic auth failures.
* The "Unknown Platform" web check uses a Nintendo Switch user-agent string through `Invoke-M365WebPortalAuth -UAtype NintendoSwitch`.

## Individual Modules

Each individual module can be run separately if needed as well.

**Microsoft Graph API**
```PowerShell
Invoke-GraphAPIAuth -Username targetuser@targetdomain.com -Password Winter2026 
```

**Azure Resource Manager API**
```PowerShell
Invoke-AzureManagementAPIAuth -Username targetuser@targetdomain.com -Password Winter2026 
```

**Microsoft 365 Exchange Web Services**
```PowerShell
Invoke-EWSAuth -Username targetuser@targetdomain.com -Password Winter2026 
```

**Microsoft 365 Web Portal (Windows user agent)**
```PowerShell
Invoke-M365WebPortalAuth -Username targetuser@targetdomain.com -Password Winter2026 -UAtype Windows
```

**Microsoft 365 Web Portal (iPhone user agent)**
```PowerShell
Invoke-M365WebPortalAuth -Username targetuser@targetdomain.com -Password Winter2026 -UAtype iPhone
```

**Microsoft 365 Web Portal (Unknown Platform / Nintendo Switch user agent)**
```PowerShell
Invoke-M365WebPortalAuth -Username targetuser@targetdomain.com -Password Winter2026 -UAtype NintendoSwitch
```

**Microsoft 365 Active Sync**
```PowerShell
Invoke-O365ActiveSyncAuth -Username targetuser@targetdomain.com -Password Winter2026 
```

**ADFS**
```PowerShell
Invoke-ADFSAuth -Username targetuser@targetdomain.com -Password Winter2026
```

**Unknown Platform (CA Policy Bypass)**

This module tests for misconfigured Conditional Access policies that don't enforce MFA for unknown device platforms. It uses a Nintendo Switch user-agent string so that Entra ID reports the device platform and browser as "Unknown."
```PowerShell
Invoke-UnknownPlatformAuth -Username targetuser@targetdomain.com -Password Winter2026 
```
### Brute Forcing Client IDs During ROPC Auth
The Invoke-BruteClientIDs function will loop through various resource types and client IDs during ROPC auth to find single factor access for various combinations of client IDs and resources. If any authentication methods result in success, tokens and/or cookies will be written to AccessTokens.json. (Currently does not log cookies or tokens for EWS, ActiveSync, and ADFS)

```PowerShell
Invoke-BruteClientIDs -Username targetuser@targetdomain.com -Password Winter2026 -VerboseOut
```

By default the Invoke-BruteClientIDs module uses a list of the top 10 most common resources and top 50 clientIDs. You can use the -FullResourceList and -FullClientIdList flags to use built-in larger lists of 514 clientIDs and 54 resources.

```PowerShell
Invoke-BruteClientIDs -Username targetuser@targetdomain.com -Password Winter2026  -FullResourceList -FullClientIdList -VerboseOut
```
