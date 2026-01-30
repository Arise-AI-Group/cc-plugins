/**
 * Professional DOCX Proposal Generator
 *
 * This example demonstrates creating professional Word documents using docx-js.
 * Customize the content and styling for your specific proposal needs.
 *
 * Usage:
 *   npm install docx
 *   node create-proposal.js
 *
 * Output: proposal.docx
 */

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        ShadingType, PageNumber, PageBreak, LevelFormat } = require('docx');
const fs = require('fs');

// ===== CONFIGURATION =====
// Customize these values for your proposal

const config = {
    company: {
        name: "Your Company",
        tagline: "Professional Services",
        email: "contact@yourcompany.com"
    },
    client: {
        name: "Client Name",
        contact: "Contact Person",
        title: "Client Title",
        company: "Client Company",
        address: "123 Client Address, City, State"
    },
    proposal: {
        title: "Project Proposal",
        subtitle: "Service Description",
        date: new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
        validDays: 30
    }
};

// ===== COLORS =====
const PRIMARY_BLUE = "1E3A5F";
const ACCENT_BLUE = "2E5A8F";
const LIGHT_BLUE = "E8F0F8";
const HEADER_GRAY = "4A4A4A";

// ===== HELPER FUNCTIONS =====

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function sectionHeader(text) {
    return new Paragraph({
        spacing: { before: 400, after: 200 },
        children: [
            new TextRun({ text: text, bold: true, size: 28, font: "Arial", color: PRIMARY_BLUE })
        ]
    });
}

function subsectionHeader(text) {
    return new Paragraph({
        spacing: { before: 300, after: 120 },
        children: [
            new TextRun({ text: text, bold: true, size: 24, font: "Arial", color: ACCENT_BLUE })
        ]
    });
}

function bodyText(text, options = {}) {
    return new Paragraph({
        spacing: { after: 120 },
        children: [
            new TextRun({ text: text, size: 22, font: "Arial", ...options })
        ]
    });
}

function bulletPoint(text, boldPrefix = null) {
    const children = [];
    if (boldPrefix) {
        children.push(new TextRun({ text: boldPrefix, bold: true, size: 22, font: "Arial" }));
        children.push(new TextRun({ text: text, size: 22, font: "Arial" }));
    } else {
        children.push(new TextRun({ text: text, size: 22, font: "Arial" }));
    }
    return new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        spacing: { after: 80 },
        children: children
    });
}

// ===== DOCUMENT CREATION =====

const doc = new Document({
    styles: {
        default: { document: { run: { font: "Arial", size: 22 } } },
    },
    numbering: {
        config: [
            {
                reference: "bullets",
                levels: [{
                    level: 0,
                    format: LevelFormat.BULLET,
                    text: "\u2022",
                    alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } }
                }]
            },
            {
                reference: "numbers",
                levels: [{
                    level: 0,
                    format: LevelFormat.DECIMAL,
                    text: "%1.",
                    alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } }
                }]
            },
        ]
    },
    sections: [{
        properties: {
            page: {
                size: { width: 12240, height: 15840 }, // US Letter
                margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
            }
        },
        headers: {
            default: new Header({
                children: [new Paragraph({
                    alignment: AlignmentType.RIGHT,
                    children: [
                        new TextRun({ text: config.company.name, bold: true, size: 20, font: "Arial", color: PRIMARY_BLUE }),
                        new TextRun({ text: ` | ${config.company.tagline}`, size: 20, font: "Arial", color: HEADER_GRAY })
                    ]
                })]
            })
        },
        footers: {
            default: new Footer({
                children: [new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [
                        new TextRun({ text: "Page ", size: 18, font: "Arial", color: HEADER_GRAY }),
                        new TextRun({ children: [PageNumber.CURRENT], size: 18, font: "Arial", color: HEADER_GRAY }),
                        new TextRun({ text: ` | ${config.company.email}`, size: 18, font: "Arial", color: HEADER_GRAY })
                    ]
                })]
            })
        },
        children: [
            // ===== TITLE SECTION =====
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { after: 120 },
                children: [
                    new TextRun({ text: "PROPOSAL", bold: true, size: 40, font: "Arial", color: PRIMARY_BLUE })
                ]
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { after: 80 },
                children: [
                    new TextRun({ text: config.proposal.subtitle, bold: true, size: 32, font: "Arial", color: ACCENT_BLUE })
                ]
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { after: 400 },
                children: [
                    new TextRun({ text: `${config.client.company}`, size: 24, font: "Arial", color: HEADER_GRAY })
                ]
            }),

            // Prepared For / By Table
            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [4680, 4680],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: noBorders,
                                width: { size: 4680, type: WidthType.DXA },
                                children: [
                                    new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Prepared for:", bold: true, size: 20, font: "Arial", color: HEADER_GRAY })] }),
                                    new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: config.client.contact, bold: true, size: 22, font: "Arial" })] }),
                                    new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: config.client.title, size: 20, font: "Arial" })] }),
                                    new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: config.client.company, size: 20, font: "Arial" })] }),
                                    new Paragraph({ children: [new TextRun({ text: config.client.address, size: 20, font: "Arial" })] })
                                ]
                            }),
                            new TableCell({
                                borders: noBorders,
                                width: { size: 4680, type: WidthType.DXA },
                                children: [
                                    new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Prepared by:", bold: true, size: 20, font: "Arial", color: HEADER_GRAY })] }),
                                    new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: config.company.name, bold: true, size: 22, font: "Arial" })] }),
                                    new Paragraph({ children: [new TextRun({ text: config.company.email, size: 20, font: "Arial" })] })
                                ]
                            })
                        ]
                    })
                ]
            }),

            // Date box
            new Paragraph({ spacing: { before: 300 }, children: [] }),
            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders,
                                shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR },
                                margins: { top: 120, bottom: 120, left: 200, right: 200 },
                                children: [
                                    new Paragraph({
                                        alignment: AlignmentType.CENTER,
                                        children: [
                                            new TextRun({ text: "Date: ", bold: true, size: 22, font: "Arial" }),
                                            new TextRun({ text: config.proposal.date, size: 22, font: "Arial" })
                                        ]
                                    })
                                ]
                            })
                        ]
                    })
                ]
            }),

            // ===== EXECUTIVE SUMMARY =====
            sectionHeader("EXECUTIVE SUMMARY"),
            bodyText("Enter your executive summary here. This should provide a high-level overview of the proposed project, key benefits, and expected outcomes."),

            // ===== PROJECT SCOPE =====
            new Paragraph({ children: [new PageBreak()] }),
            sectionHeader("PROJECT SCOPE"),

            subsectionHeader("1. Phase One"),
            bulletPoint(" Description of first phase work item", "Task 1:"),
            bulletPoint(" Description of second work item", "Task 2:"),

            subsectionHeader("2. Phase Two"),
            bulletPoint(" Description of phase two work", "Task 1:"),

            // ===== INVESTMENT =====
            sectionHeader("INVESTMENT"),
            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [4200, 1500, 1500, 2160],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({ borders, shading: { fill: PRIMARY_BLUE, type: ShadingType.CLEAR }, children: [new Paragraph({ children: [new TextRun({ text: "Service", bold: true, size: 20, font: "Arial", color: "FFFFFF" })] })] }),
                            new TableCell({ borders, shading: { fill: PRIMARY_BLUE, type: ShadingType.CLEAR }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Hours", bold: true, size: 20, font: "Arial", color: "FFFFFF" })] })] }),
                            new TableCell({ borders, shading: { fill: PRIMARY_BLUE, type: ShadingType.CLEAR }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Rate", bold: true, size: 20, font: "Arial", color: "FFFFFF" })] })] }),
                            new TableCell({ borders, shading: { fill: PRIMARY_BLUE, type: ShadingType.CLEAR }, children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Subtotal", bold: true, size: 20, font: "Arial", color: "FFFFFF" })] })] })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "Service Line 1", size: 22, font: "Arial" })] })] }),
                            new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "8", size: 22, font: "Arial" })] })] }),
                            new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "$100/hr", size: 22, font: "Arial" })] })] }),
                            new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "$800.00", size: 22, font: "Arial" })] })] })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({ borders, shading: { fill: PRIMARY_BLUE, type: ShadingType.CLEAR }, children: [new Paragraph({ children: [new TextRun({ text: "TOTAL", bold: true, size: 24, font: "Arial", color: "FFFFFF" })] })] }),
                            new TableCell({ borders, shading: { fill: PRIMARY_BLUE, type: ShadingType.CLEAR }, children: [new Paragraph({ children: [] })] }),
                            new TableCell({ borders, shading: { fill: PRIMARY_BLUE, type: ShadingType.CLEAR }, children: [new Paragraph({ children: [] })] }),
                            new TableCell({ borders, shading: { fill: PRIMARY_BLUE, type: ShadingType.CLEAR }, children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "$800.00", bold: true, size: 24, font: "Arial", color: "FFFFFF" })] })] })
                        ]
                    })
                ]
            }),

            // ===== TERMS =====
            sectionHeader("TERMS & CONDITIONS"),
            bodyText(`Payment: 50% deposit to commence work, balance due within 30 days of completion`),
            bodyText(`Validity: This proposal is valid for ${config.proposal.validDays} days`),
            bodyText(`Warranty: 30-day warranty on all work delivered`),

            // ===== SIGNATURE =====
            new Paragraph({ spacing: { before: 400 }, children: [] }),
            sectionHeader("ACCEPTANCE"),
            bodyText("By signing below, both parties agree to the terms and scope outlined in this proposal."),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [4680, 4680],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({ borders: noBorders, children: [new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "Customer", bold: true, size: 22, font: "Arial" })] })] }),
                            new TableCell({ borders: noBorders, children: [new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: config.company.name, bold: true, size: 22, font: "Arial" })] })] })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({ borders: noBorders, children: [
                                new Paragraph({ spacing: { before: 300 }, children: [new TextRun({ text: "____________________________", size: 22, font: "Arial" })] }),
                                new Paragraph({ children: [new TextRun({ text: "Signature / Date", size: 18, font: "Arial", color: HEADER_GRAY })] })
                            ]}),
                            new TableCell({ borders: noBorders, children: [
                                new Paragraph({ spacing: { before: 300 }, children: [new TextRun({ text: "____________________________", size: 22, font: "Arial" })] }),
                                new Paragraph({ children: [new TextRun({ text: "Signature / Date", size: 18, font: "Arial", color: HEADER_GRAY })] })
                            ]})
                        ]
                    })
                ]
            })
        ]
    }]
});

// ===== GENERATE DOCUMENT =====
const outputPath = process.argv[2] || "proposal.docx";

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync(outputPath, buffer);
    console.log(`Document created: ${outputPath}`);
});
