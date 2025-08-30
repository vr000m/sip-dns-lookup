import sys
import dns.resolver

def query_naptr(domain):
    try:
        answers = dns.resolver.resolve(domain, 'NAPTR')
        return answers
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return []

def query_srv(name):
    try:
        answers = dns.resolver.resolve(name, 'SRV')
        return answers
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return []

def parse_naptr_for_sip(naptr_records):
    services = []
    for r in naptr_records:
        if hasattr(r, 'service') and (b"SIP+D2U" in r.service or b"SIP+D2T" in r.service):
            if b"SIP+D2U" in r.service:
                services.append('_sip._udp.')
            if b"SIP+D2T" in r.service:
                services.append('_sip._tcp.')
    return services

def main(domain):
    print(f"Querying NAPTR records for {domain}...")
    naptr_records = query_naptr(domain)
    if naptr_records:
        naptr_services = parse_naptr_for_sip(naptr_records)
        if not naptr_services:
            print("No SIP NAPTR records found. Trying SRV records directly.")
            naptr_services = ['_sip._udp.', '_sip._tcp.']
    else:
        print("No NAPTR records found. Trying SRV records directly.")
        naptr_services = ['_sip._udp.', '_sip._tcp.']

    for service in naptr_services:
        srv_name = f"{service}{domain}"
        print(f"\nQuerying SRV records for {srv_name}...")
        srv_records = query_srv(srv_name)
        if srv_records:
            for record in srv_records:
                print(f"Priority: {record.priority}, Weight: {record.weight}, Port: {record.port}, Target: {record.target}")
        else:
            print("No SRV records found.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sip_dns_lookup.py <domain>")
        sys.exit(1)
    main(sys.argv[1])
