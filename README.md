# MFASweep
MFASweep is a PowerShell script that attempts to log in to various Microsoft services using a provided set of credentials and will attempt to identify if MFA is enabled. Depending on how conditional access policies and other multi-factor authentication settings are configured some protocols may end up being left single factor.  It also has an additional check for ADFS configurations and can attempt to log in to the on-prem ADFS server if detected. 

Currently MFASweep has the ability to login to the following services:

* Microsoft Graph API
* Azure Service Management API
* Microsoft 365 Exchange Web Services
* Microsoft 365 Web Portal
* Microsoft 365 Web Portal Using a Mobile User Agent
* Microsoft 365 Active Sync
* ADFS

**WARNING: This script attempts to login to the provided account SIX (6) different times (7 if you include ADFS). If you entered an incorrect password this may lock the account out.**

For more information check out the blog post here: [Exploiting MFA Inconsistencies on Microsoft Services](https://www.blackhillsinfosec.com/exploiting-mfa-inconsistencies-on-microsoft-services/) 

![MFASweep Example](/example.jpg?raw=true)

## Usage

This command will use the provided credentials and attempt to authenticate to the Microsoft Graph API, Azure Service Management API, Microsoft 365 Exchange Web Services, Microsoft 365 Web Portal with both a desktop browser and mobile, and Microsoft 365 Active Sync. 

```PowerShell
Invoke-MFASweep -Username targetuser@targetdomain.com -Password Winter2020 
```

This command runs with the default auth methods and checks for ADFS as well.

```PowerShell
Invoke-MFASweep -Username targetuser@targetdomain.com -Password Winter2020 -Recon -IncludeADFS
```

## Individual Modules

Each individual module can be run separately if needed as well.

**Microsoft Graph API**
```PowerShell
Invoke-GraphAPIAuth -Username targetuser@targetdomain.com -Password Winter2020 
```

**Azure Service Management API**
```PowerShell
Invoke-AzureManagementAPIAuth -Username targetuser@targetdomain.com -Password Winter2020 
```

**Microsoft 365 Exchange Web Services**
```PowerShell
Invoke-EWSAuth -Username targetuser@targetdomain.com -Password Winter2020 
```

**Microsoft 365 Web Portal**
```PowerShell
Invoke-O365WebPortalAuth -Username targetuser@targetdomain.com -Password Winter2020 
```

**Microsoft 365 Web Portal w/ Mobile User Agent**
```PowerShell
Invoke-O365WebPortalAuthMobile -Username targetuser@targetdomain.com -Password Winter2020 
```

**Microsoft 365 Active Sync**
```PowerShell
Invoke-O365ActiveSyncAuth -Username targetuser@targetdomain.com -Password Winter2020 
```

**ADFS**
```PowerShell
Invoke-ADFSAuth -Username targetuser@targetdomain.com -Password Winter2020 
```
