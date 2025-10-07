# 📄 How to View the Sample PDFs

## ✅ **PDFs You Can View**

All sample PDFs are in the `samples/` directory:

```bash
ls -lh samples/*.pdf
```

**Available PDFs:**
1. **280-utility-construction-plans.pdf** (3.8MB) - Main test PDF with utility networks
2. **bid_test.pdf** (3.8MB) - Copy of utility plans  
3. **sample.pdf** (5.2KB) - Small test file

---

## 🖥️ **Method 1: Open in Your PDF Viewer** (Easiest)

### macOS:
```bash
# Open the main utility plans
open samples/280-utility-construction-plans.pdf

# Or use Preview
open -a Preview samples/280-utility-construction-plans.pdf
```

### Linux:
```bash
# Use default PDF viewer
xdg-open samples/280-utility-construction-plans.pdf

# Or specific viewers
evince samples/280-utility-construction-plans.pdf
okular samples/280-utility-construction-plans.pdf
```

### Windows:
```bash
# Open in default PDF viewer
start samples/280-utility-construction-plans.pdf
```

---

## 🌐 **Method 2: View in Browser via Python**

Start a simple HTTP server to view PDFs in your browser:

```bash
# Start HTTP server in samples directory
cd samples
python3 -m http.server 8080

# Then open in browser:
# http://localhost:8080/280-utility-construction-plans.pdf
```

---

## 🔍 **What's In These PDFs**

### **280-utility-construction-plans.pdf** (THE MAIN ONE)

This is the PDF the system is currently configured to process. It contains:

- ✅ **Vector Geometry**: True CAD-drawn lines (not rasterized images)
- ✅ **Scale Information**: "1 inch = 20 feet" or similar
- ✅ **Utility Networks**:
  - Sanitary sewer lines
  - Storm drain lines  
  - Water lines
- ✅ **Annotations**: Pipe sizes, materials, slopes
- ✅ **Real-world Data**: Actual construction plans

**This PDF is what gets processed when you:**
- Run the ground truth test
- Use the demo project
- Test the agent API

---

## 📊 **Current Configuration**

### What the System Uses:

```bash
# Check what PDF is in the demo project:
cat backend/artifacts/demo/ingest/ingest_manifest.json | jq -r '.items[] | select(.status == "indexed" and (.filename | test("\\.pdf$"; "i"))) | {filename, indexed_at}' | jq -s 'sort_by(.indexed_at) | last'
```

**Currently configured:**
- **Demo Project**: Uses latest indexed PDF from `backend/artifacts/demo/ingest/raw/`
- **Ground Truth Test**: Uses `samples/280-utility-construction-plans.pdf`
- **Direct Agent API**: Uses whatever PDF you upload

---

## 🎯 **Quick View Commands**

```bash
# View the main utility plans PDF
open samples/280-utility-construction-plans.pdf

# See PDF metadata
file samples/280-utility-construction-plans.pdf
pdfinfo samples/280-utility-construction-plans.pdf  # if you have poppler-utils

# Check file size
ls -lh samples/280-utility-construction-plans.pdf

# View all sample PDFs
ls -lh samples/*.pdf

# Open all PDFs at once (macOS)
open samples/*.pdf
```

---

## 📝 **PDF Details**

| PDF | Size | Pages | Content | Purpose |
|-----|------|-------|---------|---------|
| 280-utility-construction-plans.pdf | 3.8MB | ~10 | Full utility plans with sanitary/storm/water networks | Main test PDF |
| bid_test.pdf | 3.8MB | ~10 | Copy of 280 utility plans | Backup/testing |
| sample.pdf | 5KB | 1 | Simple test file | Quick tests |

---

## 🔧 **Troubleshooting**

### "I don't see the PDFs"
```bash
# Check if samples directory exists
ls -la samples/

# Check if PDFs are there
ls -lh samples/*.pdf

# If missing, they might be in a different location:
find . -name "*.pdf" -type f | head -10
```

### "PDF won't open"
```bash
# Check file integrity
file samples/280-utility-construction-plans.pdf
# Should output: "PDF document, version X.X"

# Check permissions
ls -l samples/280-utility-construction-plans.pdf
# Should be readable (r--)
```

### "I want to replace the PDF"
```bash
# Copy your PDF to samples
cp /path/to/your/construction-plans.pdf samples/my-plans.pdf

# Update golden reference to use it
# Edit: backend/tests/golden_reference.json
# Change: "pdf_file": "samples/my-plans.pdf"
```

---

## 🚀 **Testing With These PDFs**

### Test the Agent API:
```bash
curl -s "http://localhost:8000/v1/agent/takeoff" \
  -F "session_id=test" \
  -F "file=@samples/280-utility-construction-plans.pdf" \
| jq '.summary'
```

### Run Ground Truth:
```bash
./scripts/compare_ground_truth.sh
```

### Ingest Into Demo Project:
```bash
curl -F "files=@samples/280-utility-construction-plans.pdf" \
  "http://localhost:8000/api/projects/demo/ingest"
```

---

**The PDFs are ready to view! Just use `open samples/280-utility-construction-plans.pdf` on macOS or your OS equivalent.** 📄

