#!/usr/bin/env python3
"""
Script to check your current public IP address
"""
import requests
import json

def get_public_ip():
    """Get your current public IP address"""
    try:
        # Try multiple services in case one is down
        services = [
            "https://api.ipify.org?format=json",
            "https://httpbin.org/ip",
            "https://api.myip.com",
            "https://ipinfo.io/json"
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=5)
                data = response.json()
                
                # Different services return IP in different fields
                if 'ip' in data:
                    return data['ip']
                elif 'origin' in data:
                    return data['origin']
                    
            except Exception as e:
                print(f"Service {service} failed: {e}")
                continue
        
        return None
        
    except Exception as e:
        print(f"Error getting IP: {e}")
        return None

def main():
    print("🔍 Checking your current public IP address...")
    print("=" * 50)
    
    ip = get_public_ip()
    
    if ip:
        print(f"✅ Your current public IP address: {ip}")
        print(f"📋 CIDR format for AWS: {ip}/32")
        print("\n" + "=" * 50)
        print("📝 Next Steps:")
        print("1. Copy this IP address")
        print("2. Go to AWS Console > EC2 > Security Groups")
        print("3. Find security group: sg-05c47e601362a1af7")
        print("4. Add inbound rule:")
        print(f"   - Type: Custom TCP")
        print(f"   - Port: 5432")
        print(f"   - Source: {ip}/32")
        print(f"   - Description: My IP for PostgreSQL")
        
    else:
        print("❌ Could not determine your public IP address")
        print("Please visit https://whatismyipaddress.com/ manually")

if __name__ == "__main__":
    main()