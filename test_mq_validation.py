#!/usr/bin/env python3
"""
Test script to validate MQ message format and test connectivity
"""

import json
import os
from pydantic import ValidationError
from src.models import KnowledgeCreateMessage, KnowledgeMessageMetadata
from src.mq_handler import MQHandler
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_message_format():
    """Validate the provided MQ message format"""
    print("🔍 Validating MQ Message Format")
    print("=" * 50)
    
    # The provided message example
    test_message = {
        "metadata": {
            "knowledgeId": "01K8ZGEBY6RARKF7ZVXSDRTHQW",
            "type": "ARTICLE",
            "access": "TENANT",
            "tenantId": "01K8ZEGGNQGZ8AM7XKS1DWSHEK",
            "accessUserIds": ["01K8YYWDRGK7Y5SA6W95SVAA1J"]
        },
        "fileType": "IMAGE",  # Note: This should be lowercase "image"
        "fileUrls": [],
        "content": """
        Headline: Admin Fee
        Category: Complaint
        Sub Category: e-money
        Case: Balance Not Update
        Knowledge Content: 
            Title: Admin Fee, Description: # Tarik Tunai Saldo DANA ke ATM

## Tarik tunai saldo DANA ke ATM merupakan fitur yang memungkinkan pelanggan untuk tarik saldo DANA dari aplikasi ke ATM (ATM BCA & ATMi)
X2P/X2L FEE ADMIN
User akan dikenakan biaya potongan Rp100/transaksi jika telah melampaui batas terima uang
lebih dari 100x dalam satu bulan dari sesama pengguna DANA melalui fitur Kirim Uang atau

Minta Uang di aplikasi DANA.

Biaya administrasi akan dikenakan sesuai dengan jumlah transaksi terima saldo, dengan rincian sebagai berikut:
>100x transaksi/bulan : Rp100
> 200x transaksi/bulan : Rp125
>300x transaksi/bulan : Rp150
>400x transaksi/bulan : Rp175
>500x transaksi/bulan : Rp200
>600x transaksi/bulan : Rp225
>700x transaksi/bulan : Rp250
TOP UP VA FEE ADMIN
Fee admin karena Sumber Top Up melakukan ke lebih dari 20 User​
User akann dikenakan biaya potongan Rp500/top up jika melakukan top up di agent tidak resmi. Agent tidak resmi yang dimaksud adalah sumber top up yang sudah melakukan top up ke lebih dari 18 user yang berbeda. Admin akan dikenakan ke penerima top up.
Fee admin karena penerima sudah Top Up lebih dari 20 kali per bulan​
User akan dikenakan biaya potongan Rp500/topp up jika telah melakukan top up VA lebih dari 20x per bulan. Admin akan dikenakan ke penerima top up. ​
Fee admin karrena top up dibawah 50K
User akan dikenakan biaya potongan Rp500/top up jika melakukan top up VA dibawah 50k. Admin akan dikenakan ke penerima top up. ​
Fee admin karena penerima sudah Top Up lebih dari 19 kali dari bank BCA dan BTPN pper bulan​
User akan dikenakan biaya potongan Rp500/top up jika telah melakukan top up VA dari bank BCA dan BTPN lebihh dari 19x per bulan. Admin akan dikenakan ke penerima top up. ​
Top up Charge VA Unprofitable​
"Jika rekening sum ber top up telah melakukan top up berkali-kali ke akun DANA, maka akan dikenakan biaya sebesar Rp500 pada akun penerima top up ya kak. DANA berhak memberikan promo dalam bentuk potongan biaya admin untuk top up dengan syarat dan ketentuan serta kebijakan yang berlaku.​


Untuk meningkatkan kouta gratis top up kakak, silakan terus bertransaksi di apllikasi DANA ya kak."​

untuk case user terkena admin saat top up, berikut detail notif pada BO ya:

o MinToppUpAmountTimes : Pengguna akan dikenakan biaya apabila top up dibawah Rp50.000 Bank : BCA, BNI, BRI, CIMB, MANDIRI, BTPN, PERMATA, PANIN

o MaximumTopUpCount : Pengguna akan dikenakan biaya jika menerima top up sebanyak lebih dari 20 kali dari sumber VA yang sama (agen tidak resmi). Bank : BCA, BNI, BRI, MANDIRI, CIMB

o PayeeTopUpCount : Pengguna akan dikenakan biaya jika menerima top up sebanyak lebih dari 20 kali tanpa mempertimbangkan sumber VA yang sama (semua VA -> BCA, BNI, BRI, CIMB, MANDIRI, BTPN, PERMATA [prefix permata dapat menerima top up dari berbagai sumber])

o [NEW] TopUpCountbyInstId : Pengguna akan dikenakan biaya jika menerima top up sebanyak lebih dari 19 kali dari BCA dan BTPN

    """
    }
    
    print("📋 Original Message:")
    print(json.dumps(test_message, indent=2))
    print()
    
    # Test validation with original message
    try:
        validated_message = KnowledgeCreateMessage(**test_message)
        print("✅ Original message validation: PASSED")
        return True, None
    except ValidationError as e:
        print("❌ Original message validation: FAILED")
        print(f"Validation errors: {e}")
        
        # Try with corrected fileType
        corrected_message = test_message.copy()
        corrected_message["fileType"] = "image"  # Fix case
        
        print("\n🔧 Trying with corrected fileType (lowercase 'image'):")
        try:
            validated_message = KnowledgeCreateMessage(**corrected_message)
            print("✅ Corrected message validation: PASSED")
            print("\n📝 Recommended fix: Change 'IMAGE' to 'image' in fileType field")
            return True, corrected_message
        except ValidationError as e2:
            print("❌ Corrected message validation: FAILED")
            print(f"Validation errors: {e2}")
            return False, str(e2)

def test_mq_connectivity():
    """Test MQ connectivity using current environment"""
    print("\n🔌 Testing MQ Connectivity")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  No .env file found. Using .env.example as reference.")
        print("Please create a .env file with your actual MQ credentials.")
        return False
    
    try:
        # Try to initialize MQ handler
        mq_handler = MQHandler()
        print("✅ MQ Handler initialized successfully")
        
        # Test connection
        if hasattr(mq_handler, 'connection') and mq_handler.connection:
            print("✅ MQ Connection established")
            
            # Get connection info
            if hasattr(mq_handler.connection, 'params'):
                params = mq_handler.connection.params
                print(f"📡 Connected to: {params.host}:{params.port}")
                print(f"🏠 Virtual host: {params.virtual_host}")
            
            return True
        else:
            print("❌ MQ Connection failed - no connection object")
            return False
            
    except Exception as e:
        print(f"❌ MQ Connection failed: {str(e)}")
        print("\n💡 Troubleshooting tips:")
        print("1. Check your .env file has correct RABBITMQ_URL")
        print("2. Ensure RabbitMQ server is running and accessible")
        print("3. Verify credentials and network connectivity")
        return False

def main():
    """Main test function"""
    print("🚀 MQ Validation and Connectivity Test")
    print("=" * 60)
    
    # Test 1: Validate message format
    format_valid, corrected_msg = validate_message_format()
    
    # Test 2: Test connectivity
    connectivity_ok = test_mq_connectivity()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"Message Format: {'✅ VALID' if format_valid else '❌ INVALID'}")
    print(f"MQ Connectivity: {'✅ CONNECTED' if connectivity_ok else '❌ DISCONNECTED'}")
    
    if format_valid and corrected_msg:
        print("\n📝 Corrected Message Format:")
        print(json.dumps(corrected_msg, indent=2))

if __name__ == "__main__":
    main()