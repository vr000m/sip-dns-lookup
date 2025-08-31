import sys
import argparse
import dns.resolver

def query_naptr(domain, timeout=5.0):
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        answers = resolver.resolve(domain, 'NAPTR')
        return answers
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return []
    except dns.resolver.Timeout:
        print(f"  Warning: NAPTR query timed out after {timeout} seconds")
        return []
    except Exception as e:
        print(f"  Warning: NAPTR query failed: {e}")
        return []

def query_srv(name, timeout=5.0):
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        answers = resolver.resolve(name, 'SRV')
        return answers
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return []
    except dns.resolver.Timeout:
        print(f"  Warning: SRV query timed out after {timeout} seconds")
        return []
    except Exception as e:
        print(f"  Warning: SRV query failed: {e}")
        return []

def parse_naptr_for_sip(naptr_records):
    services = []
    srv_targets = []
    
    for r in naptr_records:
        # Check service field for SIP protocols
        if hasattr(r, 'service') and (b"SIP+D2U" in r.service or b"SIP+D2T" in r.service or b"SIP+D2S" in r.service):
            # Check if there's a replacement field pointing to an SRV record
            if hasattr(r, 'replacement') and str(r.replacement) != '.':
                srv_target = str(r.replacement)
                if srv_target.endswith('.'):
                    srv_target = srv_target[:-1]
                srv_targets.append(srv_target)
            else:
                # Standard service prefixes
                if b"SIP+D2U" in r.service:
                    services.append('_sip._udp.')
                if b"SIP+D2T" in r.service:
                    services.append('_sip._tcp.')
                if b"SIP+D2S" in r.service:  # SCTP
                    services.append('_sip._sctp.')
    
    return services, srv_targets

def main(domain, timeout=5.0):
    print(f"Querying NAPTR records for {domain}...")
    naptr_records = query_naptr(domain, timeout)
    
    srv_names_to_query = []
    
    if naptr_records:
        naptr_services, srv_targets = parse_naptr_for_sip(naptr_records)
        
        # Add direct SRV targets from NAPTR replacement fields
        if srv_targets:
            print(f"Found {len(srv_targets)} SRV target(s) in NAPTR records")
            srv_names_to_query.extend(srv_targets)
        
        # Add service-based SRV names
        if naptr_services:
            for service in naptr_services:
                srv_names_to_query.append(f"{service}{domain}")
        
        # If no SIP-related NAPTR records, fall back to standard SRV
        if not naptr_services and not srv_targets:
            print("No SIP NAPTR records found. Trying SRV records directly.")
            srv_names_to_query = [f"_sip._udp.{domain}", f"_sip._tcp.{domain}"]
    else:
        print("No NAPTR records found. Trying SRV records directly.")
        srv_names_to_query = [f"_sip._udp.{domain}", f"_sip._tcp.{domain}"]

    # Query all SRV records
    for srv_name in srv_names_to_query:
        print(f"\nQuerying SRV records for {srv_name}...")
        srv_records = query_srv(srv_name, timeout)
        if srv_records:
            for record in srv_records:
                print(f"Priority: {record.priority}, Weight: {record.weight}, Port: {record.port}, Target: {record.target}")
        else:
            print("No SRV records found.")

def process_batch(domains, timeout=5.0):
    """Process multiple domains"""
    print(f"Processing {len(domains)} domain(s)...\n")
    for i, domain in enumerate(domains, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(domains)}] Domain: {domain}")
        print('='*60)
        main(domain.strip(), timeout)

def parse_sip_address(address):
    """Extract domain from SIP address (e.g., user@domain)"""
    if not address:
        return None
    address = address.replace("sip:", "").strip()
    if not address:
        return None
    if "@" in address:
        domain = address.split("@")[1]
        domain = domain.split(":")[0].split(";")[0].split(">")[0].strip()
        return domain if domain else None
    return address

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Query SIP-related DNS records (NAPTR, SRV) for domains",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sip.example.com                    # Query single domain
  %(prog)s user@sip.example.com               # Extract domain from SIP address
  %(prog)s -f domains.txt                     # Read domains from file
  %(prog)s domain1.com domain2.com            # Query multiple domains
        """)
    
    parser.add_argument('domains', nargs='*', help='Domain(s) to query (can be SIP addresses)')
    parser.add_argument('-f', '--file', help='File containing domains/SIP addresses (one per line)')
    parser.add_argument('-t', '--timeout', type=float, default=5.0, 
                       help='DNS query timeout in seconds (default: 5.0, min: 0.1, max: 30)')
    
    args = parser.parse_args()
    
    # Validate timeout
    if args.timeout < 0.1 or args.timeout > 30:
        print(f"Error: Timeout must be between 0.1 and 30 seconds (got {args.timeout})")
        sys.exit(1)
    
    # Collect domains to process
    domains_to_process = []
    
    # Add domains from file if specified
    if args.file:
        try:
            with open(args.file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        domain = parse_sip_address(line)
                        if domain:
                            domains_to_process.append(domain)
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    
    # Add domains from command line
    for arg_domain in args.domains:
        domain = parse_sip_address(arg_domain)
        if domain:
            domains_to_process.append(domain)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_domains = []
    for domain in domains_to_process:
        if domain not in seen:
            seen.add(domain)
            unique_domains.append(domain)
    
    # Process domains
    if not unique_domains:
        parser.print_help()
        sys.exit(1)
    elif len(unique_domains) == 1:
        main(unique_domains[0], args.timeout)
    else:
        process_batch(unique_domains, args.timeout)
