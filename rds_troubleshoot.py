#!/usr/bin/env python3
"""
Comprehensive AWS RDS troubleshooting script
"""
import socket
import requests
import subprocess
import json
import sys
import time

def check_internet_connection():
    """Check if internet connection is working"""
    try:
        response = requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

def get_public_ip():
    """Get public IP address"""
    try:
        response = requests.get("https://api.ipify.org", timeout=10)
        return response.text.strip()
    except:
        return None

def test_dns_resolution(hostname):
    """Test if DNS can resolve the hostname"""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        return None

def test_port_connectivity(hostname, port, timeout=30):
    """Test if port is reachable"""
    try:
        socket.setdefaulttimeout(timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((hostname, port))
        sock.close()
        return result == 0
    except:
        return False

def ping_host(hostname):
    """Ping the hostname"""
    try:
        # Windows command
        result = subprocess.run(['ping', '-n', '4', hostname], 
                              capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout
    except:
        try:
            # Unix/Linux command
            result = subprocess.run(['ping', '-c', '4', hostname], 
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout
        except:
            return False, "Ping command failed"

def check_aws_cli():
    """Check if AWS CLI is installed and configured"""
    try:
        result = subprocess.run(['aws', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Check if configured
            try:
                result2 = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                                       capture_output=True, text=True)
                return True, result2.returncode == 0
            except:
                return True, False
        return False, False
    except:
        return False, False

def get_security_group_rules(group_id, region):
    """Get security group rules using AWS CLI"""
    try:
        cmd = [
            'aws', 'ec2', 'describe-security-groups',
            '--group-ids', group_id,
            '--region', region,
            '--query', 'SecurityGroups[0].IpPermissions',
            '--output', 'json'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except:
        return None

def check_rds_status(db_identifier, region):
    """Check RDS instance status"""
    try:
        cmd = [
            'aws', 'rds', 'describe-db-instances',
            '--db-instance-identifier', db_identifier,
            '--region', region,
            '--query', 'DBInstances[0].{Status:DBInstanceStatus,PubliclyAccessible:PubliclyAccessible,VpcSecurityGroups:VpcSecurityGroups}',
            '--output', 'json'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except:
        return None

def main():
    print("🔍 AWS RDS Comprehensive Troubleshooting")
    print("=" * 60)
    
    # Configuration
    rds_endpoint = "stegano.cvoi8i4o83ra.ap-southeast-1.rds.amazonaws.com"
    port = 5432
    security_group = "sg-05c47e601362a1af7"
    region = "ap-southeast-1"
    db_identifier = "stegano"
    
    results = []
    
    # Test 1: Internet connectivity
    print("1️⃣ Testing internet connectivity...")
    if check_internet_connection():
        print("   ✅ Internet connection: OK")
        results.append("✅ Internet: OK")
    else:
        print("   ❌ Internet connection: FAILED")
        results.append("❌ Internet: FAILED")
        return
    
    # Test 2: Get public IP
    print("\n2️⃣ Getting your public IP address...")
    public_ip = get_public_ip()
    if public_ip:
        print(f"   ✅ Your public IP: {public_ip}")
        results.append(f"✅ Public IP: {public_ip}")
    else:
        print("   ❌ Could not get public IP")
        results.append("❌ Public IP: Unknown")
    
    # Test 3: DNS resolution
    print("\n3️⃣ Testing DNS resolution...")
    resolved_ip = test_dns_resolution(rds_endpoint)
    if resolved_ip:
        print(f"   ✅ DNS resolution: {rds_endpoint} -> {resolved_ip}")
        results.append(f"✅ DNS: {resolved_ip}")
    else:
        print(f"   ❌ DNS resolution failed for {rds_endpoint}")
        results.append("❌ DNS: FAILED")
        return
    
    # Test 4: Ping test
    print("\n4️⃣ Testing ping connectivity...")
    ping_success, ping_output = ping_host(rds_endpoint)
    if ping_success:
        print("   ✅ Ping: SUCCESS")
        results.append("✅ Ping: OK")
    else:
        print("   ⚠️ Ping: FAILED (this might be normal, many servers block ping)")
        results.append("⚠️ Ping: Blocked")
    
    # Test 5: Port connectivity
    print(f"\n5️⃣ Testing port {port} connectivity...")
    print("   (This may take up to 30 seconds...)")
    port_open = test_port_connectivity(rds_endpoint, port, 30)
    if port_open:
        print(f"   ✅ Port {port}: OPEN")
        results.append(f"✅ Port {port}: Open")
    else:
        print(f"   ❌ Port {port}: CLOSED/FILTERED")
        results.append(f"❌ Port {port}: Blocked")
    
    # Test 6: AWS CLI
    print("\n6️⃣ Checking AWS CLI...")
    aws_installed, aws_configured = check_aws_cli()
    if aws_installed:
        if aws_configured:
            print("   ✅ AWS CLI: Installed and configured")
            results.append("✅ AWS CLI: OK")
        else:
            print("   ⚠️ AWS CLI: Installed but not configured")
            results.append("⚠️ AWS CLI: Not configured")
    else:
        print("   ❌ AWS CLI: Not installed")
        results.append("❌ AWS CLI: Not installed")
    
    # Test 7: Security group rules (if AWS CLI available)
    if aws_installed and aws_configured:
        print("\n7️⃣ Checking security group rules...")
        sg_rules = get_security_group_rules(security_group, region)
        if sg_rules:
            print("   📋 Current inbound rules:")
            has_postgres_rule = False
            has_my_ip = False
            
            for rule in sg_rules:
                if rule.get('FromPort') == 5432 and rule.get('ToPort') == 5432:
                    has_postgres_rule = True
                    print(f"   📌 PostgreSQL rule found:")
                    
                    for ip_range in rule.get('IpRanges', []):
                        cidr = ip_range.get('CidrIp', '')
                        desc = ip_range.get('Description', 'No description')
                        print(f"      - CIDR: {cidr} ({desc})")
                        
                        if public_ip and cidr == f"{public_ip}/32":
                            has_my_ip = True
                        elif cidr == "0.0.0.0/0":
                            has_my_ip = True
                    
                    for sg_ref in rule.get('UserIdGroupPairs', []):
                        sg_id = sg_ref.get('GroupId', '')
                        desc = sg_ref.get('Description', 'No description')
                        print(f"      - Security Group: {sg_id} ({desc})")
            
            if has_postgres_rule:
                if has_my_ip:
                    print("   ✅ Security group: Has rule for your IP")
                    results.append("✅ Security Group: OK")
                else:
                    print(f"   ❌ Security group: No rule for your IP ({public_ip})")
                    results.append("❌ Security Group: Missing your IP")
            else:
                print("   ❌ Security group: No PostgreSQL rule found")
                results.append("❌ Security Group: No PostgreSQL rule")
        else:
            print("   ❌ Could not retrieve security group rules")
            results.append("❌ Security Group: Check failed")
    
    # Test 8: RDS status
    if aws_installed and aws_configured:
        print("\n8️⃣ Checking RDS instance status...")
        rds_status = check_rds_status(db_identifier, region)
        if rds_status:
            status = rds_status.get('Status', 'unknown')
            publicly_accessible = rds_status.get('PubliclyAccessible', False)
            
            print(f"   📊 RDS Status: {status}")
            print(f"   🌐 Publicly Accessible: {publicly_accessible}")
            
            if status == 'available' and publicly_accessible:
                print("   ✅ RDS instance: Ready for connections")
                results.append("✅ RDS: Available")
            else:
                print("   ❌ RDS instance: Not ready for public connections")
                results.append(f"❌ RDS: {status}, Public: {publicly_accessible}")
        else:
            print("   ❌ Could not retrieve RDS status")
            results.append("❌ RDS: Status unknown")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TROUBLESHOOTING SUMMARY")
    print("=" * 60)
    
    for result in results:
        print(f"   {result}")
    
    # Recommendations
    print("\n🔧 RECOMMENDATIONS:")
    
    if "❌ Port 5432: Blocked" in results:
        print("\n🎯 MAIN ISSUE: Port 5432 is blocked")
        print("   This is likely a security group issue.")
        print("\n   💡 SOLUTION:")
        if public_ip:
            print(f"   1. Go to AWS Console > EC2 > Security Groups")
            print(f"   2. Find security group: {security_group}")
            print(f"   3. Add inbound rule:")
            print(f"      - Type: Custom TCP")
            print(f"      - Port: 5432")
            print(f"      - Source: {public_ip}/32")
            print(f"      - Description: My IP for PostgreSQL")
            
            if aws_installed and aws_configured:
                print(f"\n   🚀 QUICK FIX COMMAND:")
                print(f"   aws ec2 authorize-security-group-ingress \\")
                print(f"       --group-id {security_group} \\")
                print(f"       --protocol tcp --port 5432 \\")
                print(f"       --cidr {public_ip}/32 \\")
                print(f"       --region {region}")
        
    elif "✅ Port 5432: Open" in results:
        print("✅ Network connectivity looks good!")
        print("   Try running the connection test again:")
        print("   python test_aws_connection.py")
    
    print(f"\n🔗 Useful links:")
    print(f"   AWS Console: https://console.aws.amazon.com/")
    print(f"   Security Groups: https://console.aws.amazon.com/ec2/v2/home?region={region}#SecurityGroups:")
    print(f"   RDS Console: https://console.aws.amazon.com/rds/home?region={region}")

if __name__ == "__main__":
    main()