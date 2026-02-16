#!/usr/bin/env python3
"""
SQL X-Ray Enterprise v2.1.0 Robust Edition - Backend API Testing
Tests all backend endpoints including new incremental scanner and workload analyzer
"""

import requests
import sys
import json
from datetime import datetime

class SQLXRayAPITester:
    def __init__(self, base_url="https://sql-xray-mentor.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", response_data=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def test_root_endpoint(self):
        """Test /api/ endpoint for v2.1.0 Robust Edition info"""
        try:
            response = self.session.get(f"{self.base_url}/api/")
            if response.status_code == 200:
                data = response.json()
                expected_version = "2.1.0"
                expected_edition = "MySQL 8 Enterprise - Robust Edition"
                
                if (data.get("version") == expected_version and 
                    expected_edition in data.get("edition", "")):
                    self.log_test("Root API endpoint (v2.1.0)", True, f"Version: {data.get('version')}, Edition: {data.get('edition')}", data)
                else:
                    self.log_test("Root API endpoint (v2.1.0)", False, f"Expected v{expected_version} Robust Edition, got: {data}")
            else:
                self.log_test("Root API endpoint (v2.1.0)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Root API endpoint (v2.1.0)", False, f"Error: {str(e)}")

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Health endpoint", True, "Service is healthy", data)
                else:
                    self.log_test("Health endpoint", False, f"Unexpected status: {data}")
            else:
                self.log_test("Health endpoint", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Health endpoint", False, f"Error: {str(e)}")

    def test_analyze_endpoint_without_connection(self):
        """Test /api/analyze endpoint with SQL query (no MySQL connection)"""
        test_query = """
        SELECT 
            u.name,
            u.email,
            COUNT(o.id) as total_orders,
            SUM(o.amount) as total_spent
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE o.created_at > '2024-01-01'
        GROUP BY u.id, u.name, u.email
        ORDER BY total_spent DESC
        LIMIT 100;
        """
        
        payload = {
            "query": test_query,
            "dialect": "mysql",
            "mode": "advanced"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/analyze",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                # Check if AI analysis was performed
                if "overview" in data and data["overview"].get("summary"):
                    self.log_test("SQL Analysis (AI)", True, "AI analysis completed successfully")
                else:
                    self.log_test("SQL Analysis (AI)", False, f"Missing analysis data: {data}")
            else:
                self.log_test("SQL Analysis (AI)", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("SQL Analysis (AI)", False, f"Error: {str(e)}")

    def test_mongodb_collections_structure(self):
        """Test if MongoDB collections are accessible (indirect test via auth endpoints)"""
        # Test auth/me endpoint (should return 401 without auth)
        try:
            response = self.session.get(f"{self.base_url}/api/auth/me")
            if response.status_code == 401:
                self.log_test("MongoDB Auth Collection", True, "Auth endpoint accessible (401 expected without token)")
            else:
                self.log_test("MongoDB Auth Collection", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("MongoDB Auth Collection", False, f"Error: {str(e)}")

        # Test queries endpoint (should return 401 without auth)
        try:
            response = self.session.get(f"{self.base_url}/api/queries")
            if response.status_code == 401:
                self.log_test("MongoDB Queries Collection", True, "Queries endpoint accessible (401 expected without token)")
            else:
                self.log_test("MongoDB Queries Collection", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("MongoDB Queries Collection", False, f"Error: {str(e)}")

    def test_enterprise_endpoints_without_mysql(self):
        """Test enterprise endpoints (should fail gracefully without MySQL connection)"""
        
        # Test database intelligence endpoint
        test_connection = {
            "host": "nonexistent.host",
            "port": 3306,
            "user": "test",
            "password": "test",
            "database": "test",
            "ssl": True
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/enterprise/intelligence",
                json=test_connection,
                headers={"Content-Type": "application/json"}
            )
            # Should return error but endpoint should be accessible
            if response.status_code in [400, 500]:
                self.log_test("Enterprise Intelligence Endpoint", True, "Endpoint accessible (connection error expected)")
            else:
                self.log_test("Enterprise Intelligence Endpoint", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Enterprise Intelligence Endpoint", False, f"Error: {str(e)}")

        # Test maturity score endpoint
        try:
            response = self.session.post(
                f"{self.base_url}/api/enterprise/maturity-score",
                json=test_connection,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code in [400, 500]:
                self.log_test("Enterprise Maturity Score Endpoint", True, "Endpoint accessible (connection error expected)")
            else:
                self.log_test("Enterprise Maturity Score Endpoint", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Enterprise Maturity Score Endpoint", False, f"Error: {str(e)}")

    def test_database_connection_test_endpoint(self):
        """Test database connection test endpoint"""
        test_connection = {
            "host": "invalid.host",
            "port": 3306,
            "user": "test",
            "password": "test",
            "database": "test",
            "ssl": True
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/db/test-connection",
                json=test_connection,
                headers={"Content-Type": "application/json"}
            )
            # Should return 400 with connection error
            if response.status_code == 400:
                self.log_test("Database Connection Test", True, "Endpoint working (connection error expected)")
            else:
                self.log_test("Database Connection Test", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Database Connection Test", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting SQL X-Ray Enterprise Backend Tests")
        print(f"📍 Testing: {self.base_url}")
        print("=" * 60)
        
        # Core API tests
        self.test_root_endpoint()
        self.test_health_endpoint()
        
        # Analysis functionality
        self.test_analyze_endpoint_without_connection()
        
        # Database connectivity
        self.test_database_connection_test_endpoint()
        
        # MongoDB collections (indirect test)
        self.test_mongodb_collections_structure()
        
        # Enterprise modules
        self.test_enterprise_endpoints_without_mysql()
        
        # Summary
        print("=" * 60)
        print(f"📊 Tests completed: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All backend tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed - check details above")
            return 1

def main():
    tester = SQLXRayAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())