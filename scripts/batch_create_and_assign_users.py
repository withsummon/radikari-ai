#!/usr/bin/env python3
"""
Batch create users (user2@test.com .. user50@test.com) and assign them to a tenant.

Steps:
1) POST /users to create each user and collect the returned user ID.
2) PUT /tenants/{tenantId}/users with an array of objects, one per userId.

All fixed values and endpoints are taken from the user's provided examples.
"""

import time
import json
import sys
from typing import List
import requests

BASE_URL = "https://radikari-be.withsummon.com"
CREATE_USER_ENDPOINT = f"{BASE_URL}/users"
TENANT_ID = "01K9201Z97H20E4NKTEANCFVCP"
ASSIGN_USERS_ENDPOINT = f"{BASE_URL}/tenants/{TENANT_ID}/users"

# Authorization token provided by the user (use exactly as given)
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjAxSzkyMDFCTVA5UFQ2S0ExRVhFU0s3QjZCIiwiZnVsbE5hbWUiOiJBZG1pbiIsImVtYWlsIjoiYWRtaW5AdGVzdC5jb20iLCJwaG9uZU51bWJlciI6Ii0iLCJyb2xlIjoiQURNSU4iLCJ0eXBlIjoiSU5URVJOQUwiLCJjcmVhdGVkQXQiOiIyMDI1LTExLTAyVDA5OjU4OjA2Ljc0NFoiLCJ1cGRhdGVkQXQiOiIyMDI1LTExLTAyVDA5OjU4OjA2Ljc0NFoiLCJpYXQiOjE3NjIyMjk5NjksImV4cCI6MTc2MjMxNjM2OX0.VWl4dgCzM3MYrLCou8Uh8t3uuqgRjvUqdj6-1Fa1jx4"

HEADERS_JSON = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}",
}

# Tenant assignment fixed values from the user's example
TENANT_ROLE_ID = "01K9201BYQKF3FGXTW1878YVZV"
HEAD_OF_OPERATION_USER_ID = "01K9201BMP9PT6KA1EXESK7B6B"
TEAM_LEADER_USER_ID = ""
SUPERVISOR_USER_ID = ""
MANAGER_USER_ID = ""

START_INDEX = 2  # user2@test.com
END_INDEX = 50   # up to and including user50@test.com
CREATE_DELAY_SECONDS = 0.2  # small delay to avoid rate limits


def create_user(i: int) -> str:
    """Create a single user and return its ID (or None on failure)."""
    payload = {
        "fullName": f"User {i}",
        "email": f"user{i}@test.com",
        "password": "user123",
        "phoneNumber": "08172623812932",
    }
    try:
        resp = requests.post(CREATE_USER_ENDPOINT, headers=HEADERS_JSON, json=payload, timeout=20)
        if resp.status_code >= 200 and resp.status_code < 300:
            data = resp.json()
            user_id = data.get("content", {}).get("id")
            if not user_id:
                print(f"[WARN] Created user{i} but no ID found in response: {json.dumps(data)[:200]}...")
                return None
            print(f"[OK] Created user{i}@test.com → ID={user_id}")
            return user_id
        else:
            print(f"[ERR] Failed to create user{i}@test.com: HTTP {resp.status_code} → {resp.text[:200]}...")
            return None
    except Exception as e:
        print(f"[ERR] Exception creating user{i}@test.com: {e}")
        return None


def build_assign_array(user_ids: List[str]) -> List[dict]:
    """Build the array payload for tenant assignment."""
    entries = []
    for uid in user_ids:
        entries.append({
            "tenantRoleId": TENANT_ROLE_ID,
            "userId": uid,
            "headOfOperationUserId": HEAD_OF_OPERATION_USER_ID,
            "teamLeaderUserId": TEAM_LEADER_USER_ID,
            "supervisorUserId": SUPERVISOR_USER_ID,
            "managerUserId": MANAGER_USER_ID,
        })
    return entries


def assign_users_to_tenant(user_ids: List[str]) -> bool:
    """PUT array of user assignments into the tenant."""
    if not user_ids:
        print("[WARN] No user IDs to assign; skipping tenant assignment.")
        return False

    payload = build_assign_array(user_ids)
    try:
        resp = requests.put(ASSIGN_USERS_ENDPOINT, headers=HEADERS_JSON, json=payload, timeout=30)
        if resp.status_code >= 200 and resp.status_code < 300:
            print(f"[OK] Assigned {len(user_ids)} users to tenant {TENANT_ID}.")
            try:
                print(f"Response: {json.dumps(resp.json())}")
            except Exception:
                print(f"Response (text): {resp.text[:500]}")
            return True
        else:
            print(f"[ERR] Failed to assign users: HTTP {resp.status_code} → {resp.text[:500]}")
            return False
    except Exception as e:
        print(f"[ERR] Exception assigning users: {e}")
        return False


def main():
    print(f"Starting batch creation: user{START_INDEX}@test.com .. user{END_INDEX}@test.com")
    created_ids: List[str] = []

    for i in range(START_INDEX, END_INDEX + 1):
        uid = create_user(i)
        if uid:
            created_ids.append(uid)
        time.sleep(CREATE_DELAY_SECONDS)

    print(f"\nSummary: Created {len(created_ids)} users out of {END_INDEX - START_INDEX + 1}")

    print("\nAssigning users to tenant...")
    assigned = assign_users_to_tenant(created_ids)

    print("\nDone.")
    if not assigned:
        sys.exit(1)


if __name__ == "__main__":
    main()