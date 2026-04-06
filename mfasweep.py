#!/usr/bin/env python3
"""
MFASweep - Python/Linux port
Original PowerShell tool by Beau Bullock (@dafthack)
Python port for Linux/Ubuntu - MIT License

WARNING: This script attempts to login to the provided account multiple times.
If you entered an incorrect password this may lock the account out.
Only use against accounts you are authorized to test.

Usage:
    python3 mfasweep.py --username user@domain.com --password 'Password123'
    python3 mfasweep.py --username user@domain.com --password 'Password123' --recon --include-adfs
    python3 mfasweep.py --username user@domain.com --password 'Password123' --write-tokens
    python3 mfasweep.py --username user@domain.com --password 'Password123' --brute-client-ids

Dependencies:
    pip install requests
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print("[!] Missing dependency: pip install requests")
    sys.exit(1)


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

GRAPH_CLIENT_ID    = "1b730954-1685-4b74-9bfd-dac224a7b894"   # Azure AD PowerShell
AZUREMGMT_CLIENT   = "1950a258-227b-4e31-a9cf-717495945fc2"   # Azure Management
TEAMS_CLIENT       = "1fec8e78-bce4-4aaf-ab1b-5451cc387264"
OFFICE_CLIENT      = "d3590ed6-52b3-4102-aeff-aad2292ab01c"
ACTIVESYNC_CLIENT  = "d3590ed6-52b3-4102-aeff-aad2292ab01c"

GRAPH_RESOURCE     = "https://graph.microsoft.com"
AZUREMGMT_RESOURCE = "https://management.azure.com/"
TEAMS_RESOURCE     = "https://api.spaces.skype.com"
OFFICE_RESOURCE    = "https://officeapps.live.com"

ROPC_ENDPOINT      = "https://login.microsoftonline.com/common/oauth2/token"
ADFS_REALM_URL     = "https://login.microsoftonline.com/getuserrealm.srf"

# User-Agents for the M365 Portal checks
USER_AGENTS = {
    "Windows":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Linux":         "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "MacOS":         "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Android Phone": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "iPhone":        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Windows Phone": "Mozilla/5.0 (Windows Phone 10.0; Android 6.0.1; Microsoft; Lumia 950) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Mobile Safari/537.36 Edge/15.15254",
}

# Resource/ClientID combos for brute mode
BRUTE_COMBOS = [
    {"resource": "https://graph.microsoft.com",       "client_id": "1b730954-1685-4b74-9bfd-dac224a7b894", "label": "Graph API (AAD PowerShell)"},
    {"resource": "https://graph.microsoft.com",       "client_id": "d3590ed6-52b3-4102-aeff-aad2292ab01c", "label": "Graph API (Office Client)"},
    {"resource": "https://graph.microsoft.com",       "client_id": "1fec8e78-bce4-4aaf-ab1b-5451cc387264", "label": "Graph API (Teams)"},
    {"resource": "https://management.azure.com/",     "client_id": "1950a258-227b-4e31-a9cf-717495945fc2", "label": "Azure Management"},
    {"resource": "https://management.azure.com/",     "client_id": "d3590ed6-52b3-4102-aeff-aad2292ab01c", "label": "Azure Management (Office Client)"},
    {"resource": "https://api.spaces.skype.com",      "client_id": "1fec8e78-bce4-4aaf-ab1b-5451cc387264", "label": "Teams"},
    {"resource": "https://officeapps.live.com",       "client_id": "d3590ed6-52b3-4102-aeff-aad2292ab01c", "label": "Office Apps"},
    {"resource": "https://substrate.office.com",      "client_id": "d3590ed6-52b3-4102-aeff-aad2292ab01c", "label": "Substrate (Office)"},
    {"resource": "https://outlook.office365.com",     "client_id": "d3590ed6-52b3-4102-aeff-aad2292ab01c", "label": "Exchange Online (Office)"},
    {"resource": "https://outlook.office365.com",     "client_id": "1b730954-1685-4b74-9bfd-dac224a7b894", "label": "Exchange Online (AAD PS)"},
]

tokens_store = []   # Collected tokens/cookies for --write-tokens


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def banner():
    print("\033[93m[!] Original by @dafthack")
    print("\033[93m[!] WARNING: This tool attempts to authenticate multiple times.")
    print("[!] An incorrect password may LOCK the account out.\033[0m\n")


def ok(msg):
    print(f"\033[92m[+] {msg}\033[0m")

def info(msg):
    print(f"\033[96m[*] {msg}\033[0m")

def warn(msg):
    print(f"\033[93m[!] {msg}\033[0m")

def fail(msg):
    print(f"\033[91m[-] {msg}\033[0m")

def section(title):
    print(f"\n\033[1m\033[94m{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}\033[0m")


def ropc_token(username, password, client_id, resource, scope="openid"):
    """Resource Owner Password Credentials grant."""
    data = {
        "grant_type":  "password",
        "username":    username,
        "password":    password,
        "client_id":   client_id,
        "resource":    resource,
        "scope":       scope,
    }
    try:
        r = requests.post(ROPC_ENDPOINT, data=data, timeout=20, verify=False)
        return r.json()
    except Exception as e:
        return {"error": "request_failed", "error_description": str(e)}


def mfa_required(response_json):
    """Return True if the error indicates MFA is required."""
    desc = response_json.get("error_description", "").lower()
    err  = response_json.get("error", "").lower()
    mfa_hints = [
        "mfa", "multi-factor", "multifactor",
        "aadsts50076", "aadsts50079", "aadsts50074",
        "strong authentication", "additional security verification",
    ]
    return any(h in desc or h in err for h in mfa_hints)


def check_ropc(label, username, password, client_id, resource, write_tokens=False):
    section(label)
    info(f"Attempting ROPC auth → resource: {resource}")
    resp = ropc_token(username, password, client_id, resource)

    if "access_token" in resp:
        ok("Authentication SUCCESS — No MFA enforced!")
        if write_tokens:
            tokens_store.append({"service": label, "tokens": resp})
        return True

    desc = resp.get("error_description", "")

    # Credentials valid BUT MFA is required
    mfa_codes = ["AADSTS50076", "AADSTS50079", "AADSTS50074"]
    if any(code in desc for code in mfa_codes):
        ok(f"Authentication SUCCESS — Credentials valid! NOTE: MFA is enforced.")
        return False

    # Credentials are just wrong / account locked etc.
    elif "error" in resp:
        fail(f"Auth failed: {desc[:120]}")

    return False

# ─────────────────────────────────────────────
# ADFS Recon
# ─────────────────────────────────────────────

def check_adfs_recon(username):
    section("ADFS Recon")
    info(f"Checking ADFS configuration for domain of {username}")
    try:
        r = requests.get(
            ADFS_REALM_URL,
            params={"login": username, "xml": "1"},
            timeout=15, verify=False
        )
        root = ET.fromstring(r.text)
        ns_type  = root.findtext("NameSpaceType")
        auth_url = root.findtext("AuthURL")

        if ns_type == "Federated":
            ok(f"Domain is FEDERATED (ADFS detected)")
            if auth_url:
                ok(f"ADFS Auth URL: {auth_url}")
            return auth_url
        else:
            info(f"Domain NameSpaceType: {ns_type} — ADFS not detected.")
    except Exception as e:
        fail(f"ADFS recon failed: {e}")
    return None


def check_adfs_login(username, password, adfs_url):
    section("ADFS Authentication")
    if not adfs_url:
        warn("No ADFS URL available — skipping ADFS login check.")
        return

    info(f"Attempting ADFS auth at: {adfs_url}")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data    = {"UserName": username, "Password": password, "AuthMethod": "FormsAuthentication"}

    try:
        r = requests.post(adfs_url, data=data, headers=headers,
                          allow_redirects=True, timeout=20, verify=False)
        if r.status_code == 200 and "samlp:Response" in r.text:
            ok("ADFS Authentication SUCCESS — No MFA enforced!")
        elif r.status_code in (200, 302) and "error" not in r.url.lower():
            ok("ADFS Authentication appears successful (redirect with no error).")
        else:
            warn(f"ADFS Authentication result unclear (status {r.status_code}). Check manually.")
    except Exception as e:
        fail(f"ADFS login request failed: {e}")


# ─────────────────────────────────────────────
# M365 Web Portal (cookie-based)
# ─────────────────────────────────────────────

def check_m365_portal(username, password, write_tokens=False):
    section("Microsoft 365 Web Portal")
    info("Testing 6 device User-Agents against the M365 web portal...")

    session = requests.Session()

    # Step 1 — grab the login page to find the flow URL
    try:
        init = session.get(
            "https://outlook.office365.com",
            headers={"User-Agent": USER_AGENTS["Windows"]},
            allow_redirects=True, timeout=20, verify=False
        )
    except Exception as e:
        fail(f"Could not reach M365 portal: {e}")
        return

    # Extract the login POST URL from the page source
    import re
    url_match = re.search(r'"urlLogin"\s*:\s*"([^"]+)"', init.text)
    if not url_match:
        # Fall back to the standard endpoint
        login_url = "https://login.microsoftonline.com/common/login"
    else:
        login_url = url_match.group(1).replace("\\u0026", "&")

    ctx_match = re.search(r'"sCtx"\s*:\s*"([^"]+)"', init.text)
    flow_token_match = re.search(r'"sFT"\s*:\s*"([^"]+)"', init.text)

    sctx       = ctx_match.group(1)       if ctx_match        else ""
    flow_token = flow_token_match.group(1) if flow_token_match else ""

    for device, ua in USER_AGENTS.items():
        info(f"  Trying device type: {device}")
        s = requests.Session()
        headers = {"User-Agent": ua}

        try:
            # POST credentials
            payload = {
                "login":     username,
                "passwd":    password,
                "ctx":       sctx,
                "flowToken": flow_token,
                "canary":    "",
            }
            r = s.post(login_url, data=payload, headers=headers,
                       allow_redirects=True, timeout=20, verify=False)

            if "OIDCAuth" in r.url or "outlook.office365.com" in r.url:
                ok(f"  [{device}] M365 Portal login SUCCESS — No MFA enforced!")
                if write_tokens:
                    tokens_store.append({
                        "service": f"M365 Portal ({device})",
                        "cookies": dict(s.cookies)
                    })
            elif mfa_required({"error_description": r.text, "error": r.text}):
                warn(f"  [{device}] MFA IS required.")
            elif "AADSTS" in r.text:
                code = re.search(r"AADSTS\d+", r.text)
                fail(f"  [{device}] Auth failed: {code.group(0) if code else 'AADSTS error'}")
            else:
                warn(f"  [{device}] Result unclear — manual verification recommended.")
        except Exception as e:
            fail(f"  [{device}] Request error: {e}")


# ─────────────────────────────────────────────
# Exchange Web Services (Basic Auth probe)
# ─────────────────────────────────────────────

def check_ews(username, password):
    section("Microsoft 365 Exchange Web Services (EWS)")
    info("Probing EWS endpoint with Basic Auth...")
    ews_url = "https://outlook.office365.com/EWS/Exchange.asmx"
    try:
        r = requests.get(
            ews_url,
            auth=(username, password),
            timeout=20, verify=False
        )
        if r.status_code == 200:
            ok("EWS Authentication SUCCESS — No MFA enforced!")
        elif r.status_code == 401:
            # Check WWW-Authenticate header for MFA hints
            www_auth = r.headers.get("WWW-Authenticate", "").lower()
            if "bearer" in www_auth:
                warn("EWS: MFA or modern auth required (Bearer challenge returned).")
            else:
                fail("EWS Authentication failed (401 Unauthorized).")
        elif r.status_code == 403:
            warn("EWS: 403 Forbidden — account may exist but access denied.")
        else:
            warn(f"EWS: Unexpected status {r.status_code}")
    except Exception as e:
        fail(f"EWS request failed: {e}")


# ─────────────────────────────────────────────
# ActiveSync
# ─────────────────────────────────────────────

def check_activesync(username, password):
    section("Microsoft 365 ActiveSync")
    info("Probing ActiveSync endpoint with Basic Auth...")
    as_url = "https://outlook.office365.com/Microsoft-Server-ActiveSync"
    headers = {
        "User-Agent": "Apple-iPhone9C1/1602.92",
        "MS-ASProtocolVersion": "14.0",
    }
    try:
        r = requests.options(
            as_url,
            auth=(username, password),
            headers=headers,
            timeout=20, verify=False
        )
        if r.status_code == 200:
            ok("ActiveSync Authentication SUCCESS — No MFA enforced!")
        elif r.status_code == 401:
            fail("ActiveSync Authentication failed (401).")
        elif r.status_code == 403:
            warn("ActiveSync: 403 — may be blocked by policy, not necessarily MFA.")
        else:
            warn(f"ActiveSync: Unexpected status {r.status_code}")
    except Exception as e:
        fail(f"ActiveSync request failed: {e}")


# ─────────────────────────────────────────────
# Brute Client IDs
# ─────────────────────────────────────────────

def invoke_brute_client_ids(username, password, write_tokens=False):
    section("Brute Client IDs / Resource Sweep")
    warn(f"Testing {len(BRUTE_COMBOS)} resource+clientID combinations...")
    print()

    found = []
    for combo in BRUTE_COMBOS:
        info(f"Trying: {combo['label']}")
        resp = ropc_token(username, password, combo["client_id"], combo["resource"])
        if "access_token" in resp:
            ok(f"  SUCCESS — {combo['label']} — No MFA enforced!")
            found.append(combo["label"])
            if write_tokens:
                tokens_store.append({"service": combo["label"], "tokens": resp})
        elif mfa_required(resp):
            warn(f"  MFA required — {combo['label']}")
        else:
            desc = resp.get("error_description", resp.get("error", ""))[:80]
            fail(f"  Failed — {combo['label']} ({desc})")

    print()
    if found:
        ok(f"Single-factor access found for: {', '.join(found)}")
    else:
        info("No single-factor access found across all client ID combinations.")


# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────

def print_summary(results):
    section("Summary")
    headers = ["Service", "Result"]
    col1 = max(len(h) for h in [r[0] for r in results] + [headers[0]])
    col2 = 10

    print(f"  {'Service':<{col1}}  Result")
    print(f"  {'─'*col1}  {'─'*col2}")
    for svc, status in results:
        color = "\033[92m" if "SUCCESS" in status else ("\033[93m" if "MFA" in status else "\033[91m")
        print(f"  {svc:<{col1}}  {color}{status}\033[0m")
    print()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MFASweep — Python/Linux port. Check MFA enforcement across Microsoft services.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 mfasweep.py --username user@domain.com --password 'Password123'
  python3 mfasweep.py --username user@domain.com --password 'Password123' --recon --include-adfs
  python3 mfasweep.py --username user@domain.com --password 'Password123' --write-tokens
  python3 mfasweep.py --username user@domain.com --password 'Password123' --brute-client-ids
        """
    )
    parser.add_argument("--username",         required=True,  help="Target email address")
    parser.add_argument("--password",         required=True,  help="Password")
    parser.add_argument("--recon",            action="store_true", help="Perform ADFS recon")
    parser.add_argument("--include-adfs",     action="store_true", help="Include ADFS login check")
    parser.add_argument("--write-tokens",     action="store_true", help="Write tokens/cookies to AccessTokens.json")
    parser.add_argument("--brute-client-ids", action="store_true", help="Brute-force resource/clientID combos")
    parser.add_argument("--skip-portal",      action="store_true", help="Skip M365 web portal checks")
    parser.add_argument("--skip-ews",         action="store_true", help="Skip EWS check")
    parser.add_argument("--skip-activesync",  action="store_true", help="Skip ActiveSync check")

    args = parser.parse_args()
    banner()

    info(f"Target:      {args.username}")
    info(f"Started:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.write_tokens:
        info("Token output: AccessTokens.json")

    results = []

    # ── ADFS Recon ────────────────────────────────
    adfs_url = None
    if args.recon or args.include_adfs:
        adfs_url = check_adfs_recon(args.username)

    # ── Microsoft Graph API ───────────────────────
    ok_graph = check_ropc(
        "Microsoft Graph API",
        args.username, args.password,
        GRAPH_CLIENT_ID, GRAPH_RESOURCE,
        write_tokens=args.write_tokens
    )
    results.append(("Graph API", "SUCCESS - No MFA" if ok_graph else "MFA/Failed"))

    # ── Azure Service Management ──────────────────
    ok_azure = check_ropc(
        "Azure Service Management API",
        args.username, args.password,
        AZUREMGMT_CLIENT, AZUREMGMT_RESOURCE,
        write_tokens=args.write_tokens
    )
    results.append(("Azure Mgmt API", "SUCCESS - No MFA" if ok_azure else "MFA/Failed"))

    # ── Teams ─────────────────────────────────────
    ok_teams = check_ropc(
        "Microsoft Teams",
        args.username, args.password,
        TEAMS_CLIENT, TEAMS_RESOURCE,
        write_tokens=args.write_tokens
    )
    results.append(("Teams", "SUCCESS - No MFA" if ok_teams else "MFA/Failed"))

    # ── Office Apps ───────────────────────────────
    ok_office = check_ropc(
        "Office Apps (OneDrive/SharePoint)",
        args.username, args.password,
        OFFICE_CLIENT, OFFICE_RESOURCE,
        write_tokens=args.write_tokens
    )
    results.append(("Office Apps", "SUCCESS - No MFA" if ok_office else "MFA/Failed"))

    # ── EWS ───────────────────────────────────────
    if not args.skip_ews:
        check_ews(args.username, args.password)
        results.append(("EWS", "See output above"))

    # ── ActiveSync ────────────────────────────────
    if not args.skip_activesync:
        check_activesync(args.username, args.password)
        results.append(("ActiveSync", "See output above"))

    # ── M365 Web Portal ───────────────────────────
    if not args.skip_portal:
        check_m365_portal(args.username, args.password, write_tokens=args.write_tokens)
        results.append(("M365 Portal (6 agents)", "See output above"))

    # ── ADFS Login ────────────────────────────────
    if args.include_adfs:
        check_adfs_login(args.username, args.password, adfs_url)
        results.append(("ADFS", "See output above"))

    # ── Brute Client IDs ──────────────────────────
    if args.brute_client_ids:
        invoke_brute_client_ids(args.username, args.password, write_tokens=args.write_tokens)
        results.append(("BruteClientIDs", "See output above"))

    # ── Summary ───────────────────────────────────
    print_summary(results)

    # ── Write Tokens ──────────────────────────────
    if args.write_tokens and tokens_store:
        out_file = "AccessTokens.json"
        with open(out_file, "w") as f:
            json.dump(tokens_store, f, indent=2)
        ok(f"Tokens/cookies written to {out_file}")


if __name__ == "__main__":
    main()
