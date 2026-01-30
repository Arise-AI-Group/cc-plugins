# DOCX XML Reference

## File Structure

A DOCX file is a ZIP archive containing:

```
[Content_Types].xml      # Content type definitions
_rels/.rels              # Package relationships
word/
  document.xml           # Main document content
  styles.xml             # Style definitions
  settings.xml           # Document settings
  fontTable.xml          # Font information
  comments.xml           # Comments (if present)
  commentsExtended.xml   # Threaded comments
  header1.xml            # Headers
  footer1.xml            # Footers
  _rels/
    document.xml.rels    # Document relationships
```

## Namespaces

```xml
xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
```

## Schema Compliance

### Element Order in `<w:pPr>`

Elements must appear in this order:
1. `<w:pStyle>`
2. `<w:numPr>`
3. `<w:spacing>`
4. `<w:ind>`
5. `<w:jc>`
6. `<w:rPr>` (last)

### Whitespace Preservation

Add `xml:space="preserve"` to `<w:t>` elements with leading/trailing spaces:

```xml
<w:t xml:space="preserve"> text with spaces </w:t>
```

### RSIDs

Revision save IDs must be 8-digit hex: `00AB1234`

---

## Document Structure

### Paragraph

```xml
<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading1"/>
    <w:jc w:val="center"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:b/>
      <w:sz w:val="24"/>
    </w:rPr>
    <w:t>Text content</w:t>
  </w:r>
</w:p>
```

### Run with Formatting

```xml
<w:r>
  <w:rPr>
    <w:b/>              <!-- Bold -->
    <w:i/>              <!-- Italic -->
    <w:u w:val="single"/>  <!-- Underline -->
    <w:sz w:val="24"/>  <!-- Font size (half-points, 24 = 12pt) -->
    <w:rFonts w:ascii="Arial"/>
  </w:rPr>
  <w:t>Formatted text</w:t>
</w:r>
```

### Lists

```xml
<w:p>
  <w:pPr>
    <w:numPr>
      <w:ilvl w:val="0"/>      <!-- Indentation level -->
      <w:numId w:val="1"/>     <!-- List ID -->
    </w:numPr>
  </w:pPr>
  <w:r><w:t>List item</w:t></w:r>
</w:p>
```

---

## Tracked Changes XML

### Insertion

```xml
<w:ins w:id="1" w:author="Author Name" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><!-- copy formatting from original --></w:rPr>
    <w:t>inserted text</w:t>
  </w:r>
</w:ins>
```

### Deletion

```xml
<w:del w:id="2" w:author="Author Name" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><!-- copy formatting from original --></w:rPr>
    <w:delText>deleted text</w:delText>
  </w:r>
</w:del>
```

### Paragraph Mark Deletion

When deleting an entire paragraph, mark the paragraph end:

```xml
<w:pPr>
  <w:rPr>
    <w:del w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
  </w:rPr>
</w:pPr>
```

### Formatting Changes

```xml
<w:rPr>
  <w:rPrChange w:id="3" w:author="Author" w:date="...">
    <w:rPr>
      <!-- original formatting -->
    </w:rPr>
  </w:rPrChange>
</w:rPr>
```

---

## Comments XML

### comments.xml

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="...">
  <w:comment w:id="0" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:p>
      <w:r><w:t>Comment text here</w:t></w:r>
    </w:p>
  </w:comment>
</w:comments>
```

### commentsExtended.xml (for replies)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w15:commentsEx xmlns:w15="...">
  <w15:commentEx w15:paraId="00000001" w15:paraIdParent="00000000" w15:done="0"/>
</w15:commentsEx>
```

### Comment Markers in document.xml

```xml
<w:commentRangeStart w:id="0"/>
<w:r><w:t>commented text</w:t></w:r>
<w:commentRangeEnd w:id="0"/>
<w:r>
  <w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>
  <w:commentReference w:id="0"/>
</w:r>
```

---

## Images

### In document.xml

```xml
<w:drawing>
  <wp:inline>
    <wp:extent cx="914400" cy="914400"/>  <!-- EMUs: 914400 = 1 inch -->
    <a:graphic>
      <a:graphicData uri="...">
        <pic:pic>
          <pic:blipFill>
            <a:blip r:embed="rId5"/>
          </pic:blipFill>
        </pic:pic>
      </a:graphicData>
    </a:graphic>
  </wp:inline>
</w:drawing>
```

### In document.xml.rels

```xml
<Relationship Id="rId5"
  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
  Target="media/image1.png"/>
```

### In [Content_Types].xml

```xml
<Default Extension="png" ContentType="image/png"/>
```

---

## Units

| Unit | Description | Conversion |
|------|-------------|------------|
| DXA (twips) | 1/20 of a point | 1440 DXA = 1 inch |
| EMU | English Metric Unit | 914400 EMU = 1 inch |
| Half-points | Font size unit | 24 = 12pt |

Common page sizes in DXA:
- US Letter: 12240 x 15840
- A4: 11906 x 16838
