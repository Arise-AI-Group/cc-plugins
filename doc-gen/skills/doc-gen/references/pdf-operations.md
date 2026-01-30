# PDF Operations Reference

## Python Libraries

### pypdf - Basic Operations

```python
from pypdf import PdfReader, PdfWriter

# Read PDF
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text
for page in reader.pages:
    text = page.extract_text()
```

#### Merge PDFs

```python
writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

#### Split PDF

```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Rotate Pages

```python
reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
page.rotate(90)  # Clockwise
writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

#### Metadata

```python
reader = PdfReader("document.pdf")
meta = reader.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
```

---

### pdfplumber - Text and Table Extraction

#### Extract Text with Layout

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

#### Extract Tables

```python
with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                print(row)
```

#### Tables to DataFrame

```python
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

combined = pd.concat(all_tables, ignore_index=True)
combined.to_excel("tables.xlsx", index=False)
```

---

### reportlab - Create PDFs

#### Basic PDF

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

c.drawString(100, height - 100, "Hello World!")
c.line(100, height - 120, 400, height - 120)
c.save()
```

#### Multi-page Document

```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

story.append(Paragraph("Report Title", styles['Title']))
story.append(Spacer(1, 12))
story.append(Paragraph("Body text here.", styles['Normal']))
story.append(PageBreak())
story.append(Paragraph("Page 2", styles['Heading1']))

doc.build(story)
```

---

## CLI Tool Usage

### pdf_tools.py Commands

```bash
# Merge
./run tool/pdf_tools.py merge file1.pdf file2.pdf -o merged.pdf

# Split all pages
./run tool/pdf_tools.py split document.pdf -o pages/

# Split specific pages
./run tool/pdf_tools.py split document.pdf -o pages/ --pages "1-3,5,7-10"

# Extract text
./run tool/pdf_tools.py extract-text document.pdf
./run tool/pdf_tools.py extract-text document.pdf --pages "1-5"

# Extract tables as JSON
./run tool/pdf_tools.py extract-tables document.pdf

# Extract tables as CSV
./run tool/pdf_tools.py extract-tables document.pdf --format csv -o tables/

# Rotate
./run tool/pdf_tools.py rotate document.pdf -o rotated.pdf --angle 90
./run tool/pdf_tools.py rotate document.pdf -o rotated.pdf --pages "2,4" --angle 180

# Get metadata
./run tool/pdf_tools.py metadata document.pdf
```

---

## Common Tasks

### Add Watermark

```python
from pypdf import PdfReader, PdfWriter

watermark = PdfReader("watermark.pdf").pages[0]
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Password Protection

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

writer.encrypt("userpassword", "ownerpassword")

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

### Remove Password

```bash
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

---

## Quick Reference

| Task | Tool | Method |
|------|------|--------|
| Merge | pypdf | `writer.add_page(page)` |
| Split | pypdf | One page per file |
| Extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Rotate | pypdf | `page.rotate(angle)` |
| Metadata | pypdf | `reader.metadata` |
| CLI merge | qpdf | `qpdf --empty --pages ...` |
