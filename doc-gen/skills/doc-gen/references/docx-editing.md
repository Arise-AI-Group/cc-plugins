# DOCX Editing Reference

## Unpack/Edit/Pack Workflow

### Step 1: Unpack

```bash
./run tool/office/unpack.py document.docx unpacked/
```

This:
- Extracts the DOCX (ZIP archive) to a directory
- Pretty-prints XML for readability
- Merges adjacent runs with identical formatting
- Converts smart quotes to XML entities

Use `--merge-runs false` to skip run merging.

### Step 2: Edit XML

Edit files in `unpacked/word/`. The main content is in `document.xml`.

**Use "Claude" as the author** for tracked changes and comments, unless specified otherwise.

**Use the Edit tool directly** for string replacement. Do not write Python scripts.

**Use smart quotes for new content:**
```xml
<w:t>Here&#x2019;s a quote: &#x201C;Hello&#x201D;</w:t>
```

| Entity | Character |
|--------|-----------|
| `&#x2018;` | ' (left single) |
| `&#x2019;` | ' (right single / apostrophe) |
| `&#x201C;` | " (left double) |
| `&#x201D;` | " (right double) |

### Step 3: Pack

```bash
./run tool/office/pack.py unpacked/ output.docx
```

Auto-repairs:
- `durableId` values >= 0x7FFFFFFF (regenerates valid ID)
- Missing `xml:space="preserve"` on `<w:t>` with whitespace

Use `--validate false` to skip validation.

---

## Tracked Changes

### Insertion

```xml
<w:ins w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:t>inserted text</w:t></w:r>
</w:ins>
```

### Deletion

```xml
<w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
```

**Inside `<w:del>`**: Use `<w:delText>` instead of `<w:t>`.

### Minimal Edits

Only mark what changes:

```xml
<!-- Change "30 days" to "60 days" -->
<w:r><w:t>The term is </w:t></w:r>
<w:del w:id="1" w:author="Claude" w:date="...">
  <w:r><w:delText>30</w:delText></w:r>
</w:del>
<w:ins w:id="2" w:author="Claude" w:date="...">
  <w:r><w:t>60</w:t></w:r>
</w:ins>
<w:r><w:t> days.</w:t></w:r>
```

### Deleting Entire Paragraphs

When removing ALL content from a paragraph, also mark the paragraph mark as deleted:

```xml
<w:p>
  <w:pPr>
    <w:rPr>
      <w:del w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:r><w:delText>Entire paragraph being deleted...</w:delText></w:r>
  </w:del>
</w:p>
```

### Rejecting Another Author's Insertion

Nest deletion inside their insertion:

```xml
<w:ins w:author="Jane" w:id="5">
  <w:del w:author="Claude" w:id="10">
    <w:r><w:delText>their inserted text</w:delText></w:r>
  </w:del>
</w:ins>
```

### Restoring Another Author's Deletion

Add insertion after (don't modify their deletion):

```xml
<w:del w:author="Jane" w:id="5">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
<w:ins w:author="Claude" w:id="10">
  <w:r><w:t>deleted text</w:t></w:r>
</w:ins>
```

---

## Comments

### Adding Comments

1. Run comment.py to add comment to comments.xml:
   ```bash
   ./run tool/office/comment.py unpacked/ 0 "Comment text"
   ./run tool/office/comment.py unpacked/ 1 "Reply" --parent 0
   ```

2. Add markers to document.xml:
   ```xml
   <w:commentRangeStart w:id="0"/>
   <w:r><w:t>text being commented on</w:t></w:r>
   <w:commentRangeEnd w:id="0"/>
   <w:r>
     <w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>
     <w:commentReference w:id="0"/>
   </w:r>
   ```

**CRITICAL**: `<w:commentRangeStart>` and `<w:commentRangeEnd>` are siblings of `<w:r>`, never inside `<w:r>`.

### Comment with Reply

```xml
<w:commentRangeStart w:id="0"/>
  <w:commentRangeStart w:id="1"/>
  <w:r><w:t>text</w:t></w:r>
  <w:commentRangeEnd w:id="1"/>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="1"/></w:r>
```

---

## Common Pitfalls

1. **Replace entire `<w:r>` elements**: When adding tracked changes, replace the whole run with `<w:del>...<w:ins>...` as siblings. Don't inject inside a run.

2. **Preserve `<w:rPr>` formatting**: Copy the original run's `<w:rPr>` block into tracked change runs.

3. **Comment markers outside runs**: `<w:commentRangeStart>` goes directly in `<w:p>`, not inside `<w:r>`.

4. **Use unique IDs**: Each tracked change and comment needs a unique `w:id`.
