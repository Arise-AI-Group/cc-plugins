# PDF Form Filling Reference

This guide covers filling both fillable PDF forms (with AcroForm fields) and non-fillable PDFs (using annotations).

## Decision Tree

1. **Check if fillable**: `./run tool/forms/check_fillable.py form.pdf`
2. If `has_fields: true` → Use **Fillable PDF Workflow**
3. If `has_fields: false` → Use **Non-Fillable PDF Workflow**

---

## Fillable PDF Workflow

For PDFs with actual form fields (text boxes, checkboxes, dropdowns).

### Step 1: Extract Field Information

```bash
./run tool/forms/extract_fields.py form.pdf -o field_info.json
```

Output format:
```json
[
  {
    "field_id": "last_name",
    "page": 1,
    "rect": [100, 200, 300, 220],
    "type": "text"
  },
  {
    "field_id": "checkbox1",
    "page": 1,
    "type": "checkbox",
    "checked_value": "/On",
    "unchecked_value": "/Off"
  },
  {
    "field_id": "gender",
    "page": 1,
    "type": "radio_group",
    "radio_options": [
      {"value": "/Male", "rect": [100, 200, 120, 220]},
      {"value": "/Female", "rect": [100, 180, 120, 200]}
    ]
  },
  {
    "field_id": "country",
    "page": 1,
    "type": "choice",
    "choice_options": [
      {"value": "US", "text": "United States"},
      {"value": "CA", "text": "Canada"}
    ]
  }
]
```

### Step 2: Convert to Images (Optional)

For visual analysis of field purposes:

```bash
./run tool/forms/convert_to_images.py form.pdf images/ --scale 1.5
```

### Step 3: Create Values File

Create `values.json`:
```json
[
  {
    "field_id": "last_name",
    "description": "User's last name",
    "page": 1,
    "value": "Simpson"
  },
  {
    "field_id": "checkbox1",
    "description": "Confirm 18 or over",
    "page": 1,
    "value": "/On"
  }
]
```

**Note**: Use `checked_value` from field_info.json for checkboxes.

### Step 4: Fill the Form

```bash
./run tool/forms/fill_fields.py form.pdf values.json -o filled.pdf
```

---

## Non-Fillable PDF Workflow

For PDFs without form fields. This adds text annotations to "fill" the form visually.

### Approach A: Structure-Based (Preferred)

Use when the PDF has extractable text.

#### A.1: Extract Structure

```bash
./run tool/forms/extract_structure.py form.pdf -o structure.json
```

Output contains:
- **labels**: Text elements with coordinates
- **lines**: Horizontal lines (field boundaries)
- **checkboxes**: Small square rectangles
- **row_boundaries**: Row positions from lines

#### A.2: Analyze and Create fields.json

Use the structure to calculate entry positions:

```json
{
  "pages": [
    {"page_number": 1, "pdf_width": 612, "pdf_height": 792}
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry",
      "field_label": "Last Name",
      "label_bounding_box": [43, 63, 87, 73],
      "entry_bounding_box": [92, 63, 260, 79],
      "entry_text": {"text": "Smith", "font_size": 10}
    }
  ]
}
```

**Coordinate calculation:**
- entry x0 = label x1 + 5 (gap after label)
- entry x1 = next label's x0, or line end
- entry top/bottom = same as label or row boundaries

### Approach B: Visual Estimation (Fallback)

Use when the PDF is scanned/image-based.

#### B.1: Convert to Images

```bash
./run tool/forms/convert_to_images.py form.pdf images/ --scale 2.0
```

#### B.2: Identify Fields

Examine images to find:
- Field labels and their positions
- Entry areas (lines, boxes)
- Checkbox locations

#### B.3: Create fields.json with Image Coordinates

Use `image_width`/`image_height` to signal image coordinates:

```json
{
  "pages": [
    {"page_number": 1, "image_width": 1700, "image_height": 2200}
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry",
      "field_label": "Last Name",
      "label_bounding_box": [120, 175, 242, 198],
      "entry_bounding_box": [255, 175, 720, 218],
      "entry_text": {"text": "Smith", "font_size": 10}
    }
  ]
}
```

The fill script auto-converts image to PDF coordinates.

### Step: Validate Before Filling

```bash
./run tool/forms/check_bounding_boxes.py fields.json
```

Checks for:
- Intersecting entry boxes
- Boxes too small for font size
- Invalid coordinates

### Step: Fill with Annotations

```bash
./run tool/forms/fill_annotations.py form.pdf fields.json -o filled.pdf
```

### Step: Verify Output

```bash
./run tool/forms/convert_to_images.py filled.pdf verify/ --scale 1.5
```

Check that text appears in correct positions.

---

## Coordinate Systems

### PDF Coordinates
- Origin at **bottom-left**
- Y increases upward
- Use `pdf_width`/`pdf_height` in fields.json

### Image Coordinates
- Origin at **top-left**
- Y increases downward
- Use `image_width`/`image_height` in fields.json

**Conversion (image → PDF):**
```
pdf_x = image_x * (pdf_width / image_width)
pdf_y = pdf_height - (image_y * (pdf_height / image_height))
```

---

## CLI Reference

### check_fillable.py

```bash
./run tool/forms/check_fillable.py input.pdf [--output-format json|text]
```

### extract_fields.py

```bash
./run tool/forms/extract_fields.py input.pdf [-o fields.json] [--output-format json|text]
```

### fill_fields.py

```bash
./run tool/forms/fill_fields.py input.pdf values.json -o filled.pdf
```

### convert_to_images.py

```bash
./run tool/forms/convert_to_images.py input.pdf output_dir/ [--scale 1.5] [--pages "1-3,5"] [--format png|jpg]
```

### extract_structure.py

```bash
./run tool/forms/extract_structure.py input.pdf [-o structure.json]
```

### fill_annotations.py

```bash
./run tool/forms/fill_annotations.py input.pdf fields.json -o filled.pdf
```

### check_bounding_boxes.py

```bash
./run tool/forms/check_bounding_boxes.py fields.json [--output-format json|text]
```

---

## Troubleshooting

### Text appears in wrong position

1. Check coordinate system (pdf_width vs image_width)
2. Verify image dimensions match actual image
3. Use structure extraction for accurate PDF coordinates

### Checkboxes not detected

Structure extraction only finds **square** rectangles. For circular checkboxes:
- Use visual estimation
- Mark center point and add "X" text

### Scanned PDF has no structure

Fall back to visual estimation (Approach B). Use high resolution (`--scale 2.0`) for accurate positioning.
