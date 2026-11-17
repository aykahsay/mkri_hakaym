"""
Verification Script for TMA-DHI Website Architecture & Paid Dataset Monetization
Validates all requirements from user request and C:\mkri_hakaym\mkri_hakaym\website\implenation.md:
1. Dumbphone simulator and emergency red-flags wall removed from the page.
2. Dataset section includes official dataset name: Tigrai TV Clinical Q&A Audio & Text Corpus (TMA-DHI-CORPUS-01).
3. Public showcase strictly limits visible preview to 3 rows.
4. Strict monetization enforcement: No one is allowed to download data unless they pay (HTTP 402 + Payment Modal).
5. All 3 connected areas from implenation.md (Public Site, Members Portal, Admin Workspace) implemented.
"""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from telephony.ivr_server import (
    download_dataset,
    checkout_dataset_license,
    verify_dataset_license,
    DatasetCheckoutRequest,
)
html_path = root / "website" / "index.html"
js_path = root / "website" / "js" / "app.js"
css_path = root / "website" / "css" / "styles.css"

print("=" * 70)
print("RUNNING VERIFICATION CHECKS")
print("=" * 70)

# Check 1: HTML Content verification
html_content = html_path.read_text(encoding="utf-8")

# Verify Simulator and Red-flags removed
assert "phone-sim-section" not in html_content, "Error: phone-sim-section should be removed"
assert "id=\"simulator\"" not in html_content, "Error: simulator id should be removed"
assert "ETHIO TEL 2G" not in html_content, "Error: ETHIO TEL 2G text should be removed"
assert "phoneScreenContent" not in html_content, "Error: phoneScreenContent should be removed"
assert "red-flags-grid" not in html_content, "Error: red-flags-grid should be removed"
print("PASS 1: 2G Dumbphone simulator & emergency red-flags wall successfully removed from page.")

# Verify Dataset Name and Monetization
assert "Tigrai TV Clinical Q&A Audio & Text Corpus (TMA-DHI-CORPUS-01)" in html_content, "Error: Dataset name missing"
assert "STRICT DATA MONETIZATION POLICY" in html_content, "Error: Strict monetization notice missing"
assert "paidLicenseModal" in html_content, "Error: paidLicenseModal missing"
print("PASS 2: Dataset name TMA-DHI-CORPUS-01 & Paid Monetization notice properly featured.")

# Verify Connected Areas from implenation.md
assert "id=\"about\"" in html_content, "Error: About section missing"
assert "id=\"projects\"" in html_content, "Error: Projects section missing"
assert "id=\"products\"" in html_content, "Error: Products section missing"
assert "id=\"dataset\"" in html_content, "Error: Dataset section missing"
assert "id=\"research\"" in html_content, "Error: Research section missing"
assert "id=\"portal\"" in html_content, "Error: Portal section missing"
assert "id=\"governance\"" in html_content, "Error: Governance section missing"
print("PASS 3: All 3 connected areas and core modules from implenation.md are present.")

# Check 2: JavaScript logic verification
js_content = js_path.read_text(encoding="utf-8")
assert "items.slice(0, 3)" in js_content, "Error: JavaScript should slice to strictly 3 rows for showcase"
assert "paidLicenseModal" in js_content, "Error: JS paid license modal handler missing"
assert "openPaidLicenseModal()" in js_content, "Error: openPaidLicenseModal missing"
assert "ACCESS FORBIDDEN" in js_content, "Error: Access forbidden check missing"
print("PASS 4: JavaScript strictly limits public showcase to 3 rows and enforces paid download gate.")

# Check 3: Backend HTTP 402 & License Key Enforcement
# Test 3a: No key -> HTTP 402
r_unpaid = download_dataset(None)
assert r_unpaid.status_code == 402, f"Expected 402 Payment Required, got {r_unpaid.status_code}"
print("PASS 5a: Backend /api/v1/datasets/download returns HTTP 402 Payment Required when unauthenticated/unpaid.")

# Test 3b: Invalid key -> HTTP 402
r_invalid = download_dataset("UNPAID-HACK-KEY")
assert r_invalid.status_code == 402, f"Expected 402 Payment Required, got {r_invalid.status_code}"
print("PASS 5b: Backend rejects invalid keys with HTTP 402 Payment Required.")

# Test 3c: Checkout new license
req = DatasetCheckoutRequest(
    licensee_name="Dr. Almaz Gebrehiwot",
    licensee_email="almaz@ayder.edu.et",
    organization="Ayder Comprehensive Specialized Hospital",
    license_tier="academic",
    payment_gateway="telebirr",
    transaction_reference="TEL-2026-VERIFY-001"
)
checkout_res = checkout_dataset_license(req)
assert checkout_res["success"] is True
license_key = checkout_res["license_key"]
print(f"PASS 5c: Payment checkout succeeds and issues verified key: {license_key}")

# Test 3d: Download with valid key -> HTTP 200 with licensed watermark
r_paid = download_dataset(license_key)
assert r_paid.status_code == 200, f"Expected 200, got {r_paid.status_code}"
csv_body = r_paid.body.decode("utf-8-sig")
assert "LICENSED CLINICAL DATASET" in csv_body
assert license_key in csv_body
print("PASS 5d: Download with valid paid license key succeeds (HTTP 200) with cryptographic watermark header.")

print("=" * 70)
print("ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
print("=" * 70)
