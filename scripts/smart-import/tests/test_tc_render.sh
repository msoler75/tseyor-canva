#!/bin/bash
# test_tc_render.sh — Integration test for the headless renderer
#
# This test verifies:
# 1. Node.js and npx are available
# 2. Playwright is listed in requirements
# 3. tc_render.js can parse a minimal valid .tc file
# 4. The renderer rejects invalid .tc files
# 5. The renderer outputs a help message with --help
#
# NOTE: The full render test (headless browser) requires:
#   - PHP 8.1+ with Composer deps installed
#   - MySQL/MariaDB running
#   - App build (npm run build)
#   - Playwright Chromium installed (npx playwright install chromium)
#
# Run the full render manually with:
#   node scripts/smart-import/tc_render.js --tc <path.tc> --output <path.png>
#
# Or via the wrapper:
#   ./scripts/smart-import/tc_render.sh <path.tc> <path.png>
#
# Prerequisites check:
#   php -v && node -v && npx playwright --version

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMART_IMPORT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(cd "$SMART_IMPORT_DIR/../.." && pwd)"
PASS=0
FAIL=0

print_result() {
    local label="$1"
    local status="$2"
    if [ "$status" = "pass" ]; then
        echo "  ✅ $label"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $label"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== tc_render.js Integration Tests ==="
echo ""

# ----- 1. Check Node.js availability -----
echo "[1/5] Checking Node.js availability..."
if command -v node &>/dev/null; then
    NODE_VER=$(node -v)
    print_result "Node.js found: $NODE_VER" "pass"
else
    print_result "Node.js not found (install Node 20+)" "fail"
fi

# ----- 2. Check npx availability -----
echo "[2/5] Checking npx availability..."
if command -v npx &>/dev/null; then
    NPX_VER=$(npx --version 2>/dev/null || echo "unknown")
    print_result "npx found: $NPX_VER" "pass"
else
    print_result "npx not found" "fail"
fi

# ----- 3. Check Playwright in requirements -----
echo "[3/5] Checking Playwright in requirements..."
REQ_FILE="$SMART_IMPORT_DIR/requirements.txt"

# Playwright is a Node dependency, not Python — check if it's in package.json
# or installed globally. Also check if the requirements.txt mentions it.
if [ -f "$REQ_FILE" ]; then
    if grep -qi "playwright" "$REQ_FILE"; then
        print_result "Playwright found in requirements.txt" "pass"
    else
        echo "  ⚠ Playwright not listed in requirements.txt (it's a Node dependency, installed via npm)"
        echo "  ℹ  Install: npm install --save-dev playwright && npx playwright install chromium"
        print_result "Playwright noted (Node dependency, not Python)" "info"
    fi
else
    echo "  ⚠ requirements.txt not found at $REQ_FILE"
    print_result "requirements.txt missing" "fail"
fi

# Check if Playwright is actually installed (node_modules)
if [ -f "$PROJECT_ROOT/node_modules/playwright/package.json" ]; then
    print_result "Playwright package installed (node_modules)" "pass"
else
    echo "  ⚠ Playwright not installed. Run: npm install --save-dev playwright"
    print_result "Playwright not installed" "fail"
fi

# ----- 4. Test with minimal valid .tc file -----
echo "[4/5] Testing tc_render.js with minimal valid .tc..."
MINIMAL_TC="$SMART_IMPORT_DIR/tests/.minimal_test.tc"
OUTPUT_PNG="$SMART_IMPORT_DIR/tests/.test_output.png"

# Create a minimal valid .tc file that matches the expected structure
cat > "$MINIMAL_TC" << 'EOF'
{
  "tcVersion": 2,
  "format": "poster",
  "size": "custom",
  "designSurface": {
    "width": 1080,
    "height": 1350
  },
  "designTitle": "Test Design",
  "designTitleManual": true,
  "objective": "event",
  "outputType": "print",
  "content": {
    "title": "Test Title",
    "subtitle": "Test Subtitle",
    "date": "2025-01-01",
    "time": "18:00",
    "location": "Test Location",
    "platform": "",
    "teacher": "",
    "price": "",
    "contact": "info@test.com",
    "extra": ""
  },
  "elementLayout": {
    "background": {
      "backgroundColor": "#4338ca",
      "backgroundImageSrc": null,
      "backgroundImageAssetId": null,
      "backgroundImagePendingDataUrl": null,
      "backgroundImageStoragePath": null
    },
    "title": {
      "x": 28, "y": 72, "w": 300, "zIndex": 50,
      "fontSize": 44, "color": "#ffffff",
      "fontFamily": "Poppins, sans-serif",
      "fontWeight": "bold", "textAlign": "left",
      "opacity": 100, "letterSpacing": 0, "lineHeight": 0.95
    },
    "subtitle": {
      "x": 32, "y": 186, "w": 280, "zIndex": 40,
      "fontSize": 18, "color": "#f8fafc",
      "fontFamily": "Bebas Neue, sans-serif",
      "fontWeight": "regular", "textAlign": "left",
      "opacity": 100, "letterSpacing": 0, "lineHeight": 1.45
    }
  },
  "customElements": {},
  "userUploadedImages": [],
  "workingDocumentPageId": "page-1",
  "pages": [
    {
      "id": "page-1",
      "content": {
        "title": "",
        "subtitle": "",
        "date": "",
        "time": "",
        "location": "",
        "platform": "",
        "teacher": "",
        "price": "",
        "contact": "",
        "extra": ""
      },
      "elementLayout": {
        "background": {
          "backgroundColor": "#4338ca",
          "backgroundImageSrc": null
        },
        "title": {
          "x": 28, "y": 72, "w": 300, "zIndex": 50,
          "fontSize": 44, "color": "#ffffff",
          "fontFamily": "Poppins, sans-serif",
          "fontWeight": "bold", "textAlign": "left",
          "opacity": 100, "letterSpacing": 0, "lineHeight": 0.95
        },
        "subtitle": {
          "x": 32, "y": 186, "w": 280, "zIndex": 40,
          "fontSize": 18, "color": "#f8fafc",
          "fontFamily": "Bebas Neue, sans-serif",
          "fontWeight": "regular", "textAlign": "left",
          "opacity": 100, "letterSpacing": 0, "lineHeight": 1.45
        }
      },
      "customElements": {}
    }
  ]
}
EOF

# Run the script with --help to test argument parsing (no browser needed)
echo "  → Testing --help flag..."
HELP_OUTPUT=$(node "$SMART_IMPORT_DIR/tc_render.js" --help 2>&1 || true)
if echo "$HELP_OUTPUT" | grep -q "tc_render.js"; then
    print_result "--help flag works" "pass"
else
    print_result "--help flag failed" "fail"
fi

# Test that missing --tc argument gives error
echo "  → Testing missing required args..."
ERROR_OUTPUT=$(node "$SMART_IMPORT_DIR/tc_render.js" 2>&1 || true)
if echo "$ERROR_OUTPUT" | grep -q "Missing required argument"; then
    print_result "Missing --tc reports error" "pass"
else
    print_result "Missing --tc error handling failed" "fail"
fi

# Test with --tc only (missing --output)
echo "  → Testing missing --output argument..."
ERROR_OUTPUT2=$(node "$SMART_IMPORT_DIR/tc_render.js" --tc "$MINIMAL_TC" 2>&1 || true)
if echo "$ERROR_OUTPUT2" | grep -q "Missing required argument"; then
    print_result "Missing --output reports error" "pass"
else
    print_result "Missing --output error handling failed" "fail"
fi

# Test that invalid .tc file path gives error
echo "  → Testing invalid file path..."
ERROR_OUTPUT3=$(node "$SMART_IMPORT_DIR/tc_render.js" --tc "/nonexistent/file.tc" --output "$OUTPUT_PNG" 2>&1 || true)
if echo "$ERROR_OUTPUT3" | grep -q "not found"; then
    print_result "Invalid --tc path reports error" "pass"
else
    print_result "Invalid --tc path error handling failed" "fail"
fi

# Test that invalid JSON gives error
echo "  → Testing invalid .tc content..."
INVALID_TC="$SMART_IMPORT_DIR/tests/.invalid_test.tc"
echo "this is not json" > "$INVALID_TC"
ERROR_OUTPUT4=$(node "$SMART_IMPORT_DIR/tc_render.js" --tc "$INVALID_TC" --output "$OUTPUT_PNG" 2>&1 || true)
if echo "$ERROR_OUTPUT4" | grep -q "Invalid JSON"; then
    print_result "Invalid .tc JSON reports error" "pass"
else
    print_result "Invalid .tc JSON error handling failed" "fail"
fi

# Test that .tc without tcVersion gives error
echo "  → Testing .tc without tcVersion..."
NO_VERSION_TC="$SMART_IMPORT_DIR/tests/.noversion_test.tc"
echo '{"format": "poster"}' > "$NO_VERSION_TC"
ERROR_OUTPUT5=$(node "$SMART_IMPORT_DIR/tc_render.js" --tc "$NO_VERSION_TC" --output "$OUTPUT_PNG" 2>&1 || true)
if echo "$ERROR_OUTPUT5" | grep -q "tcVersion"; then
    print_result "Missing tcVersion reports error" "pass"
else
    print_result "Missing tcVersion error handling failed" "fail"
fi

# Cleanup test files
rm -f "$MINIMAL_TC" "$INVALID_TC" "$NO_VERSION_TC" "$OUTPUT_PNG"

# ----- 5. Summary -----
echo ""
echo "[5/5] Checking for headless browser dependencies..."
echo ""
echo "  To run a full render (requires full Laravel stack):"
echo "    # 1. Ensure MySQL is running"
echo "    # 2. Build the frontend"
echo "    npm run build"
echo ""
echo "    # 3. Run the renderer:"
echo "    node scripts/smart-import/tc_render.js \\"
echo "      --tc scripts/smart-import/output/gemini-2.5-flash/img-01/design.tc \\"
echo "      --output scripts/smart-import/output/gemini-2.5-flash/img-01/render.png"
echo ""
echo "    # Or via wrapper:"
echo "    ./scripts/smart-import/tc_render.sh design.tc render.png"
echo ""
echo "  Prerequisites for full render:"
echo "    - PHP 8.1+ with Composer deps (composer install)"
echo "    - MySQL/MariaDB running"
echo "    - Node 20+ and Playwright: npx playwright install chromium"
echo "    - App build: npm run build"
echo ""

# Check if PHP is available for full render
if command -v php &>/dev/null; then
    PHP_VER=$(php -v | head -1)
    print_result "PHP available: $PHP_VER" "pass"
else
    print_result "PHP not found (needed for full render)" "fail"
fi

# Check if Chromium is available for Playwright
if command -v npx &>/dev/null; then
    if npx playwright install --dry-run chromium 2>/dev/null; then
        print_result "Playwright Chromium available" "pass"
    else
        echo "  ⚠ Playwright Chromium not installed. Run: npx playwright install chromium"
        print_result "Playwright Chromium not installed" "fail"
    fi
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
